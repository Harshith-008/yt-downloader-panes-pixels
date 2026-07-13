import os
import sys
import subprocess
import winreg
import tkinter as tk
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

class Uninstaller(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("YT Downloader - Uninstall")
        self.geometry("450x250")
        self.resizable(False, False)
        self.configure(fg_color="#11111b")
        
        # Load window icon
        try:
            icon_file = resource_path("icon.ico")
            if os.path.exists(icon_file):
                self.iconbitmap(icon_file)
        except:
            pass
            
        # Title
        self.title_lbl = ctk.CTkLabel(
            self,
            text="Uninstall YT Downloader",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color="#f38ba8"
        )
        self.title_lbl.pack(pady=(20, 10))
        
        # Message
        self.msg_lbl = ctk.CTkLabel(
            self,
            text="Are you sure you want to completely remove\nYT Downloader by Panes & Pixels and all of its components?",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#cdd6f4",
            justify="center"
        )
        self.msg_lbl.pack(padx=20, pady=10)
        
        # Status Label
        self.status_lbl = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#a6e3a1"
        )
        self.status_lbl.pack(pady=5)
        
        # Buttons Row
        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.pack(pady=15)
        
        self.yes_btn = ctk.CTkButton(
            self.btn_frame,
            text="Uninstall",
            width=120,
            height=35,
            fg_color="#f38ba8",
            hover_color="#eba0ac",
            text_color="#11111b",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            command=self.run_uninstall,
            corner_radius=6
        )
        self.yes_btn.pack(side="left", padx=10)
        
        self.no_btn = ctk.CTkButton(
            self.btn_frame,
            text="Cancel",
            width=100,
            height=35,
            fg_color="#313244",
            hover_color="#45475a",
            text_color="#cdd6f4",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            command=self.destroy,
            corner_radius=6
        )
        self.no_btn.pack(side="left", padx=10)
        
    def run_uninstall(self):
        self.yes_btn.configure(state="disabled")
        self.no_btn.configure(state="disabled")
        self.status_lbl.configure(text="Removing components...", text_color="#a6e3a1")
        self.update()
        
        # 1. Delete shortcuts
        desktop = get_special_folder("Desktop")
        start_menu = get_special_folder("Programs")
        
        shortcut_paths = []
        if desktop:
            shortcut_paths.append(os.path.join(desktop, "YT Downloader by Panes & Pixels.lnk"))
        if start_menu:
            shortcut_paths.append(os.path.join(start_menu, "YT Downloader by Panes & Pixels.lnk"))
        
        for path in shortcut_paths:
            if os.path.exists(path):
                try:
                    os.remove(path)
                except Exception as e:
                    print(f"Error removing shortcut {path}: {e}")
                    
        # 2. Delete registry key
        try:
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\YT Downloader by Panes & Pixels"
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key_path)
        except Exception as e:
            print(f"Error deleting registry key: {e}")
            
        # 3. Create self-deleting batch script in %TEMP%
        install_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        temp_dir = os.environ.get("TEMP", os.path.expanduser("~"))
        bat_path = os.path.join(temp_dir, "yt_downloader_cleanup.bat")
        
        bat_content = f"""@echo off
chcp 65001 > nul
timeout /t 2 /nobreak > NUL
rmdir /s /q "{install_dir}"
del "%~f0"
"""
        try:
            with open(bat_path, "w", encoding="utf-8") as f:
                f.write(bat_content)
                
            # Launch batch script in background without showing console window
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            subprocess.Popen([bat_path], startupinfo=startupinfo, creationflags=subprocess.CREATE_NO_WINDOW)
            
            # Terminate this application immediately
            self.quit()
        except Exception as e:
            self.status_lbl.configure(text=f"Error writing cleanup script: {e}", text_color="#f38ba8")
            self.yes_btn.configure(state="normal")
            self.no_btn.configure(state="normal")

if __name__ == "__main__":
    app = Uninstaller()
    app.mainloop()
