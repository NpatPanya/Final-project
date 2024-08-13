import os
import hashlib
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from tkinter.scrolledtext import ScrolledText
from PIL import Image, ImageTk
import send2trash
import tempfile
import psutil
from concurrent.futures import ThreadPoolExecutor

directory = ""
duplicate_files = {}

def calculate_file_hash(filepath):
    try:
        with open(filepath, 'rb') as file:
            return hashlib.md5(file.read()).hexdigest()
    except Exception as e:
        return None

def find_duplicate_files(directory, max_depth=None):
    file_hash_map = {}
    duplicates = {}

    def calculate_hash_and_check_duplicate(filepath):
        file_hash = calculate_file_hash(filepath)
        if file_hash:
            if file_hash in file_hash_map:
                duplicates[filepath] = file_hash_map[file_hash]
            else:
                file_hash_map[file_hash] = filepath

    with ThreadPoolExecutor() as executor:
        for root, dirs, files in os.walk(directory):
            file_paths = [os.path.join(root, filename) for filename in files]

            if max_depth is not None:
                relative_depths = [len(os.path.relpath(filepath, start=directory).split(os.path.sep)) for filepath in file_paths]
                file_paths = [file_paths[i] for i, depth in enumerate(relative_depths) if depth <= max_depth]

            executor.map(calculate_hash_and_check_duplicate, file_paths)

    return duplicates

def browse_directory():
    global directory
    directory = filedialog.askdirectory()
    if directory:
        global duplicate_files
        max_depth = 10
        duplicate_files = find_duplicate_files(directory, max_depth)
        reset_results()
        display_results(duplicate_files)

def display_results(duplicates):
    result_text.delete(1.0, tk.END)
    if not duplicates:
        result_text.insert(tk.END, "No duplicate files found in the directory\n")
    else:
        for file1, file2 in duplicates.items():
            tree.insert('', 'end', values=(file1, file2))
            
def reset_results():
    tree.delete(*tree.get_children())
    result_text.delete(1.0, tk.END)

def select_all():
    for item in tree.get_children():
        tree.selection_add(item)

def delete_selected():
    selected_items = tree.selection()

    if not selected_items:
        messagebox.showinfo("No Selection", "No files selected for deletion.")
        return

    confirmed = messagebox.askyesno("Confirmation", "Are you sure you want to delete the selected files? This action cannot be undone.")
    
    if confirmed:
        deleted_files = []

        for item in selected_items:
            file1 = tree.item(item, "values")[0]
            if file1 != "No duplicate files found":
                try:
                    full_path = os.path.join(directory, file1)
                    if os.path.isfile(full_path):
                        os.remove(full_path)
                    elif os.path.isdir(full_path):
                        shutil.rmtree(full_path, ignore_errors=True)
                    deleted_files.append(file1)
                    tree.delete(item)
                except Exception as e:
                    result_text.insert(tk.END, f"Failed to delete {file1}: {str(e)}\n")
        
        if deleted_files:
            result_text.insert(tk.END, "Deleted files:\n")
            for file in deleted_files:
                result_text.insert(tk.END, f"{file}\n")

        messagebox.showinfo("Operation Complete", "Selected files have been deleted.")
        display_free_space()

def preview_selected():
    selected_items = tree.selection()

    if not selected_items:
        messagebox.showinfo("No Selection", "No files selected for preview.")
        return

    file1 = tree.item(selected_items[0], "values")[0]
    if file1 != "No duplicate files found":
        full_path = os.path.join(directory, file1)
        try:
            if is_text_file(full_path):
                with open(full_path, 'r', encoding='utf-8') as file:
                    contents = file.read()
                    show_preview(contents)
            elif is_image_file(full_path):
                show_image_preview(full_path)
            else:
                show_preview("This file type cannot be previewed.")
        except Exception as e:
            result_text.insert(tk.END, f"Failed to preview {file1}: {str(e)}\n")

def is_image_file(filepath):
    try:
        with Image.open(filepath):
            return True
    except Exception:
        return False

def show_image_preview(image_path):
    if not hasattr(app, 'image_preview_window') or not app.image_preview_window.winfo_exists():
        app.image_preview_window = tk.Toplevel(app)
        app.image_preview_window.title("Image Preview")

        image = Image.open(image_path)
        photo = ImageTk.PhotoImage(image)

        preview_label = tk.Label(app.image_preview_window, image=photo)
        preview_label.photo = photo
        preview_label.pack()


def is_text_file(filepath):
    try:
        with open(filepath, 'rb') as file:
            # Read a chunk of the file and check for null bytes (binary files often have them)
            chunk = file.read(1024)
            return b'\x00' not in chunk
    except Exception:
        return False

