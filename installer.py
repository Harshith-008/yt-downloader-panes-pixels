import os
import sys
import zipfile
import threading
import subprocess
import winreg
import shutil
import tkinter as tk
from tkinter import filedialog
import customtkinter as ctk

# Set appearance and theme
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def get_special_folder(folder_name):
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders")
        value, _ = winreg.QueryValueEx(key, folder_name)
        winreg.CloseKey(key)
        return os.path.expandvars(value)
    except Exception:
        if folder_name == "Desktop":
            return os.path.join(os.path.expanduser("~"), "Desktop")
        elif folder_name == "Programs":
            return os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "Microsoft", "Windows", "Start Menu", "Programs")
        return None

def create_shortcut(target, shortcut_path, icon):
    try:
        target_escaped = target.replace("'", "''")
        shortcut_escaped = shortcut_path.replace("'", "''")
        icon_escaped = icon.replace("'", "''")
        
        ps_command = (
            f'$WshShell = New-Object -ComObject WScript.Shell; '
            f'$Shortcut = $WshShell.CreateShortcut(\'{shortcut_escaped}\'); '
            f'$Shortcut.TargetPath = \'{target_escaped}\'; '
            f'$Shortcut.WorkingDirectory = \'{os.path.dirname(target_escaped)}\'; '
            f'$Shortcut.IconLocation = \'{icon_escaped},0\'; '
            f'$Shortcut.Save()'
        )
        
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_command],
            creationflags=subprocess.CREATE_NO_WINDOW,
            check=True
        )
    except Exception as e:
        print(f"Error creating shortcut: {e}")

