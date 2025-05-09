import os
import shutil
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime
from PIL import Image
from PIL.ExifTags import TAGS
import threading
import queue

class PhotoImporterGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Photo Importer")
        
        # Variables
        self.source_path = tk.StringVar()
        self.dest_path = tk.StringVar()
        self.status = tk.StringVar(value="Ready")
        self.progress_queue = queue.Queue()
        
        # Create UI
        self.create_widgets()
        
        # Start queue checker
        self.check_queue()

    def create_widgets(self):
        # Source Folder
        ttk.Label(self.root, text="Source Folder (Camera):").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        ttk.Entry(self.root, textvariable=self.source_path, width=50).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(self.root, text="Browse", command=self.select_source).grid(row=0, column=2, padx=5, pady=5)
        
        # Destination Folder
        ttk.Label(self.root, text="Destination Folder:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        ttk.Entry(self.root, textvariable=self.dest_path, width=50).grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(self.root, text="Browse", command=self.select_dest).grid(row=1, column=2, padx=5, pady=5)
        
        # Progress Bar
        self.progress = ttk.Progressbar(self.root, orient="horizontal", length=400, mode="determinate")
        self.progress.grid(row=2, column=0, columnspan=3, padx=5, pady=5)
        
        # Start Button
        ttk.Button(self.root, text="Start Import", command=self.start_import).grid(row=3, column=1, pady=10)
        
        # Status Bar
        ttk.Label(self.root, textvariable=self.status).grid(row=4, column=0, columnspan=3, pady=5)

    def select_source(self):
        folder = filedialog.askdirectory(title="Select Camera/SD Card Folder")
        if folder:
            self.source_path.set(folder)

    def select_dest(self):
        folder = filedialog.askdirectory(title="Select Destination Folder")
        if folder:
            self.dest_path.set(folder)

    def get_photo_date(self, image_path):
        try:
            with Image.open(image_path) as img:
                exif = img._getexif()
                if exif:
                    for tag_id, value in exif.items():
                        tag = TAGS.get(tag_id, tag_id)
                        if tag == "DateTimeOriginal":
                            date_str = value.strip()
                            return datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
        except (AttributeError, KeyError, ValueError):
            pass
        
        timestamp = os.path.getmtime(image_path)
        return datetime.fromtimestamp(timestamp)

    def organize_photos(self):
        try:
            source = self.source_path.get()
            dest_root = self.dest_path.get()
            
            # Count total files first for progress
            file_count = 0
            for root, _, files in os.walk(source):
                for file in files:
                    if file.lower().endswith(('.jpg', '.jpeg', '.cr2', '.png')):
                        file_count += 1
            
            self.progress_queue.put(("max", file_count))
            self.progress_queue.put(("update", 0, file_count))
            
            current_file = 0
            for root, _, files in os.walk(source):
                for file in files:
                    if file.lower().endswith(('.jpg', '.jpeg', '.cr2', '.png')):
                        src_path = os.path.join(root, file)
                        date_taken = self.get_photo_date(src_path)
                        
                        year = date_taken.strftime("%Y")
                        day = date_taken.strftime("%Y-%m-%d")
                        dest_dir = os.path.join(dest_root, year, day)
                        
                        os.makedirs(dest_dir, exist_ok=True)
                        
                        dest_path = os.path.join(dest_dir, file)
                        if not os.path.exists(dest_path):
                            shutil.copy2(src_path, dest_path)
                        
                        current_file += 1
                        self.progress_queue.put(("update", current_file, file_count))
                        self.progress_queue.put(("status", f"Processing {current_file}/{file_count}: {file}"))
            
            self.progress_queue.put(("complete", "Import completed successfully!"))
        except Exception as e:
            self.progress_queue.put(("error", f"Error: {str(e)}"))

    def check_queue(self):
        try:
            while True:
                msg = self.progress_queue.get_nowait()
                if msg[0] == "max":
                    self.progress["maximum"] = msg[1]
                elif msg[0] == "update":
                    self.progress["value"] = msg[1]
                    self.status.set(f"Processed {msg[1]} of {msg[2]} files")
                elif msg[0] == "status":
                    self.status.set(msg[1])
                elif msg[0] == "complete":
                    messagebox.showinfo("Complete", msg[1])
                    self.status.set("Ready")
                    self.progress["value"] = 0
                elif msg[0] == "error":
                    messagebox.showerror("Error", msg[1])
                    self.status.set("Error occurred")
                    self.progress["value"] = 0
                self.root.update_idletasks()
        except queue.Empty:
            pass
        self.root.after(100, self.check_queue)

    def start_import(self):
        if not self.source_path.get() or not self.dest_path.get():
            messagebox.showwarning("Warning", "Please select both folders first")
            return
        
        # Reset progress
        self.progress["value"] = 0
        self.status.set("Starting import...")
        
        # Start thread
        thread = threading.Thread(target=self.organize_photos)
        thread.daemon = True
        thread.start()

if __name__ == "__main__":
    root = tk.Tk()
    app = PhotoImporterGUI(root)
    root.mainloop()