def show_preview(contents):
    if not hasattr(app, 'preview_window') or not app.preview_window.winfo_exists():
        app.preview_window = tk.Toplevel(app)
        app.preview_window.title("Preview")

    preview_text = ScrolledText(app.preview_window, wrap=tk.WORD, width=80, height=20)
    preview_text.delete(1.0, tk.END)
    preview_text.insert(tk.END, contents)
    preview_text.pack()

def display_manual():
    if not hasattr(app, 'manual_window'):
        app.manual_window = tk.Toplevel(app)
        app.manual_window.title("User Manual")

    manual_text = """
    Duplicate File Finder and Directory Cleanup

    1. Click the 'Browse Directory' button to select a directory for scanning duplicate files.
    2. Click 'Find Duplicates' to locate and display duplicate files.
    3. Select duplicate files in the list to preview or delete.
    4. Click 'Preview Selected' to view the contents of a selected file.
    5. Click 'Delete Selected' to remove selected duplicate files.
    6. Click 'Clean Up Directory' to delete all files and folders in the directory.
    7. Click 'Disk Cleanup' to delete temporary and unnecessary files in the directory.
    8. To exit the application, click the close button (X) on the window.

    Note: Use caution when deleting files as it cannot be undone.
    """

    manual_text_widget = ScrolledText(app.manual_window, wrap=tk.WORD, width=80, height=20)
    manual_text_widget.delete(1.0, tk.END)
    manual_text_widget.insert(tk.END, manual_text)
    manual_text_widget.pack()


def display_free_space():
    disk_partitions = psutil.disk_partitions()
    result_text.delete(1.0, tk.END)
    result_text.insert(tk.END, "Free Space Available:\n")
    
    for partition in disk_partitions:
        partition_info = psutil.disk_usage(partition.mountpoint)
        free_space = partition_info.free / (1024 ** 3)  # Convert to GB
        result_text.insert(tk.END, f"{partition.device} - Free Space: {free_space:.2f} GB\n")



def clean_up_directory():
    temp_directory = tempfile.gettempdir()
    num_deleted_files = 0
    reset_results() 
    for root, dirs, files in os.walk(temp_directory):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                send2trash.send2trash(file_path)
                result_text.insert(tk.END, f"{file}\n")
                num_deleted_files += 1
            except Exception as e:
                continue
        
        for dir in dirs:
            dir_path = os.path.join(root, dir)
            try:
                send2trash.send2trash(dir_path)
                result_text.insert(tk.END, f"{dir}\n")
                num_deleted_files += 1
            except Exception as e:
                continue

    result_text.insert(tk.END, f"Disk Cleanup Complete. Deleted {num_deleted_files} files.\n")
    messagebox.showinfo("Disk Cleanup Complete", "Disk cleanup operation is finished.")
    display_free_space()

app = tk.Tk()
app.title("Duplicate File Finder and DirectCleanup")

style = ttk.Style()
style.configure("TButton", foreground="black", background="blue")

app.geometry("800x600")
app.resizable(True, True)

label1 = tk.Label(app, text="Duplicate File Finder and Directory Cleanup", font=("Helvetica", 16))
label1.pack(pady=10)

free_space_label = tk.Label(app, text="Free Space Available: Loading...")
free_space_label.pack(padx=10, anchor="w")

tree = ttk.Treeview(app, columns=("File 1", "File 2"), show="headings", height=10)
tree.heading("File 1", text="Duplicated File")
tree.heading("File 2", text="Original File")
tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

# Create a frame for the buttons and pack it to the left side
button_frame = tk.Frame(app)
button_frame.pack(side=tk.LEFT, padx=100)

browse_button = ttk.Button(app, text="Browse Directory", command=browse_directory)
select_all_button = ttk.Button(app, text="Select All", command=select_all)
delete_button = ttk.Button(app, text="Delete Selected", command=delete_selected)
cleanup_button = ttk.Button(app, text="Disk Cleanup", command=clean_up_directory)
separator1 = ttk.Separator(app, orient="horizontal")
preview_button = ttk.Button(app, text="Preview Selected", command=preview_selected)
manual_button = ttk.Button(app, text="User Manual", command=display_manual)

browse_button.pack(in_=button_frame, pady=10, anchor='w')
select_all_button.pack(in_=button_frame, pady=10, anchor='w')
delete_button.pack(in_=button_frame, pady=10, anchor='w')
cleanup_button.pack(in_=button_frame, pady=10, anchor='w')
preview_button.pack(in_=button_frame, pady=10, anchor='w')
manual_button.pack(in_=button_frame, pady=10, anchor='w')

result_text = tk.Text(app, wrap=tk.WORD, width=200, height=25)
result_text.pack(padx=10)

display_free_space()  # Display free space information when the application starts

app.mainloop()