class Installer(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("YT Downloader - Installation Wizard")
        self.geometry("550x400")
        self.resizable(False, False)
        self.configure(fg_color="#11111b")
        
        # Load window icon
        try:
            icon_file = resource_path("icon.ico")
            if os.path.exists(icon_file):
                self.iconbitmap(icon_file)
        except:
            pass
            
        # Default settings
        default_dir = os.path.join(
            os.environ.get("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local")),
            "Programs",
            "YT Downloader by Panes & Pixels"
        )
        self.install_dir = tk.StringVar(value=default_dir)
        self.create_desktop_shortcut = tk.BooleanVar(value=True)
        self.create_start_menu_shortcut = tk.BooleanVar(value=True)
        
        self.current_step = 1
        self.zip_extracted_success = False
        
        # Container frame for active step
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.pack(fill="both", expand=True, padx=30, pady=20)
        
        # Bottom navigation row
        self.nav_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.nav_frame.pack(fill="x", padx=30, pady=(0, 20))
        
        self.back_btn = ctk.CTkButton(
            self.nav_frame,
            text="Back",
            width=100,
            height=35,
            fg_color="#313244",
            hover_color="#45475a",
            text_color="#cdd6f4",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            command=self.prev_step,
            corner_radius=6
        )
        
        self.next_btn = ctk.CTkButton(
            self.nav_frame,
            text="Next",
            width=100,
            height=35,
            fg_color="#cba6f7",
            hover_color="#b4befe",
            text_color="#11111b",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            command=self.next_step,
            corner_radius=6
        )
        self.next_btn.pack(side="right")
        
        self.show_step()
        
    def show_step(self):
        # Clear current content
        for widget in self.content_frame.winfo_children():
            widget.destroy()
            
        # Hide/show back button
        if self.current_step == 1 or self.current_step == 4 or self.current_step == 5:
            self.back_btn.pack_forget()
        else:
            self.back_btn.pack(side="left")
            
        if self.current_step == 1:
            self.show_welcome_step()
        elif self.current_step == 2:
            self.show_directory_step()
        elif self.current_step == 3:
            self.show_shortcuts_step()
        elif self.current_step == 4:
            self.show_progress_step()
        elif self.current_step == 5:
            self.show_complete_step()
            
    def prev_step(self):
        if self.current_step > 1:
            self.current_step -= 1
            self.show_step()
            
    def next_step(self):
        if self.current_step < 5:
            if self.current_step == 3:
                # Move to installation progress
                self.current_step += 1
                self.show_step()
                self.start_installation()
            else:
                self.current_step += 1
                self.show_step()
        else:
            self.finish_installer()

    # --- STEP 1: WELCOME SCREEN ---
    def show_welcome_step(self):
        title = ctk.CTkLabel(
            self.content_frame,
            text="Welcome to YT Downloader Setup",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color="#cba6f7"
        )
        title.pack(pady=(10, 10))
        
        desc = ctk.CTkLabel(
            self.content_frame,
            text="This wizard will install YT Downloader by Panes & Pixels on your computer.\n\nIt is recommended to close all other applications before continuing.",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#cdd6f4",
            justify="center"
        )
        desc.pack(pady=20)
        
        legal = ctk.CTkLabel(
            self.content_frame,
            text="Click 'Next' to continue, or close this window to cancel.",
            font=ctk.CTkFont(family="Segoe UI", size=11, slant="italic"),
            text_color="#a6adc8"
        )
        legal.pack(pady=(30, 0))
        self.next_btn.configure(text="Next", state="normal")

    # --- STEP 2: DIRECTORY SELECTION ---
    def show_directory_step(self):
        title = ctk.CTkLabel(
            self.content_frame,
            text="Choose Install Location",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color="#cba6f7"
        )
        title.pack(pady=(10, 10))
        
        desc = ctk.CTkLabel(
            self.content_frame,
            text="Setup will install the program files into the following folder.\nTo install to a different folder, click Browse and select another folder.",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#cdd6f4",
            justify="left"
        )
        desc.pack(fill="x", pady=(10, 20))
        
        dir_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        dir_frame.pack(fill="x", pady=10)
        
        self.dir_entry = ctk.CTkEntry(
            dir_frame,
            textvariable=self.install_dir,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            fg_color="#1e1e2e",
            border_color="#313244",
            text_color="#cdd6f4",
            corner_radius=6,
            height=35
        )
        self.dir_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        browse_btn = ctk.CTkButton(
            dir_frame,
            text="Browse...",
            width=90,
            height=35,
            fg_color="#313244",
            hover_color="#45475a",
            text_color="#cdd6f4",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            command=self.browse_directory,
            corner_radius=6
        )
        browse_btn.pack(side="right")

    def browse_directory(self):
        chosen = filedialog.askdirectory(initialdir=self.install_dir.get(), title="Select Installation Folder")
        if chosen:
            # Normalize path slashes
            normalized = os.path.abspath(chosen)
            self.install_dir.set(normalized)

    # --- STEP 3: SHORTCUT OPTIONS ---
    def show_shortcuts_step(self):
        title = ctk.CTkLabel(
            self.content_frame,
            text="Select Additional Tasks",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color="#cba6f7"
        )
        title.pack(pady=(10, 10))
        
        desc = ctk.CTkLabel(
            self.content_frame,
            text="Select the shortcuts you would like Setup to create while installing\nYT Downloader by Panes & Pixels, then click Next.",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#cdd6f4",
            justify="left"
        )
        desc.pack(fill="x", pady=(10, 20))
        
        chk_desktop = ctk.CTkCheckBox(
            self.content_frame,
            text="Create a Desktop shortcut",
            variable=self.create_desktop_shortcut,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color="#cba6f7",
            hover_color="#b4befe"
        )
        chk_desktop.pack(anchor="w", padx=40, pady=10)
        
        chk_start = ctk.CTkCheckBox(
            self.content_frame,
            text="Create a Start Menu shortcut",
            variable=self.create_start_menu_shortcut,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color="#cba6f7",
            hover_color="#b4befe"
        )
        chk_start.pack(anchor="w", padx=40, pady=10)
        
        self.next_btn.configure(text="Install")

    # --- STEP 4: INSTALLATION PROGRESS ---
    def show_progress_step(self):
        self.next_btn.pack_forget() # Hide next during install
        
        title = ctk.CTkLabel(
            self.content_frame,
            text="Installing Files",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color="#cba6f7"
        )
        title.pack(pady=(10, 10))
        
        self.progress_status = ctk.CTkLabel(
            self.content_frame,
            text="Extracting program archives...",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#cdd6f4"
        )
        self.progress_status.pack(pady=(20, 10))
        
        self.progress_bar = ctk.CTkProgressBar(
            self.content_frame,
            width=400,
            height=12,
            fg_color="#181825",
            progress_color="#cba6f7"
        )
        self.progress_bar.pack(pady=10)
        self.progress_bar.set(0)

    def start_installation(self):
        threading.Thread(target=self.install_worker, daemon=True).start()

    def install_worker(self):
        target_dir = self.install_dir.get()
        zip_name = "YT Downloader by Panes & Pixels.zip"
        
        # Determine path to zip (packaged inside MEIPASS or local build)
        try:
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.join(os.path.abspath("."), "dist")
            
        zip_path = os.path.join(base_path, zip_name)
        
        if not os.path.exists(zip_path):
            self.after(0, lambda: self.show_error(f"Error: Archive '{zip_name}' not found at {zip_path}"))
            return
            
        try:
            # 1. Create target folder
            if not os.path.exists(target_dir):
                os.makedirs(target_dir, exist_ok=True)
                
            # 2. Extract ZIP with progress simulation
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                file_list = zip_ref.namelist()
                total_files = len(file_list)
                
                for i, file in enumerate(file_list, 1):
                    zip_ref.extract(file, target_dir)
                    pct = i / total_files
                    self.after(0, lambda val=pct, f=file: self.update_progress(val, f"Extracting: {os.path.basename(f)}"))
            
            # 3. Create shortcuts
            app_folder_name = "YT Downloader by Panes & Pixels"
            exe_name = "YT Downloader by Panes & Pixels.exe"
            # ZIP extracts into a subfolder matching app_folder_name
            installed_exe_path = os.path.join(target_dir, app_folder_name, exe_name)
            installed_icon_path = os.path.join(target_dir, app_folder_name, "icon.ico")
            
            # If icon was extracted from the ZIP, use it; otherwise fallback
            if not os.path.exists(installed_icon_path):
                # Copy icon from installer
                try:
                    shutil.copy(resource_path("icon.ico"), installed_icon_path)
                except:
                    pass
            
            # Create Desktop Shortcut
            if self.create_desktop_shortcut.get():
                self.after(0, lambda: self.progress_status.configure(text="Creating Desktop shortcut..."))
                desktop_dir = get_special_folder("Desktop")
                if desktop_dir:
                    shortcut_path = os.path.join(desktop_dir, "YT Downloader by Panes & Pixels.lnk")
                    create_shortcut(installed_exe_path, shortcut_path, installed_icon_path)
                
            # Create Start Menu Shortcut
            if self.create_start_menu_shortcut.get():
                self.after(0, lambda: self.progress_status.configure(text="Creating Start Menu shortcut..."))
                start_menu_dir = get_special_folder("Programs")
                if start_menu_dir:
                    os.makedirs(start_menu_dir, exist_ok=True)
                    shortcut_path = os.path.join(start_menu_dir, "YT Downloader by Panes & Pixels.lnk")
                    create_shortcut(installed_exe_path, shortcut_path, installed_icon_path)
                
            # 4. Write Registry Keys for Control Panel (Add/Remove Programs)
            self.after(0, lambda: self.progress_status.configure(text="Registering with Windows..."))
            self.write_registry_entries(target_dir, installed_exe_path)
            
            self.zip_extracted_success = True
            self.after(0, self.go_to_complete)
            
        except Exception as e:
            self.after(0, lambda: self.show_error(f"Error during installation: {e}"))

    def write_registry_entries(self, install_dir, exe_path):
        try:
            # Determine directory size for EstimatedSize key
            total_size_bytes = 0
            for dirpath, dirnames, filenames in os.walk(install_dir):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    if os.path.exists(fp):
                        total_size_bytes += os.path.getsize(fp)
            size_kb = total_size_bytes // 1024
            
            # Path to registry
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\YT Downloader by Panes & Pixels"
            
            # Create key
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path)
            
            # Write values
            winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, "YT Downloader by Panes & Pixels")
            # Point uninstall string to the uninstall.exe inside app subfolder
            app_subfolder = os.path.join(install_dir, "YT Downloader by Panes & Pixels")
            winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ, f'"{os.path.join(app_subfolder, "uninstall.exe")}"')
            winreg.SetValueEx(key, "DisplayIcon", 0, winreg.REG_SZ, f'"{exe_path}"')
            winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, "Panes & Pixels")
            winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, "1.0.0")
            winreg.SetValueEx(key, "EstimatedSize", 0, winreg.REG_DWORD, size_kb)
            winreg.SetValueEx(key, "NoModify", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(key, "NoRepair", 0, winreg.REG_DWORD, 1)
            
            winreg.CloseKey(key)
        except Exception as e:
            print(f"Error writing registry keys: {e}")

    def update_progress(self, val, msg):
        self.progress_bar.set(val)
        self.progress_status.configure(text=msg)
        
    def show_error(self, err_msg):
        for widget in self.content_frame.winfo_children():
            widget.destroy()
            
        title = ctk.CTkLabel(
            self.content_frame,
            text="Installation Failed",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color="#f38ba8"
        )
        title.pack(pady=10)
        
        desc = ctk.CTkLabel(
            self.content_frame,
            text=err_msg,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#cdd6f4",
            wraplength=480,
            justify="center"
        )
        desc.pack(pady=20)
        
        self.next_btn.configure(text="Close", state="normal")
        self.next_btn.pack(side="right")
        self.current_step = 5
        self.zip_extracted_success = False

    def go_to_complete(self):
        self.current_step = 5
        self.show_step()

    # --- STEP 5: INSTALL COMPLETE ---
    def show_complete_step(self):
        self.next_btn.pack(side="right")
        self.next_btn.configure(text="Finish", state="normal")
        
        title = ctk.CTkLabel(
            self.content_frame,
            text="Installation Completed",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color="#a6e3a1"
        )
        title.pack(pady=(10, 10))
        
        desc = ctk.CTkLabel(
            self.content_frame,
            text="YT Downloader by Panes & Pixels has been successfully installed on your computer.\n\nClick Finish to exit this wizard.",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#cdd6f4",
            justify="center"
        )
        desc.pack(pady=20)
        
        self.launch_var = tk.BooleanVar(value=True)
        self.chk_launch = ctk.CTkCheckBox(
            self.content_frame,
            text="Launch YT Downloader now",
            variable=self.launch_var,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color="#a6e3a1",
            hover_color="#94e2d5"
        )
        self.chk_launch.pack(pady=10)

    def finish_installer(self):
        if self.zip_extracted_success and self.launch_var.get():
            app_folder = os.path.join(self.install_dir.get(), "YT Downloader by Panes & Pixels")
            target_exe = os.path.join(app_folder, "YT Downloader by Panes & Pixels.exe")
            if os.path.exists(target_exe):
                try:
                    subprocess.Popen([target_exe], cwd=app_folder)
                except Exception as e:
                    print(f"Error launching installed app: {e}")
        self.destroy()

if __name__ == "__main__":
    app = Installer()
    app.mainloop()
