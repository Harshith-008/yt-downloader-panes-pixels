import os
import sys
import threading
import urllib.request
import io
import tkinter as tk
from tkinter import filedialog
from PIL import Image
import customtkinter as ctk

# Import our downloader functions
import downloader
import crypto_utils

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Set appearance and theme
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class ShortCard(ctk.CTkFrame):
    """A card displaying a YouTube Short with its thumbnail, title, and views."""
    def __init__(self, master, short_data, **kwargs):
        super().__init__(master, fg_color="#1e1e2e", corner_radius=10, border_width=1, border_color="#313244", **kwargs)
        self.short_data = short_data
        self.selected = tk.BooleanVar(value=True)
        
        # Configure layout
        self.grid_columnconfigure(0, minsize=40)  # Checkbox
        self.grid_columnconfigure(1, minsize=80)  # Thumbnail
        self.grid_columnconfigure(2, weight=1)    # Title and views
        
        # Checkbox
        self.checkbox = ctk.CTkCheckBox(
            self, 
            text="", 
            variable=self.selected, 
            width=24, 
            height=24,
            fg_color="#cba6f7",
            hover_color="#b4befe"
        )
        self.checkbox.grid(row=0, column=0, padx=(12, 6), pady=12, sticky="w")
        
        # Thumbnail placeholder / Image
        self.thumb_label = ctk.CTkLabel(self, text="Loading...", width=60, height=90, fg_color="#181825", corner_radius=6)
        self.thumb_label.grid(row=0, column=1, padx=6, pady=12, sticky="w")
        
        # Details Frame (Title + Views)
        self.details_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.details_frame.grid(row=0, column=2, padx=12, pady=12, sticky="nsew")
        self.details_frame.grid_columnconfigure(0, weight=1)
        
        # Title (wrapped)
        self.title_label = ctk.CTkLabel(
            self.details_frame, 
            text=short_data['title'], 
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            anchor="w",
            justify="left",
            wraplength=350,
            text_color="#cdd6f4"
        )
        self.title_label.grid(row=0, column=0, sticky="w", pady=(0, 4))
        
        # Views count formatted nicely (e.g. 1.2M views)
        views = short_data['views']
        if views >= 1_000_000_000:
            views_str = f"{views / 1_000_000_000:.1f}B views"
        elif views >= 1_000_000:
            views_str = f"{views / 1_000_000:.1f}M views"
        elif views >= 1_000:
            views_str = f"{views / 1_000:.1f}K views"
        else:
            views_str = f"{views} views"
            
        self.views_label = ctk.CTkLabel(
            self.details_frame,
            text=views_str,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#a6e3a1",
            anchor="w"
        )
        self.views_label.grid(row=1, column=0, sticky="w")
        
        self.zoom_win = None
        self.thumb_label.bind("<Enter>", self.show_zoom_popup)
        self.thumb_label.bind("<Leave>", self.hide_zoom_popup)
        
        # Load thumbnail asynchronously
        threading.Thread(target=self.load_thumbnail, daemon=True).start()
        
    def load_thumbnail(self):
        url = self.short_data.get('thumbnail')
        if not url:
            self.set_blank_thumb()
            return
            
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=8) as response:
                image_data = response.read()
            img = Image.open(io.BytesIO(image_data))
            
            w, h = img.size
            if w > h:
                new_w = int(h * 2/3)
                start_x = (w - new_w) // 2
                img = img.crop((start_x, 0, start_x + new_w, h))
            
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(60, 90))
            self.after(0, lambda: self.set_thumb_image(ctk_img))
            
        except Exception as e:
            print(f"Error loading thumbnail: {e}")
            self.after(0, self.set_blank_thumb)
            
    def set_thumb_image(self, ctk_img):
        self.thumb_label.configure(image=ctk_img, text="")
        
    def set_blank_thumb(self):
        blank_img = Image.new("RGB", (60, 90), color="#313244")
        ctk_img = ctk.CTkImage(light_image=blank_img, dark_image=blank_img, size=(60, 90))
        self.thumb_label.configure(image=ctk_img, text="")

    def show_zoom_popup(self, event):
        url = self.short_data.get('thumbnail')
        if not url:
            return
        x = self.winfo_pointerx() + 20
        y = self.winfo_pointery() - 100
        self.zoom_win = ctk.CTkToplevel(self)
        self.zoom_win.wm_overrideredirect(True)
        self.zoom_win.geometry(f"+{x}+{y}")
        self.zoom_win.configure(fg_color="#11111b")
        zoom_lbl = ctk.CTkLabel(self.zoom_win, text="Loading Preview...", text_color="#7f849c", font=ctk.CTkFont(family="Segoe UI", size=11))
        zoom_lbl.pack(padx=3, pady=3)
        def load_zoom():
            try:
                import urllib.request
                import io
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=5) as response:
                    img_data = response.read()
                img = Image.open(io.BytesIO(img_data))
                img = img.resize((200, 300), Image.Resampling.LANCZOS)
                photo = ctk.CTkImage(light_image=img, dark_image=img, size=(200, 300))
                if self.zoom_win and self.zoom_win.winfo_exists():
                    zoom_lbl.configure(image=photo, text="")
                    zoom_lbl.image = photo
            except Exception as e:
                if self.zoom_win and self.zoom_win.winfo_exists():
                    zoom_lbl.configure(text="Preview Error")
        threading.Thread(target=load_zoom, daemon=True).start()
        
    def hide_zoom_popup(self, event):
        if self.zoom_win:
            try:
                self.zoom_win.destroy()
            except:
                pass
            self.zoom_win = None

    def is_selected(self):
        return self.selected.get()


class ReelCard(ctk.CTkFrame):
    """A card displaying an Instagram Reel with its thumbnail, caption, and duration."""
    def __init__(self, master, reel_data, **kwargs):
        super().__init__(master, fg_color="#1e1e2e", corner_radius=10, border_width=1, border_color="#313244", **kwargs)
        self.reel_data = reel_data
        self.selected = tk.BooleanVar(value=True)
        
        self.grid_columnconfigure(0, minsize=40)  # Checkbox
        self.grid_columnconfigure(1, minsize=80)  # Thumbnail
        self.grid_columnconfigure(2, weight=1)    # Details
        
        # Checkbox
        self.checkbox = ctk.CTkCheckBox(
            self, 
            text="", 
            variable=self.selected, 
            width=24, 
            height=24,
            fg_color="#cba6f7",
            hover_color="#b4befe"
        )
        self.checkbox.grid(row=0, column=0, padx=(12, 6), pady=12, sticky="w")
        
        # Thumbnail placeholder / Image
        self.thumb_label = ctk.CTkLabel(self, text="Loading...", width=60, height=90, fg_color="#181825", corner_radius=6)
        self.thumb_label.grid(row=0, column=1, padx=6, pady=12, sticky="w")
        
        # Details Frame (Title + Uploader)
        self.details_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.details_frame.grid(row=0, column=2, padx=12, pady=12, sticky="nsew")
        self.details_frame.grid_columnconfigure(0, weight=1)
        
        # Title (wrapped)
        caption_text = reel_data['title'] if reel_data['title'] else "Instagram Reel"
        self.title_label = ctk.CTkLabel(
            self.details_frame, 
            text=caption_text, 
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            anchor="w",
            justify="left",
            wraplength=350,
            text_color="#cdd6f4"
        )
        self.title_label.grid(row=0, column=0, sticky="w", pady=(0, 4))
        
        # Uploader & Duration info
        duration_str = f"Duration: {reel_data['duration']}s" if reel_data['duration'] > 0 else ""
        uploader_str = f"@{reel_data['uploader']}" if reel_data['uploader'] != 'Unknown' else "Instagram Creator"
        details_text = f"{uploader_str} | {duration_str}" if duration_str else uploader_str
        
        self.views_label = ctk.CTkLabel(
            self.details_frame,
            text=details_text,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#a6e3a1",
            anchor="w"
        )
        self.views_label.grid(row=1, column=0, sticky="w")
        
        self.zoom_win = None
        self.thumb_label.bind("<Enter>", self.show_zoom_popup)
        self.thumb_label.bind("<Leave>", self.hide_zoom_popup)
        
        # Load thumbnail asynchronously
        threading.Thread(target=self.load_thumbnail, daemon=True).start()
        
    def load_thumbnail(self):
        url = self.reel_data.get('thumbnail')
        if not url:
            self.set_blank_thumb()
            return
            
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=8) as response:
                image_data = response.read()
            img = Image.open(io.BytesIO(image_data))
            
            # Crop to vertical aspect ratio
            w, h = img.size
            if w > h:
                new_w = int(h * 2/3)
                start_x = (w - new_w) // 2
                img = img.crop((start_x, 0, start_x + new_w, h))
            
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(60, 90))
            self.after(0, lambda: self.set_thumb_image(ctk_img))
            
        except Exception as e:
            print(f"Error loading Reel thumbnail: {e}")
            self.after(0, self.set_blank_thumb)
            
    def set_thumb_image(self, ctk_img):
        self.thumb_label.configure(image=ctk_img, text="")
        
    def set_blank_thumb(self):
        blank_img = Image.new("RGB", (60, 90), color="#313244")
        ctk_img = ctk.CTkImage(light_image=blank_img, dark_image=blank_img, size=(60, 90))
        self.thumb_label.configure(image=ctk_img, text="")

    def show_zoom_popup(self, event):
        url = self.reel_data.get('thumbnail')
        if not url:
            return
        x = self.winfo_pointerx() + 20
        y = self.winfo_pointery() - 100
        self.zoom_win = ctk.CTkToplevel(self)
        self.zoom_win.wm_overrideredirect(True)
        self.zoom_win.geometry(f"+{x}+{y}")
        self.zoom_win.configure(fg_color="#11111b")
        zoom_lbl = ctk.CTkLabel(self.zoom_win, text="Loading Preview...", text_color="#7f849c", font=ctk.CTkFont(family="Segoe UI", size=11))
        zoom_lbl.pack(padx=3, pady=3)
        def load_zoom():
            try:
                import urllib.request
                import io
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=5) as response:
                    img_data = response.read()
                img = Image.open(io.BytesIO(img_data))
                img = img.resize((200, 300), Image.Resampling.LANCZOS)
                photo = ctk.CTkImage(light_image=img, dark_image=img, size=(200, 300))
                if self.zoom_win and self.zoom_win.winfo_exists():
                    zoom_lbl.configure(image=photo, text="")
                    zoom_lbl.image = photo
            except Exception as e:
                if self.zoom_win and self.zoom_win.winfo_exists():
                    zoom_lbl.configure(text="Preview Error")
        threading.Thread(target=load_zoom, daemon=True).start()
        
    def hide_zoom_popup(self, event):
        if self.zoom_win:
            try:
                self.zoom_win.destroy()
            except:
                pass
            self.zoom_win = None

    def is_selected(self):
        return self.selected.get()


class VideoCard(ctk.CTkFrame):
    """A card displaying a YouTube Video with its thumbnail, title, views, uploader, and duration."""
    def __init__(self, parent, video_data):
        super().__init__(parent, fg_color="#1e1e2e", corner_radius=10, border_width=1, border_color="#313244")
        self.video_data = video_data
        
        self.grid_columnconfigure(1, weight=1)
        
        # Thumbnail Frame (standard 16:9 ratio)
        self.thumb_frame = ctk.CTkFrame(self, width=160, height=90, fg_color="#11111b", corner_radius=6)
        self.thumb_frame.grid(row=0, column=0, rowspan=4, padx=12, pady=12, sticky="nw")
        self.thumb_frame.grid_propagate(False)
        
        self.thumb_label = ctk.CTkLabel(self.thumb_frame, text="Loading...", text_color="#7f849c", font=ctk.CTkFont(family="Segoe UI", size=11))
        self.thumb_label.place(relx=0.5, rely=0.5, anchor="center")
        
        title_text = video_data.get('title', 'YouTube Video')
        self.title_lbl = ctk.CTkLabel(
            self,
            text=title_text,
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color="#cdd6f4",
            anchor="w",
            justify="left",
            wraplength=320
        )
        self.title_lbl.grid(row=0, column=1, padx=(5, 12), pady=(12, 2), sticky="w")
        
        uploader_text = f"Channel: {video_data.get('uploader', 'Unknown')}"
        self.uploader_lbl = ctk.CTkLabel(
            self,
            text=uploader_text,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#89b4fa",
            anchor="w"
        )
        self.uploader_lbl.grid(row=1, column=1, padx=(5, 12), pady=2, sticky="w")
        
        views = video_data.get('views', 0)
        if views >= 1_000_000:
            views_text = f"{views / 1_000_000:.1f}M views"
        elif views >= 1_000:
            views_text = f"{views / 1_000:.1f}K views"
        else:
            views_text = f"{views} views"
            
        duration = video_data.get('duration', 0)
        minutes = duration // 60
        seconds = duration % 60
        duration_text = f"{minutes:02d}:{seconds:02d}"
        
        meta_text = f"Views: {views_text}  |  Duration: {duration_text}"
        self.meta_lbl = ctk.CTkLabel(
            self,
            text=meta_text,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#a6adc8",
            anchor="w"
        )
        self.meta_lbl.grid(row=2, column=1, padx=(5, 12), pady=2, sticky="w")
        
        self.zoom_win = None
        self.thumb_label.bind("<Enter>", self.show_zoom_popup)
        self.thumb_label.bind("<Leave>", self.hide_zoom_popup)
        
        threading.Thread(target=self.load_thumbnail, daemon=True).start()
        
    def load_thumbnail(self):
        url = self.video_data.get('thumbnail')
        if not url:
            self.thumb_label.configure(text="No Image")
            return
            
        try:
            import urllib.request
            from PIL import Image
            import io
            
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as response:
                img_data = response.read()
                
            img = Image.open(io.BytesIO(img_data))
            img = img.resize((160, 90), Image.Resampling.LANCZOS)
            
            photo = ctk.CTkImage(light_image=img, dark_image=img, size=(160, 90))
            
            self.thumb_label.configure(image=photo, text="")
            self.thumb_label.image = photo
        except Exception as e:
            print(f"Error loading video thumbnail: {e}")
            self.thumb_label.configure(text="Error")

    def show_zoom_popup(self, event):
        url = self.video_data.get('thumbnail')
        if not url:
            return
        x = self.winfo_pointerx() + 20
        y = self.winfo_pointery() - 100
        self.zoom_win = ctk.CTkToplevel(self)
        self.zoom_win.wm_overrideredirect(True)
        self.zoom_win.geometry(f"+{x}+{y}")
        self.zoom_win.configure(fg_color="#11111b")
        zoom_lbl = ctk.CTkLabel(self.zoom_win, text="Loading Preview...", text_color="#7f849c", font=ctk.CTkFont(family="Segoe UI", size=11))
        zoom_lbl.pack(padx=3, pady=3)
        def load_zoom():
            try:
                import urllib.request
                import io
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=5) as response:
                    img_data = response.read()
                img = Image.open(io.BytesIO(img_data))
                img = img.resize((320, 180), Image.Resampling.LANCZOS)
                photo = ctk.CTkImage(light_image=img, dark_image=img, size=(320, 180))
                if self.zoom_win and self.zoom_win.winfo_exists():
                    zoom_lbl.configure(image=photo, text="")
                    zoom_lbl.image = photo
            except Exception as e:
                if self.zoom_win and self.zoom_win.winfo_exists():
                    zoom_lbl.configure(text="Preview Error")
        threading.Thread(target=load_zoom, daemon=True).start()
        
    def hide_zoom_popup(self, event):
        if self.zoom_win:
            try:
                self.zoom_win.destroy()
            except:
                pass
            self.zoom_win = None


def check_terms_accepted():
    config_dir = os.path.expanduser("~")
    config_path = os.path.join(config_dir, ".yt_shorts_downloader_accepted")
    return os.path.exists(config_path)

def set_terms_accepted():
    config_dir = os.path.expanduser("~")
    config_path = os.path.join(config_dir, ".yt_shorts_downloader_accepted")
    try:
        with open(config_path, "w") as f:
            f.write("accepted=true\n")
    except Exception as e:
        print(f"Error saving terms acceptance: {e}")

class TermsWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Terms & Conditions - YT Downloader by Panes & Pixels")
        self.geometry("500x580")
        self.resizable(False, False)
        self.configure(fg_color="#11111b")
        self.accepted = False
        
        # Load window icon
        try:
            icon_file = resource_path("icon.ico")
            if os.path.exists(icon_file):
                self.iconbitmap(icon_file)
        except Exception as e:
            print(f"Error setting TermsWindow icon: {e}")
            
        # Center window
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'+{x}+{y}')
        
        # Fade-in animation on startup
        self.attributes("-alpha", 0.0)
        self.fade_in()
        
        # UI Elements
        # Title
        self.title_label = ctk.CTkLabel(
            self,
            text="Terms & Conditions",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color="#cba6f7"
        )
        self.title_label.pack(pady=(15, 5))
        
        # Subtitle/Warning
        self.warning_label = ctk.CTkLabel(
            self,
            text="Please review and accept to continue",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#a6adc8"
        )
        self.warning_label.pack(pady=(0, 10))
        
        # Scrollable Textbox for terms
        self.textbox = ctk.CTkTextbox(
            self,
            width=440,
            height=260,
            fg_color="#181825",
            border_color="#313244",
            border_width=1,
            text_color="#cdd6f4",
            wrap="word",
            corner_radius=8,
            font=ctk.CTkFont(family="Segoe UI", size=12)
        )
        self.textbox.pack(padx=30, pady=5)
        
        terms_text = (
            "TERMS AND CONDITIONS & COPYRIGHT DISCLAIMER\n\n"
            "Please read this Disclaimer and Terms of Use carefully before using the YT Downloader by Panes & Pixels application.\n\n"
            "1. Educational and Personal Use Only\n"
            "This software is designed solely for educational, research, and personal, non-commercial use. You agree not to use this tool for commercial purposes or to infringe upon the rights of any content creators.\n\n"
            "2. Copyright Compliance\n"
            "Downloading copyrighted material from YouTube or Instagram without permission from the copyright owner is illegal and violates the respective platform's Terms of Service. You are solely responsible for ensuring that you have the legal right or permission to download any video/audio content.\n\n"
            "The developer of this application does not encourage, support, or condone copyright infringement. By using this tool, you warrant that you will only download content for which you own the copyright or have obtained explicit permission from the copyright holder.\n\n"
            "3. No Warranties and Limitation of Liability\n"
            "This software is provided 'as is' without warranty of any kind. The developer shall not be liable for any claims, damages, account suspensions, or legal actions resulting from the use or misuse of this tool."
        )
        self.textbox.insert("1.0", terms_text)
        self.textbox.configure(state="disabled") # Make read-only
        
        # Checkbox
        self.agree_var = tk.BooleanVar(value=False)
        self.checkbox = ctk.CTkCheckBox(
            self,
            text="I agree to the Terms of Service & Copyright Disclaimer",
            variable=self.agree_var,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            fg_color="#cba6f7",
            hover_color="#b4befe",
            command=self.toggle_accept_button
        )
        self.checkbox.pack(padx=30, pady=10, anchor="w")
        
        # Buttons frame
        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.pack(fill="x", padx=30, pady=(5, 5))
        self.btn_frame.grid_columnconfigure(0, weight=1)
        self.btn_frame.grid_columnconfigure(1, weight=1)
        
        self.decline_btn = ctk.CTkButton(
            self.btn_frame,
            text="Decline & Exit",
            fg_color="#f38ba8",
            hover_color="#eba0b2",
            text_color="#11111b",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            command=self.decline,
            corner_radius=6
        )
        self.decline_btn.grid(row=0, column=0, padx=(0, 10), sticky="ew")
        
        self.accept_btn = ctk.CTkButton(
            self.btn_frame,
            text="Accept & Continue",
            fg_color="#a6e3a1",
            hover_color="#94e2d5",
            text_color="#11111b",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            state="disabled",
            command=self.accept,
            corner_radius=6
        )
        self.accept_btn.grid(row=0, column=1, padx=(10, 0), sticky="ew")
        
        # Copyright Label
        self.copyright_label = ctk.CTkLabel(
            self,
            text="© Copyright by Panes & Pixels. All rights reserved.",
            font=ctk.CTkFont(family="Segoe UI", size=9),
            text_color="#585b70"
        )
        self.copyright_label.pack(side="bottom", pady=10)
        
    def fade_in(self, alpha=0.0):
        if alpha < 1.0:
            alpha += 0.08
            if alpha > 1.0:
                alpha = 1.0
            self.attributes("-alpha", alpha)
            self.after(16, lambda: self.fade_in(alpha))
            
    def toggle_accept_button(self):
        if self.agree_var.get():
            self.accept_btn.configure(state="normal")
        else:
            self.accept_btn.configure(state="disabled")
            
    def accept(self):
        self.accepted = True
        set_terms_accepted()
        self.destroy()
    def decline(self):
        self.accepted = False
        self.destroy()

class InstaLoginWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Instagram Login Settings")
        self.geometry("450x520")
        self.resizable(False, False)
        self.configure(fg_color="#11111b")
        self.transient(parent)
        self.grab_set()
        
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
            text="Instagram Authentication",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color="#f5c2e7"
        )
        self.title_lbl.pack(pady=(20, 10))
        
        # Info notice
        self.info_lbl = ctk.CTkLabel(
            self,
            text="Credentials are encrypted locally on your machine using\nWindows Data Protection (DPAPI). Only your Windows account can read them.",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#a6adc8",
            justify="center"
        )
        self.info_lbl.pack(padx=20, pady=(0, 20))
        
        # Username Field
        self.user_entry = ctk.CTkEntry(
            self,
            placeholder_text="Instagram Username...",
            width=320,
            height=35,
            fg_color="#1e1e2e",
            border_color="#313244",
            text_color="#cdd6f4",
            corner_radius=6,
            font=ctk.CTkFont(family="Segoe UI", size=12)
        )
        self.user_entry.pack(pady=10)
        
        # Password Field
        self.pass_entry = ctk.CTkEntry(
            self,
            placeholder_text="Instagram Password...",
            width=320,
            height=35,
            fg_color="#1e1e2e",
            border_color="#313244",
            text_color="#cdd6f4",
            show="*",
            corner_radius=6,
            font=ctk.CTkFont(family="Segoe UI", size=12)
        )
        self.pass_entry.pack(pady=10)
        
        # Proxy Field
        self.proxy_entry = ctk.CTkEntry(
            self,
            placeholder_text="Proxy (e.g. http://user:pass@host:port) (Optional)...",
            width=320,
            height=35,
            fg_color="#1e1e2e",
            border_color="#313244",
            text_color="#cdd6f4",
            corner_radius=6,
            font=ctk.CTkFont(family="Segoe UI", size=12)
        )
        self.proxy_entry.pack(pady=10)
        
        # Status Label
        self.status_lbl = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#a6e3a1"
        )
        self.status_lbl.pack(pady=5)
        
        # Buttons Row
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=15)
        
        self.save_btn = ctk.CTkButton(
            btn_frame,
            text="Save & Encrypt",
            width=130,
            height=35,
            fg_color="#a6e3a1",
            hover_color="#94e2d5",
            text_color="#11111b",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            command=self.save_creds,
            corner_radius=6
        )
        self.save_btn.pack(side="left", padx=10)
        
        self.clear_btn = ctk.CTkButton(
            btn_frame,
            text="Clear",
            width=100,
            height=35,
            fg_color="#f38ba8",
            hover_color="#eba0ac",
            text_color="#11111b",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            command=self.clear_creds,
            corner_radius=6
        )
        self.clear_btn.pack(side="left", padx=10)
        
        self.browser_btn = ctk.CTkButton(
            self,
            text="Login via Browser Window",
            width=260,
            height=35,
            fg_color="#cdd6f4",
            hover_color="#a6adc8",
            text_color="#11111b",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            command=self.login_via_browser,
            corner_radius=6
        )
        self.browser_btn.pack(pady=(5, 10))
        
        self.reset_history_btn = ctk.CTkButton(
            self,
            text="Reset Scrape History",
            width=260,
            height=35,
            fg_color="#f38ba8",
            hover_color="#eba0ac",
            text_color="#11111b",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            command=self.reset_scrape_history,
            corner_radius=6
        )
        self.reset_history_btn.pack(pady=(5, 15))
        
        # Load existing details if any
        self.load_creds()
        
    def load_creds(self):
        config_path = os.path.join(os.path.expanduser("~"), ".yt_shorts_downloader_insta")
        if os.path.exists(config_path):
            try:
                import crypto_utils
                with open(config_path, "r", encoding="utf-8") as f:
                    enc_str = f.read().strip()
                creds = crypto_utils.decrypt_credentials(enc_str)
                if creds:
                    user = creds[0]
                    pw = creds[1]
                    proxy = creds[2] if len(creds) > 2 else ""
                    self.user_entry.insert(0, user)
                    self.pass_entry.insert(0, pw)
                    self.proxy_entry.insert(0, proxy)
                    self.status_lbl.configure(text="Loaded saved credentials (encrypted).", text_color="#a6e3a1")
            except Exception as e:
                print(f"Error loading credentials: {e}")
                
    def reset_scrape_history(self):
        history_file = os.path.join(os.path.expanduser("~"), ".yt_shorts_downloader_history.json")
        if os.path.exists(history_file):
            try:
                os.remove(history_file)
                self.status_lbl.configure(text="Scrape history reset successfully!", text_color="#a6e3a1")
            except Exception as e:
                self.status_lbl.configure(text=f"Reset failed: {e}", text_color="#f38ba8")
        else:
            self.status_lbl.configure(text="No scrape history found to reset.", text_color="#f9e2af")

    def save_creds(self):
        user = self.user_entry.get().strip()
        pw = self.pass_entry.get().strip()
        proxy = self.proxy_entry.get().strip()
        if not user or not pw:
            self.status_lbl.configure(text="Please fill in both fields.", text_color="#f38ba8")
            return
            
        self.save_btn.configure(state="disabled")
        self.clear_btn.configure(state="disabled")
        self.status_lbl.configure(text="Connecting to Instagram...", text_color="#f9e2af")
        self.update()
        
        threading.Thread(target=self.login_worker, args=(user, pw, proxy), daemon=True).start()
        
    def login_worker(self, username, password, proxy):
        try:
            import downloader
            
            # Temporarily save credentials with proxy so downloader.instagram_web_login can read proxy config
            import crypto_utils
            enc_str = crypto_utils.encrypt_credentials(username, password, proxy)
            config_path = os.path.join(os.path.expanduser("~"), ".yt_shorts_downloader_insta")
            with open(config_path, "w", encoding="utf-8") as f:
                f.write(enc_str)
                
            try:
                # Use direct web login (same as browser)
                session = downloader.instagram_web_login(username, password)
                
                # Save the web session
                session_dir = os.path.join(
                    os.environ.get("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local")),
                    "Instaloader"
                )
                downloader.save_instagram_session(session, username, session_dir)
                
                self.after(0, lambda: self.login_success())
            except Exception as e:
                err_msg = str(e)
                if "TWO_FACTOR_REQUIRED" in err_msg:
                    # Fall back to instaloader for 2FA flow
                    try:
                        import instaloader
                        from instaloader.exceptions import TwoFactorAuthRequiredException
                        L = instaloader.Instaloader(
                            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, size Gecko) Chrome/126.0.0.0 Safari/537.36'
                        )
                        if proxy:
                            L.context._session.proxies = {"http": proxy, "https": proxy}
                        try:
                            L.login(username, password)
                        except TwoFactorAuthRequiredException:
                            self.after(0, lambda: self.handle_2fa(L, username, password, proxy))
                            return
                    except Exception:
                        pass
                    self.after(0, lambda: self.login_failed("2FA required but handler failed. Please try again."))
                else:
                    self.after(0, lambda err=e: self.login_failed(f"Login failed: {err}"))
        except Exception as e:
            self.after(0, lambda err=e: self.login_failed(f"Error: {err}"))
            
    def handle_2fa(self, L, username, password, proxy):
        dialog = ctk.CTkInputDialog(
            text="Two-Factor Authentication is required.\nPlease enter the code sent to your device:",
            title="Instagram 2FA"
        )
        dialog.transient(self)
        dialog.grab_set()
        
        code = dialog.get_input()
        if not code:
            self.login_failed("2FA code required. Login aborted.")
            return
            
        self.status_lbl.configure(text="Verifying 2FA code...", text_color="#f9e2af")
        self.update()
        
        threading.Thread(target=self.verify_2fa_worker, args=(L, username, password, code, proxy), daemon=True).start()
        
    def verify_2fa_worker(self, L, username, password, code, proxy):
        try:
            session_file = os.path.join(
                os.environ.get("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local")),
                "Instaloader",
                f"session-{username}"
            )
            os.makedirs(os.path.dirname(session_file), exist_ok=True)
            
            L.two_factor_login(code)
            L.save_session_to_file(filename=session_file)
            
            import crypto_utils
            enc_str = crypto_utils.encrypt_credentials(username, password, proxy)
            config_path = os.path.join(os.path.expanduser("~"), ".yt_shorts_downloader_insta")
            with open(config_path, "w", encoding="utf-8") as f:
                f.write(enc_str)
                
            self.after(0, lambda: self.login_success())
        except Exception as e:
            self.after(0, lambda err=e: self.login_failed(f"2FA failed: {err}"))
            
    def login_success(self):
        self.save_btn.configure(state="normal")
        self.clear_btn.configure(state="normal")
        self.status_lbl.configure(text="Connected and saved successfully!", text_color="#a6e3a1")
        
    def login_failed(self, msg):
        self.save_btn.configure(state="normal")
        self.clear_btn.configure(state="normal")
        # Truncate message if it is too long
        if len(msg) > 50:
            msg = msg[:47] + "..."
        self.status_lbl.configure(text=msg, text_color="#f38ba8")
            
    def clear_creds(self):
        config_path = os.path.join(os.path.expanduser("~"), ".yt_shorts_downloader_insta")
        if os.path.exists(config_path):
            try:
                os.remove(config_path)
            except:
                pass
        self.user_entry.delete(0, "end")
        self.pass_entry.delete(0, "end")
        self.proxy_entry.delete(0, "end")
        self.status_lbl.configure(text="Cleared credentials.", text_color="#f9e2af")
        
    def login_via_browser(self):
        user = self.user_entry.get().strip()
        proxy = self.proxy_entry.get().strip()
        if not user:
            self.status_lbl.configure(text="Please enter your Instagram username first.", text_color="#f38ba8")
            return
            
        self.browser_btn.configure(state="disabled")
        self.save_btn.configure(state="disabled")
        self.clear_btn.configure(state="disabled")
        self.status_lbl.configure(text="Opening browser login window...", text_color="#f9e2af")
        self.update()
        
        # Save temporary credentials file so proxy is written to disk for helper webview process
        import crypto_utils
        enc_str = crypto_utils.encrypt_credentials(user, "temp_browser", proxy)
        config_path = os.path.join(os.path.expanduser("~"), ".yt_shorts_downloader_insta")
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                f.write(enc_str)
        except:
            pass
            
        threading.Thread(target=self.browser_login_worker, args=(user, proxy), daemon=True).start()
        
    def browser_login_worker(self, username, proxy):
        try:
            import subprocess
            import sys
            import json
            import os
            import requests
            import downloader
            import crypto_utils
            
            temp_path = os.path.join(os.path.expanduser("~"), ".yt_shorts_downloader_insta_temp_cookies.json")
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass
            
            # Find app.py path
            app_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
            
            # Run helper script in a separate process to avoid thread conflicts
            # Use subprocess to run the helper cleanly on its own main thread
            if getattr(sys, 'frozen', False):
                cmd = [sys.executable, "--webview-login"]
            else:
                app_path = os.path.join(app_dir, "app.py")
                cmd = [sys.executable, app_path, "--webview-login"]
                
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if os.path.exists(temp_path):
                self.after(0, lambda: self.status_lbl.configure(text="Verifying session...", text_color="#f9e2af"))
                
                with open(temp_path, "r", encoding="utf-8") as f:
                    cookies_dict = json.load(f)
                
                try:
                    os.remove(temp_path)
                except:
                    pass
                
                session = requests.Session()
                if proxy:
                    session.proxies = {"http": proxy, "https": proxy}
                    
                session.headers.update({
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
                })
                for name, info in cookies_dict.items():
                    session.cookies.set(name, info["value"], domain=info["domain"], path=info["path"])
                
                if downloader.verify_instagram_session(session):
                    # Save web session JSON
                    session_dir = os.path.join(
                        os.environ.get("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local")),
                        "Instaloader"
                    )
                    downloader.save_instagram_session(session, username, session_dir)
                    
                    # Save credentials with dummy password
                    enc_str = crypto_utils.encrypt_credentials(username, "browser_session", proxy)
                    config_path = os.path.join(os.path.expanduser("~"), ".yt_shorts_downloader_insta")
                    with open(config_path, "w", encoding="utf-8") as f:
                        f.write(enc_str)
                        
                    self.after(0, lambda: self.browser_login_success())
                else:
                    self.after(0, lambda: self.browser_login_failed("Verification failed. Session is invalid."))
            else:
                self.after(0, lambda: self.browser_login_failed("Login cancelled or failed."))
        except Exception as e:
            self.after(0, lambda err=e: self.browser_login_failed(f"Error: {err}"))
            
    def browser_login_success(self):
        self.browser_btn.configure(state="normal")
        self.save_btn.configure(state="normal")
        self.clear_btn.configure(state="normal")
        self.status_lbl.configure(text="Connected via browser successfully!", text_color="#a6e3a1")
        
    def browser_login_failed(self, msg):
        self.browser_btn.configure(state="normal")
        self.save_btn.configure(state="normal")
        self.clear_btn.configure(state="normal")
        if len(msg) > 50:
            msg = msg[:47] + "..."
        self.status_lbl.configure(text=msg, text_color="#f38ba8")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Configure window
        self.title("YT Downloader by Panes & Pixels")
        self.geometry("640x740")
        self.minsize(580, 620)
        self.configure(fg_color="#11111b")
        
        # Load window icon
        try:
            icon_file = resource_path("icon.ico")
            if os.path.exists(icon_file):
                self.iconbitmap(icon_file)
        except Exception as e:
            print(f"Error setting App window icon: {e}")
            
        # Smooth fade-in animation on startup
        self.attributes("-alpha", 0.0)
        self.fade_in()
        
        # YouTube Downloader State Variables
        self.shorts_list = []
        self.cards = []
        self.hash_shorts_list = []
        self.hash_cards = []
        self.video_data = None
        self.video_card = None
        
        # Instagram Downloader State Variables
        self.insta_reel_data = None
        self.insta_cards = []
        self.insta_profile_cards = []
        
        self.default_download_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        self.download_dir = tk.StringVar(value=self.default_download_dir)
        self.is_processing = False
        
        # Parallel queue manager state
        import concurrent.futures
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=3)
        self.queue_tasks = {}
        self.task_counter = 0
        
        # Design UI components
        self.build_ui()
        
    def fade_in(self, alpha=0.0):
        if alpha < 1.0:
            alpha += 0.08
            if alpha > 1.0:
                alpha = 1.0
            self.attributes("-alpha", alpha)
            self.after(16, lambda: self.fade_in(alpha))
            
    def build_ui(self):
        # We create 4 separate containers for different screens
        self.dashboard_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.yt_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.insta_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.scheduler_frame = ctk.CTkFrame(self, fg_color="transparent")
        
        # Build queue frame (hidden by default)
        self.queue_frame = ctk.CTkFrame(self, fg_color="#181825", border_width=1, border_color="#313244", height=130, corner_radius=12)
        
        queue_lbl = ctk.CTkLabel(
            self.queue_frame,
            text="⚡ Active Download Queue",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#cba6f7"
        )
        queue_lbl.pack(anchor="w", padx=15, pady=(8, 2))
        
        self.queue_scroll = ctk.CTkScrollableFrame(self.queue_frame, fg_color="transparent", height=80)
        self.queue_scroll.pack(fill="both", expand=True, padx=10, pady=(2, 8))
        
        self.setup_dashboard()
        self.setup_youtube_ui()
        self.setup_instagram_ui()
        self.setup_scheduler_ui()
        
        # Start background scheduler loop
        self.start_scheduler_loop()
        
        # Start at dashboard
        self.show_dashboard()
        
    def show_dashboard(self):
        self.yt_frame.pack_forget()
        self.insta_frame.pack_forget()
        self.dashboard_frame.pack(fill="both", expand=True, padx=5, pady=5)
        self.attributes("-alpha", 0.5)
        self.fade_in(0.5)
        
    def show_youtube_downloader(self):
        self.dashboard_frame.pack_forget()
        self.yt_frame.pack(fill="both", expand=True, padx=5, pady=5)
        self.attributes("-alpha", 0.5)
        self.fade_in(0.5)
        
    def show_instagram_downloader(self):
        self.dashboard_frame.pack_forget()
        self.insta_frame.pack(fill="both", expand=True, padx=5, pady=5)
        self.attributes("-alpha", 0.5)
        self.fade_in(0.5)
        
    def setup_dashboard(self):
        # Header
        header = ctk.CTkLabel(
            self.dashboard_frame,
            text="YT Downloader",
            font=ctk.CTkFont(family="Segoe UI", size=32, weight="bold"),
            text_color="#cba6f7"
        )
        header.pack(pady=(60, 5))
        
        brand = ctk.CTkLabel(
            self.dashboard_frame,
            text="by Panes & Pixels",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color="#89b4fa"
        )
        brand.pack(pady=(0, 10))
        
        sub = ctk.CTkLabel(
            self.dashboard_frame,
            text="Select a platform to start downloading",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#a6adc8"
        )
        sub.pack(pady=(0, 50))
        
        # Grid frame for options
        grid_frame = ctk.CTkFrame(self.dashboard_frame, fg_color="transparent")
        grid_frame.pack(fill="x", padx=40, pady=10)
        grid_frame.grid_columnconfigure(0, weight=1)
        grid_frame.grid_columnconfigure(1, weight=1)
        
        # YouTube Card Button
        self.yt_card = ctk.CTkButton(
            grid_frame,
            text="YouTube Shorts\n\nDownload top channel Shorts",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            fg_color="#1e1e2e",
            hover_color="#f38ba8", # Red highlight
            text_color="#cdd6f4",
            height=180,
            corner_radius=12,
            border_width=1,
            border_color="#313244",
            command=self.show_youtube_downloader
        )
        self.yt_card.grid(row=0, column=0, padx=(0, 15), sticky="ew")
        
        # Instagram Card Button
        self.insta_card = ctk.CTkButton(
            grid_frame,
            text="Instagram Reels\n\nDownload Reels via links",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            fg_color="#1e1e2e",
            hover_color="#f5c2e7", # Pinkish highlight
            text_color="#cdd6f4",
            height=180,
            corner_radius=12,
            border_width=1,
            border_color="#313244",
            command=self.show_instagram_downloader
        )
        self.insta_card.grid(row=0, column=1, padx=(15, 0), sticky="ew")
        
        # Scheduler Card Button
        self.scheduler_card = ctk.CTkButton(
            grid_frame,
            text="📅 Scheduler & Publisher\n\nSchedule and auto-publish content",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            fg_color="#1e1e2e",
            hover_color="#cba6f7", # Purple highlight
            text_color="#cdd6f4",
            height=100,
            corner_radius=12,
            border_width=1,
            border_color="#313244",
            command=self.show_scheduler
        )
        self.scheduler_card.grid(row=1, column=0, columnspan=2, pady=(20, 0), sticky="ew")
        
        # Clipboard switch
        self.monitor_clipboard = tk.BooleanVar(value=False)
        self.clipboard_switch = ctk.CTkSwitch(
            self.dashboard_frame,
            text="Auto-Detect Copied Video Links",
            variable=self.monitor_clipboard,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            progress_color="#cba6f7",
            text_color="#cdd6f4",
            command=self.toggle_clipboard_monitor
        )
        self.clipboard_switch.pack(pady=(40, 10))
        
        # Bottom Copyright
        copyright_lbl = ctk.CTkLabel(
            self.dashboard_frame,
            text="© Copyright by Panes & Pixels. All rights reserved.",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color="#585b70"
        )
        copyright_lbl.pack(side="bottom", pady=20)

    def setup_youtube_ui(self):
        # Header navigation row
        nav_frame = ctk.CTkFrame(self.yt_frame, fg_color="transparent")
        nav_frame.pack(fill="x", padx=20, pady=(15, 5))
        
        back_btn = ctk.CTkButton(
            nav_frame,
            text="← Dashboard",
            width=100,
            height=32,
            fg_color="#313244",
            hover_color="#45475a",
            text_color="#cdd6f4",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            command=self.show_dashboard,
            corner_radius=6
        )
        back_btn.pack(side="left")
        
        # Headers inside frame
        yt_title = ctk.CTkLabel(
            self.yt_frame,
            text="YouTube Downloader Suite",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color="#cba6f7"
        )
        yt_title.pack(padx=20, pady=(10, 2))
        
        yt_sub = ctk.CTkLabel(
            self.yt_frame,
            text="Download standard videos, channel Shorts, or search by hashtags",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#a6adc8"
        )
        yt_sub.pack(padx=20, pady=(0, 10))
        
        # Segmented Button for tabs
        self.yt_tab_control = ctk.CTkSegmentedButton(
            self.yt_frame,
            values=["Channel Shorts", "Hashtag Shorts", "Video Downloader"],
            command=self.on_yt_tab_changed,
            fg_color="#181825",
            selected_color="#cba6f7",
            unselected_color="#1e1e2e",
            text_color="#cdd6f4",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")
        )
        self.yt_tab_control.pack(padx=20, pady=(0, 10), fill="x")
        self.yt_tab_control.set("Channel Shorts")
        
        # Container frames for each tab
        self.tab_channel_frame = ctk.CTkFrame(self.yt_frame, fg_color="transparent")
        self.tab_hashtag_frame = ctk.CTkFrame(self.yt_frame, fg_color="transparent")
        self.tab_video_frame = ctk.CTkFrame(self.yt_frame, fg_color="transparent")
        
        # --- TAB 1: CHANNEL SHORTS WIDGETS ---
        search_frame = ctk.CTkFrame(self.tab_channel_frame, fg_color="transparent")
        search_frame.pack(fill="x", padx=20, pady=10)
        search_frame.grid_columnconfigure(0, weight=1)
        
        self.url_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="Enter YouTube channel link (e.g. @MrBeast)...",
            height=45,
            fg_color="#1e1e2e",
            border_color="#313244",
            text_color="#cdd6f4",
            placeholder_text_color="#7f849c",
            corner_radius=8,
            font=ctk.CTkFont(family="Segoe UI", size=13)
        )
        self.url_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.url_entry.bind("<Return>", lambda e: self.start_fetch())
        
        self.fetch_btn = ctk.CTkButton(
            search_frame,
            text="Analyze Channel",
            height=45,
            fg_color="#89b4fa",
            hover_color="#b4befe",
            text_color="#11111b",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            command=self.start_fetch,
            corner_radius=8
        )
        self.fetch_btn.grid(row=0, column=1, sticky="ns")
        
        self.status_label = ctk.CTkLabel(
            self.tab_channel_frame, 
            text="Ready to search.", 
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#a6adc8"
        )
        self.status_label.pack(padx=20, pady=(5, 5))
        
        self.fetch_progress = ctk.CTkProgressBar(
            self.tab_channel_frame, 
            height=6, 
            fg_color="#1e1e2e", 
            progress_color="#f9e2af"
        )
        self.fetch_progress.pack(fill="x", padx=20, pady=(0, 10))
        self.fetch_progress.set(0)
        
        self.scroll_frame = ctk.CTkScrollableFrame(
            self.tab_channel_frame, 
            fg_color="#181825", 
            border_color="#313244", 
            border_width=1,
            corner_radius=10
        )
        self.scroll_frame.pack(fill="both", expand=True, padx=20, pady=5)
        
        self.placeholder_label = ctk.CTkLabel(
            self.scroll_frame,
            text="Paste a YouTube channel link above\nand click 'Analyze Channel' to find top Shorts.",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color="#7f849c",
            justify="center"
        )
        self.placeholder_label.pack(expand=True, fill="both", pady=80)
        
        # --- TAB 2: HASHTAG SHORTS WIDGETS ---
        hash_search_frame = ctk.CTkFrame(self.tab_hashtag_frame, fg_color="transparent")
        hash_search_frame.pack(fill="x", padx=20, pady=10)
        hash_search_frame.grid_columnconfigure(0, weight=1)
        
        self.hash_entry = ctk.CTkEntry(
            hash_search_frame,
            placeholder_text="Enter hashtags separated by commas (e.g. funny, trending, diy)...",
            height=45,
            fg_color="#1e1e2e",
            border_color="#313244",
            text_color="#cdd6f4",
            placeholder_text_color="#7f849c",
            corner_radius=8,
            font=ctk.CTkFont(family="Segoe UI", size=13)
        )
        self.hash_entry.grid(row=0, column=0, columnspan=2, sticky="ew", padx=(0, 0), pady=(0, 10))
        self.hash_entry.bind("<Return>", lambda e: self.start_hashtag_fetch())
        
        self.sort_option = ctk.CTkOptionMenu(
            hash_search_frame,
            values=["Views (High to Low)", "Views (Low to High)", "Title (A-Z)", "Duration (Short to Long)"],
            height=35,
            fg_color="#313244",
            button_color="#45475a",
            button_hover_color="#585b70",
            text_color="#cdd6f4",
            dropdown_fg_color="#1e1e2e",
            dropdown_hover_color="#313244",
            dropdown_text_color="#cdd6f4",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")
        )
        self.sort_option.grid(row=1, column=0, sticky="ew", padx=(0, 10))
        self.sort_option.set("Views (High to Low)")
        
        self.hash_fetch_btn = ctk.CTkButton(
            hash_search_frame,
            text="Search Hashtags",
            height=35,
            fg_color="#cba6f7",
            hover_color="#b4befe",
            text_color="#11111b",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            command=self.start_hashtag_fetch,
            corner_radius=8
        )
        self.hash_fetch_btn.grid(row=1, column=1, sticky="ew")
        
        self.hash_status_label = ctk.CTkLabel(
            self.tab_hashtag_frame, 
            text="Ready to search.", 
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#a6adc8"
        )
        self.hash_status_label.pack(padx=20, pady=(5, 5))
        
        self.hash_progress = ctk.CTkProgressBar(
            self.tab_hashtag_frame, 
            height=6, 
            fg_color="#1e1e2e", 
            progress_color="#f9e2af"
        )
        self.hash_progress.pack(fill="x", padx=20, pady=(0, 10))
        self.hash_progress.set(0)
        
        self.hash_scroll_frame = ctk.CTkScrollableFrame(
            self.tab_hashtag_frame, 
            fg_color="#181825", 
            border_color="#313244", 
            border_width=1,
            corner_radius=10
        )
        self.hash_scroll_frame.pack(fill="both", expand=True, padx=20, pady=5)
        
        self.hash_placeholder_label = ctk.CTkLabel(
            self.hash_scroll_frame,
            text="Enter hashtags above separated by commas\nand click 'Search Hashtags' to find top Shorts.",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color="#7f849c",
            justify="center"
        )
        self.hash_placeholder_label.pack(expand=True, fill="both", pady=80)
        
        # --- TAB 3: VIDEO DOWNLOADER WIDGETS ---
        vid_search_frame = ctk.CTkFrame(self.tab_video_frame, fg_color="transparent")
        vid_search_frame.pack(fill="x", padx=20, pady=10)
        vid_search_frame.grid_columnconfigure(0, weight=1)
        
        self.vid_url_entry = ctk.CTkEntry(
            vid_search_frame,
            placeholder_text="Enter standard YouTube video URL...",
            height=45,
            fg_color="#1e1e2e",
            border_color="#313244",
            text_color="#cdd6f4",
            placeholder_text_color="#7f849c",
            corner_radius=8,
            font=ctk.CTkFont(family="Segoe UI", size=13)
        )
        self.vid_url_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.vid_url_entry.bind("<Return>", lambda e: self.start_video_fetch())
        
        self.vid_fetch_btn = ctk.CTkButton(
            vid_search_frame,
            text="Fetch Info",
            height=45,
            fg_color="#89b4fa",
            hover_color="#b4befe",
            text_color="#11111b",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            command=self.start_video_fetch,
            corner_radius=8
        )
        self.vid_fetch_btn.grid(row=0, column=1, sticky="ns")
        
        self.vid_status_label = ctk.CTkLabel(
            self.tab_video_frame, 
            text="Ready to search.", 
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#a6adc8"
        )
        self.vid_status_label.pack(padx=20, pady=(5, 5))
        
        self.vid_progress = ctk.CTkProgressBar(
            self.tab_video_frame, 
            height=6, 
            fg_color="#1e1e2e", 
            progress_color="#f9e2af"
        )
        self.vid_progress.pack(fill="x", padx=20, pady=(0, 10))
        self.vid_progress.set(0)
        
        self.vid_card_frame = ctk.CTkFrame(
            self.tab_video_frame, 
            fg_color="#181825", 
            border_color="#313244", 
            border_width=1,
            corner_radius=10
        )
        self.vid_card_frame.pack(fill="both", expand=True, padx=20, pady=5)
        
        self.vid_placeholder_label = ctk.CTkLabel(
            self.vid_card_frame,
            text="Paste a YouTube video URL above\nand click 'Fetch Info' to load video details.",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color="#7f849c",
            justify="center"
        )
        self.vid_placeholder_label.pack(expand=True, fill="both", pady=100)
        
        # Pack the default frame
        self.tab_channel_frame.pack(fill="both", expand=True)
        
        # --- BOTTOM CONTROLS (Common to all tabs) ---
        self.controls_frame = ctk.CTkFrame(self.yt_frame, fg_color="#1e1e2e", corner_radius=10, border_width=1, border_color="#313244")
        self.controls_frame.pack(fill="x", padx=20, pady=(5, 5))
        self.controls_frame.grid_columnconfigure(1, weight=1)
        
        dir_title = ctk.CTkLabel(
            self.controls_frame, 
            text="Save to:", 
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#a6adc8"
        )
        dir_title.grid(row=0, column=0, padx=(15, 5), pady=(12, 6), sticky="w")
        
        dir_entry = ctk.CTkEntry(
            self.controls_frame,
            textvariable=self.download_dir,
            height=30,
            fg_color="#181825",
            border_color="#313244",
            text_color="#cdd6f4",
            corner_radius=6,
            font=ctk.CTkFont(family="Segoe UI", size=12)
        )
        dir_entry.grid(row=0, column=1, padx=5, pady=(12, 6), sticky="ew")
        
        browse_btn = ctk.CTkButton(
            self.controls_frame,
            text="Browse...",
            width=80,
            height=30,
            fg_color="#45475a",
            hover_color="#585b70",
            text_color="#cdd6f4",
            command=self.browse_folder,
            corner_radius=6,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")
        )
        browse_btn.grid(row=0, column=2, padx=(5, 15), pady=(12, 6))
        
        # Format preset selector for YouTube
        format_lbl = ctk.CTkLabel(
            self.controls_frame,
            text="Format:",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#a6adc8"
        )
        format_lbl.grid(row=1, column=0, padx=(15, 5), pady=(6, 6), sticky="w")
        
        self.yt_format_option = ctk.CTkOptionMenu(
            self.controls_frame,
            values=["Best Quality (Video)", "1080p (Video)", "720p (Video)", "480p (Video)", "Audio Only (MP3)"],
            height=30,
            fg_color="#313244",
            button_color="#45475a",
            button_hover_color="#585b70",
            text_color="#cdd6f4",
            dropdown_fg_color="#1e1e2e",
            dropdown_hover_color="#313244",
            dropdown_text_color="#cdd6f4",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")
        )
        self.yt_format_option.grid(row=1, column=1, columnspan=2, padx=(5, 15), pady=(6, 6), sticky="ew")
        self.yt_format_option.set("Best Quality (Video)")
        
        self.organize_subfolders = ctk.CTkCheckBox(
            self.controls_frame,
            text="Organize into Creator Subfolders",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#cdd6f4",
            fg_color="#a6e3a1",
            hover_color="#94e2d5",
            border_color="#45475a"
        )
        self.organize_subfolders.grid(row=2, column=0, columnspan=3, padx=15, pady=(4, 4), sticky="w")
        self.organize_subfolders.select()
        
        self.download_btn = ctk.CTkButton(
            self.controls_frame,
            text="Download Selected Shorts",
            height=45,
            fg_color="#a6e3a1",
            hover_color="#94e2d5",
            text_color="#11111b",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            state="disabled",
            command=self.start_download,
            corner_radius=8
        )
        self.download_btn.grid(row=3, column=0, columnspan=3, padx=15, pady=(6, 12), sticky="ew")
        
        self.down_status_label = ctk.CTkLabel(
            self.controls_frame,
            text="",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#f5e0dc"
        )
        self.down_status_label.grid(row=4, column=0, columnspan=3, padx=15, pady=(0, 2), sticky="ew")
        self.down_status_label.grid_remove()
        
        self.down_progress = ctk.CTkProgressBar(
            self.controls_frame,
            height=6,
            fg_color="#181825",
            progress_color="#a6e3a1"
        )
        self.down_progress.grid(row=5, column=0, columnspan=3, padx=15, pady=(0, 15), sticky="ew")
        self.down_progress.set(0)
        self.down_progress.grid_remove()

        copyright_lbl = ctk.CTkLabel(
            self.yt_frame,
            text="© Copyright by Panes & Pixels. All rights reserved.",
            font=ctk.CTkFont(family="Segoe UI", size=9),
            text_color="#585b70"
        )
        copyright_lbl.pack(side="bottom", pady=(5, 10))

    def setup_instagram_ui(self):
        # Header navigation row
        nav_frame = ctk.CTkFrame(self.insta_frame, fg_color="transparent")
        nav_frame.pack(fill="x", padx=20, pady=(15, 5))
        
        back_btn = ctk.CTkButton(
            nav_frame,
            text="← Dashboard",
            width=100,
            height=32,
            fg_color="#313244",
            hover_color="#45475a",
            text_color="#cdd6f4",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            command=self.show_dashboard,
            corner_radius=6
        )
        back_btn.pack(side="left")
        
        self.settings_btn = ctk.CTkButton(
            nav_frame,
            text="⚙️ Login Settings",
            width=120,
            height=32,
            fg_color="#313244",
            hover_color="#45475a",
            text_color="#cdd6f4",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            command=self.open_insta_login_window,
            corner_radius=6
        )
        self.settings_btn.pack(side="right")
        
        # Headers inside frame
        insta_title = ctk.CTkLabel(
            self.insta_frame,
            text="Instagram Downloader Suite",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color="#cba6f7"
        )
        insta_title.pack(padx=20, pady=(10, 2))
        
        insta_sub = ctk.CTkLabel(
            self.insta_frame,
            text="Download single Reels or scrape recent videos from any public profile",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#a6adc8"
        )
        insta_sub.pack(padx=20, pady=(0, 10))
        
        # Segmented Button for tabs
        self.insta_tab_control = ctk.CTkSegmentedButton(
            self.insta_frame,
            values=["Single Reel", "Profile Scraper"],
            command=self.on_insta_tab_changed,
            fg_color="#181825",
            selected_color="#cba6f7",
            unselected_color="#1e1e2e",
            text_color="#cdd6f4",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")
        )
        self.insta_tab_control.pack(padx=20, pady=(0, 10), fill="x")
        self.insta_tab_control.set("Single Reel")
        
        # Container frames for each tab
        self.tab_insta_single_frame = ctk.CTkFrame(self.insta_frame, fg_color="transparent")
        self.tab_insta_profile_frame = ctk.CTkFrame(self.insta_frame, fg_color="transparent")
        
        # --- TAB 1: SINGLE REEL WIDGETS ---
        self.insta_search_frame = ctk.CTkFrame(self.tab_insta_single_frame, fg_color="transparent")
        self.insta_search_frame.pack(fill="x", padx=20, pady=10)
        self.insta_search_frame.grid_columnconfigure(0, weight=1)
        
        self.insta_url_entry = ctk.CTkEntry(
            self.insta_search_frame,
            placeholder_text="Paste Instagram Reel link (e.g. instagram.com/reel/...)...",
            height=45,
            fg_color="#1e1e2e",
            border_color="#313244",
            text_color="#cdd6f4",
            placeholder_text_color="#7f849c",
            corner_radius=8,
            font=ctk.CTkFont(family="Segoe UI", size=13)
        )
        self.insta_url_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.insta_url_entry.bind("<Return>", lambda e: self.start_insta_fetch())
        
        self.insta_fetch_btn = ctk.CTkButton(
            self.insta_search_frame,
            text="Analyze Reel",
            height=45,
            fg_color="#89b4fa",
            hover_color="#b4befe",
            text_color="#11111b",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            command=self.start_insta_fetch,
            corner_radius=8
        )
        self.insta_fetch_btn.grid(row=0, column=1, sticky="ns")
        
        self.insta_status_label = ctk.CTkLabel(
            self.tab_insta_single_frame, 
            text="Ready to search.", 
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#a6adc8"
        )
        self.insta_status_label.pack(padx=20, pady=(5, 5))
        
        self.insta_fetch_progress = ctk.CTkProgressBar(
            self.tab_insta_single_frame, 
            height=6, 
            fg_color="#1e1e2e", 
            progress_color="#f9e2af"
        )
        self.insta_fetch_progress.pack(fill="x", padx=20, pady=(0, 10))
        self.insta_fetch_progress.set(0)
        
        self.insta_scroll_frame = ctk.CTkScrollableFrame(
            self.tab_insta_single_frame, 
            fg_color="#181825", 
            border_color="#313244", 
            border_width=1,
            corner_radius=10
        )
        self.insta_scroll_frame.pack(fill="both", expand=True, padx=20, pady=5)
        
        self.insta_placeholder_label = ctk.CTkLabel(
            self.insta_scroll_frame,
            text="Paste an Instagram Reel link above\nand click 'Analyze Reel' to load preview.",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color="#7f849c",
            justify="center"
        )
        self.insta_placeholder_label.pack(expand=True, fill="both", pady=100)
        
        # --- TAB 2: PROFILE SCRAPER WIDGETS ---
        profile_search_frame = ctk.CTkFrame(self.tab_insta_profile_frame, fg_color="transparent")
        profile_search_frame.pack(fill="x", padx=20, pady=10)
        profile_search_frame.grid_columnconfigure(0, weight=1)
        
        self.insta_profile_entry = ctk.CTkEntry(
            profile_search_frame,
            placeholder_text="Enter Instagram username (e.g. nature)...",
            height=45,
            fg_color="#1e1e2e",
            border_color="#313244",
            text_color="#cdd6f4",
            placeholder_text_color="#7f849c",
            corner_radius=8,
            font=ctk.CTkFont(family="Segoe UI", size=13)
        )
        self.insta_profile_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.insta_profile_entry.bind("<Return>", lambda e: self.start_insta_profile_fetch())
        
        self.insta_profile_fetch_btn = ctk.CTkButton(
            profile_search_frame,
            text="Scrape Reels",
            height=45,
            fg_color="#cba6f7",
            hover_color="#b4befe",
            text_color="#11111b",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            command=self.start_insta_profile_fetch,
            corner_radius=8
        )
        self.insta_profile_fetch_btn.grid(row=0, column=1, sticky="ns")
        
        self.insta_profile_status_label = ctk.CTkLabel(
            self.tab_insta_profile_frame, 
            text="Ready to search.", 
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#a6adc8"
        )
        self.insta_profile_status_label.pack(padx=20, pady=(5, 5))
        
        self.insta_profile_progress = ctk.CTkProgressBar(
            self.tab_insta_profile_frame, 
            height=6, 
            fg_color="#1e1e2e", 
            progress_color="#f9e2af"
        )
        self.insta_profile_progress.pack(fill="x", padx=20, pady=(0, 10))
        self.insta_profile_progress.set(0)
        
        self.insta_profile_scroll_frame = ctk.CTkScrollableFrame(
            self.tab_insta_profile_frame, 
            fg_color="#181825", 
            border_color="#313244", 
            border_width=1,
            corner_radius=10
        )
        self.insta_profile_scroll_frame.pack(fill="both", expand=True, padx=20, pady=5)
        
        self.insta_profile_placeholder_label = ctk.CTkLabel(
            self.insta_profile_scroll_frame,
            text="Enter an Instagram username above\nand click 'Scrape Reels' to search recent videos.",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color="#7f849c",
            justify="center"
        )
        self.insta_profile_placeholder_label.pack(expand=True, fill="both", pady=100)
        
        # Pack default frame
        self.tab_insta_single_frame.pack(fill="both", expand=True)
        
        # --- BOTTOM CONTROLS (Common to all tabs) ---
        self.insta_controls_frame = ctk.CTkFrame(self.insta_frame, fg_color="#1e1e2e", corner_radius=10, border_width=1, border_color="#313244")
        self.insta_controls_frame.pack(fill="x", padx=20, pady=(5, 5))
        self.insta_controls_frame.grid_columnconfigure(1, weight=1)
        
        dir_title = ctk.CTkLabel(
            self.insta_controls_frame, 
            text="Save to:", 
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#a6adc8"
        )
        dir_title.grid(row=0, column=0, padx=(15, 5), pady=(12, 6), sticky="w")
        
        dir_entry = ctk.CTkEntry(
            self.insta_controls_frame,
            textvariable=self.download_dir,
            height=30,
            fg_color="#181825",
            border_color="#313244",
            text_color="#cdd6f4",
            corner_radius=6,
            font=ctk.CTkFont(family="Segoe UI", size=12)
        )
        dir_entry.grid(row=0, column=1, padx=5, pady=(12, 6), sticky="ew")
        
        browse_btn = ctk.CTkButton(
            self.insta_controls_frame,
            text="Browse...",
            width=80,
            height=30,
            fg_color="#45475a",
            hover_color="#585b70",
            text_color="#cdd6f4",
            command=self.browse_folder,
            corner_radius=6,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")
        )
        browse_btn.grid(row=0, column=2, padx=(5, 15), pady=(12, 6))
        
        # Shared format preset selector at bottom next to download button
        format_lbl = ctk.CTkLabel(
            self.insta_controls_frame,
            text="Format:",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#a6adc8"
        )
        format_lbl.grid(row=1, column=0, padx=(15, 5), pady=(6, 6), sticky="w")
        
        self.format_option = ctk.CTkOptionMenu(
            self.insta_controls_frame,
            values=["Best Quality (Video)", "1080p (Video)", "720p (Video)", "480p (Video)", "Audio Only (MP3)"],
            height=30,
            fg_color="#313244",
            button_color="#45475a",
            button_hover_color="#585b70",
            text_color="#cdd6f4",
            dropdown_fg_color="#1e1e2e",
            dropdown_hover_color="#313244",
            dropdown_text_color="#cdd6f4",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")
        )
        self.format_option.grid(row=1, column=1, columnspan=2, padx=(5, 15), pady=(6, 6), sticky="ew")
        self.format_option.set("Best Quality (Video)")
        
        self.insta_organize_subfolders = ctk.CTkCheckBox(
            self.insta_controls_frame,
            text="Organize into Creator Subfolders",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#cdd6f4",
            fg_color="#a6e3a1",
            hover_color="#94e2d5",
            border_color="#45475a"
        )
        self.insta_organize_subfolders.grid(row=2, column=0, columnspan=3, padx=15, pady=(4, 4), sticky="w")
        self.insta_organize_subfolders.select()
        
        self.insta_download_btn = ctk.CTkButton(
            self.insta_controls_frame,
            text="Download Reel",
            height=45,
            fg_color="#a6e3a1",
            hover_color="#94e2d5",
            text_color="#11111b",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            state="disabled",
            command=self.start_insta_download,
            corner_radius=8
        )
        self.insta_download_btn.grid(row=3, column=0, columnspan=3, padx=15, pady=(6, 12), sticky="ew")
        
        self.insta_down_status_label = ctk.CTkLabel(
            self.insta_controls_frame,
            text="",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#f5e0dc"
        )
        self.insta_down_status_label.grid(row=4, column=0, columnspan=3, padx=15, pady=(0, 2), sticky="ew")
        self.insta_down_status_label.grid_remove()
        
        self.insta_down_progress = ctk.CTkProgressBar(
            self.insta_controls_frame,
            height=6,
            fg_color="#181825",
            progress_color="#a6e3a1"
        )
        self.insta_down_progress.grid(row=5, column=0, columnspan=3, padx=15, pady=(0, 15), sticky="ew")
        self.insta_down_progress.set(0)
        self.insta_down_progress.grid_remove()
        
        copyright_lbl = ctk.CTkLabel(
            self.insta_frame,
            text="© Copyright by Panes & Pixels. All rights reserved.",
            font=ctk.CTkFont(family="Segoe UI", size=9),
            text_color="#585b70"
        )
        copyright_lbl.pack(side="bottom", pady=(5, 10))

    def show_scheduler(self):
        self.dashboard_frame.pack_forget()
        self.yt_frame.pack_forget()
        self.insta_frame.pack_forget()
        self.scheduler_frame.pack(fill="both", expand=True, padx=5, pady=5)
        self.attributes("-alpha", 0.5)
        self.fade_in(0.5)
        self.refresh_scheduler_queue()

    def setup_scheduler_ui(self):
        # Header navigation row
        nav_frame = ctk.CTkFrame(self.scheduler_frame, fg_color="transparent")
        nav_frame.pack(fill="x", padx=20, pady=(15, 5))
        
        back_btn = ctk.CTkButton(
            nav_frame,
            text="← Dashboard",
            width=100,
            height=32,
            fg_color="#313244",
            hover_color="#45475a",
            text_color="#cdd6f4",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            command=self.show_dashboard,
            corner_radius=6
        )
        back_btn.pack(side="left")
        
        # Headers inside frame
        title = ctk.CTkLabel(
            self.scheduler_frame,
            text="📅 Scheduler & Publisher Suite",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color="#cba6f7"
        )
        title.pack(padx=20, pady=(10, 2))
        
        sub = ctk.CTkLabel(
            self.scheduler_frame,
            text="Schedule and automate publishing to YouTube and Instagram",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#a6adc8"
        )
        sub.pack(padx=20, pady=(0, 10))
        
        # Main split container (glassmorphic layout)
        main_split = ctk.CTkFrame(self.scheduler_frame, fg_color="transparent")
        main_split.pack(fill="both", expand=True, padx=20, pady=5)
        main_split.grid_columnconfigure(0, weight=1, uniform="group1")
        main_split.grid_columnconfigure(1, weight=1, uniform="group1")
        main_split.grid_rowconfigure(0, weight=1)
        
        # --- LEFT PANEL: Post Creator Form ---
        form_card = ctk.CTkFrame(
            main_split,
            fg_color="#181825",
            border_color="#313244",
            border_width=1,
            corner_radius=12
        )
        form_card.grid(row=0, column=0, padx=(0, 10), pady=5, sticky="nsew")
        
        form_title = ctk.CTkLabel(
            form_card,
            text="Schedule a Post",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color="#cdd6f4"
        )
        form_title.pack(anchor="w", padx=15, pady=(15, 10))
        
        # 1. Video Selector
        self.scheduler_selected_file = None
        sel_btn = ctk.CTkButton(
            form_card,
            text="📁 Select Video File...",
            fg_color="#313244",
            hover_color="#45475a",
            text_color="#cdd6f4",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            command=self.select_scheduler_video,
            height=32,
            corner_radius=6
        )
        sel_btn.pack(fill="x", padx=15, pady=5)
        
        self.file_path_lbl = ctk.CTkLabel(
            form_card,
            text="No file selected",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#7f849c"
        )
        self.file_path_lbl.pack(anchor="w", padx=20, pady=(2, 8))
        
        # 2. Platform Selector
        plat_lbl = ctk.CTkLabel(
            form_card,
            text="Target Platform:",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#a6adc8"
        )
        plat_lbl.pack(anchor="w", padx=15, pady=(5, 2))
        
        self.scheduler_platform = ctk.CTkOptionMenu(
            form_card,
            values=["Instagram Reels", "YouTube Shorts"],
            fg_color="#313244",
            button_color="#45475a",
            button_hover_color="#585b70",
            text_color="#cdd6f4",
            dropdown_fg_color="#1e1e2e",
            dropdown_hover_color="#313244",
            dropdown_text_color="#cdd6f4",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold")
        )
        self.scheduler_platform.pack(fill="x", padx=15, pady=5)
        self.scheduler_platform.set("Instagram Reels")
        
        # 3. Caption / Description
        desc_lbl = ctk.CTkLabel(
            form_card,
            text="Caption / Description:",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#a6adc8"
        )
        desc_lbl.pack(anchor="w", padx=15, pady=(5, 2))
        
        self.scheduler_caption = ctk.CTkTextbox(
            form_card,
            height=60,
            fg_color="#1e1e2e",
            border_color="#313244",
            border_width=1,
            text_color="#cdd6f4",
            corner_radius=6,
            font=ctk.CTkFont(family="Segoe UI", size=11)
        )
        self.scheduler_caption.pack(fill="x", padx=15, pady=5)
        
        # 4. Visual Time-Picker
        time_lbl = ctk.CTkLabel(
            form_card,
            text="Scheduled Time:",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#a6adc8"
        )
        time_lbl.pack(anchor="w", padx=15, pady=(5, 2))
        
        time_frame = ctk.CTkFrame(form_card, fg_color="transparent")
        time_frame.pack(fill="x", padx=15, pady=2)
        
        # Date entry (Prefilled with today)
        import datetime
        today_str = datetime.datetime.now().strftime("%Y-%m-%d")
        self.scheduler_date_entry = ctk.CTkEntry(
            time_frame,
            width=90,
            height=28,
            fg_color="#1e1e2e",
            border_color="#313244",
            text_color="#cdd6f4",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            corner_radius=6
        )
        self.scheduler_date_entry.pack(side="left", padx=(0, 5))
        self.scheduler_date_entry.insert(0, today_str)
        
        # Hours Dropdown
        self.scheduler_hour = ctk.CTkOptionMenu(
            time_frame,
            values=[f"{i:02d}" for i in range(1, 13)],
            width=55,
            height=28,
            fg_color="#313244",
            button_color="#45475a",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            corner_radius=6
        )
        self.scheduler_hour.pack(side="left", padx=2)
        current_hour = datetime.datetime.now().strftime("%I")
        self.scheduler_hour.set(current_hour)
        
        colon_lbl = ctk.CTkLabel(time_frame, text=":", text_color="#cdd6f4", font=ctk.CTkFont(size=12, weight="bold"))
        colon_lbl.pack(side="left", padx=1)
        
        # Minutes Dropdown
        self.scheduler_minute = ctk.CTkOptionMenu(
            time_frame,
            values=[f"{i:02d}" for i in range(0, 60, 5)],
            width=55,
            height=28,
            fg_color="#313244",
            button_color="#45475a",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            corner_radius=6
        )
        self.scheduler_minute.pack(side="left", padx=2)
        self.scheduler_minute.set("00")
        
        # AM/PM Dropdown
        self.scheduler_ampm = ctk.CTkOptionMenu(
            time_frame,
            values=["AM", "PM"],
            width=55,
            height=28,
            fg_color="#313244",
            button_color="#45475a",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            corner_radius=6
        )
        self.scheduler_ampm.pack(side="left", padx=(5, 0))
        current_ampm = datetime.datetime.now().strftime("%p")
        self.scheduler_ampm.set(current_ampm)
        
        # 5. Uniquifier Options
        unq_lbl = ctk.CTkLabel(
            form_card,
            text="Uniquifier Options (Anti-Duplication):",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#a6adc8"
        )
        unq_lbl.pack(anchor="w", padx=15, pady=(10, 2))
        
        unq_grid = ctk.CTkFrame(form_card, fg_color="transparent")
        unq_grid.pack(fill="x", padx=15, pady=2)
        
        self.unq_mirror = ctk.CTkCheckBox(
            unq_grid,
            text="Mirror horizontally",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#cdd6f4",
            fg_color="#a6e3a1",
            hover_color="#94e2d5",
            border_color="#45475a"
        )
        self.unq_mirror.pack(anchor="w", pady=2)
        
        self.unq_speed = ctk.CTkCheckBox(
            unq_grid,
            text="Micro-speed alteration (101%)",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#cdd6f4",
            fg_color="#a6e3a1",
            hover_color="#94e2d5",
            border_color="#45475a"
        )
        self.unq_speed.pack(anchor="w", pady=2)
        
        self.unq_contrast = ctk.CTkCheckBox(
            unq_grid,
            text="Contrast shift (±1%)",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#cdd6f4",
            fg_color="#a6e3a1",
            hover_color="#94e2d5",
            border_color="#45475a"
        )
        self.unq_contrast.pack(anchor="w", pady=2)
        
        self.unq_scrub = ctk.CTkCheckBox(
            unq_grid,
            text="Scrub original metadata",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#cdd6f4",
            fg_color="#a6e3a1",
            hover_color="#94e2d5",
            border_color="#45475a"
        )
        self.unq_scrub.pack(anchor="w", pady=2)
        self.unq_scrub.select()
        
        # 6. Schedule Button
        schedule_btn = ctk.CTkButton(
            form_card,
            text="Schedule Post 📅",
            height=36,
            fg_color="#cba6f7",
            hover_color="#b4befe",
            text_color="#11111b",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            command=self.add_scheduled_post,
            corner_radius=6
        )
        schedule_btn.pack(fill="x", padx=15, pady=(15, 15))
        
        # --- RIGHT PANEL: Queue ---
        queue_card = ctk.CTkFrame(
            main_split,
            fg_color="#181825",
            border_color="#313244",
            border_width=1,
            corner_radius=12
        )
        queue_card.grid(row=0, column=1, padx=(10, 0), pady=5, sticky="nsew")
        
        queue_title = ctk.CTkLabel(
            queue_card,
            text="Scheduled Queue",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color="#cdd6f4"
        )
        queue_title.pack(anchor="w", padx=15, pady=(15, 5))
        
        self.scheduler_scroll = ctk.CTkScrollableFrame(
            queue_card,
            fg_color="transparent"
        )
        self.scheduler_scroll.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.scheduler_placeholder = ctk.CTkLabel(
            self.scheduler_scroll,
            text="No scheduled posts yet.\nFill the form on the left to schedule a video.",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#7f849c",
            justify="center"
        )
        self.scheduler_placeholder.pack(pady=100)
        
        # --- BOTTOM LOGS CONSOLE ---
        log_frame = ctk.CTkFrame(
            self.scheduler_frame,
            fg_color="#181825",
            border_color="#313244",
            border_width=1,
            corner_radius=10,
            height=100
        )
        log_frame.pack(fill="x", padx=20, pady=(5, 10))
        
        log_title = ctk.CTkLabel(
            log_frame,
            text="Activity Logs Console",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color="#cba6f7"
        )
        log_title.pack(anchor="w", padx=12, pady=(5, 1))
        
        self.scheduler_log_box = ctk.CTkTextbox(
            log_frame,
            fg_color="transparent",
            text_color="#a6e3a1",
            font=ctk.CTkFont(family="Consolas", size=10),
            height=65
        )
        self.scheduler_log_box.pack(fill="both", expand=True, padx=10, pady=(1, 8))
        self.scheduler_log_box.configure(state="disabled")

    def add_scheduler_log(self, message):
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        log_line = f"[{timestamp}] {message}\n"
        def append_log():
            self.scheduler_log_box.configure(state="normal")
            self.scheduler_log_box.insert("end", log_line)
            self.scheduler_log_box.see("end")
            self.scheduler_log_box.configure(state="disabled")
        self.after(0, append_log)

    def select_scheduler_video(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Video Files", "*.mp4 *.mov *.avi *.mkv"), ("All Files", "*.*")]
        )
        if file_path:
            self.scheduler_selected_file = file_path
            display_name = os.path.basename(file_path)
            if len(display_name) > 30:
                display_name = display_name[:27] + "..."
            self.file_path_lbl.configure(text=display_name, text_color="#a6e3a1")

    def add_scheduled_post(self):
        if not self.scheduler_selected_file:
            self.add_scheduler_log("Error: Please select a video file first.")
            return
            
        caption = self.scheduler_caption.get("1.0", "end-1c").strip()
        date_val = self.scheduler_date_entry.get().strip()
        hour_val = self.scheduler_hour.get()
        min_val = self.scheduler_minute.get()
        ampm_val = self.scheduler_ampm.get()
        
        try:
            hour_int = int(hour_val)
            if ampm_val == "PM" and hour_int < 12:
                hour_int += 12
            elif ampm_val == "AM" and hour_int == 12:
                hour_int = 0
            time_str = f"{hour_int:02d}:{min_val}"
            scheduled_time_str = f"{date_val} {time_str}"
            
            import datetime
            datetime.datetime.strptime(scheduled_time_str, "%Y-%m-%d %H:%M")
        except Exception:
            self.add_scheduler_log("Error: Invalid date/time format. Please check your inputs.")
            return
            
        platform_raw = self.scheduler_platform.get()
        platform = "youtube" if platform_raw == "YouTube Shorts" else "instagram"
        
        uniquifier_opts = {
            "mirror": bool(self.unq_mirror.get()),
            "speed": bool(self.unq_speed.get()),
            "contrast": bool(self.unq_contrast.get()),
            "scrub": bool(self.unq_scrub.get())
        }
        
        import scheduler_db
        task = scheduler_db.add_task(
            video_path=self.scheduler_selected_file,
            platform=platform,
            caption=caption,
            scheduled_time_str=scheduled_time_str,
            uniquifier_opts=uniquifier_opts
        )
        
        self.add_scheduler_log(f"Scheduled upload for {os.path.basename(self.scheduler_selected_file)} at {scheduled_time_str}.")
        
        self.scheduler_selected_file = None
        self.file_path_lbl.configure(text="No file selected", text_color="#7f849c")
        self.scheduler_caption.delete("1.0", "end")
        self.refresh_scheduler_queue()

    def refresh_scheduler_queue(self):
        for child in self.scheduler_scroll.winfo_children():
            child.destroy()
            
        import scheduler_db
        tasks = scheduler_db.load_schedule()
        
        if not tasks:
            self.scheduler_placeholder = ctk.CTkLabel(
                self.scheduler_scroll,
                text="No scheduled posts yet.\nFill the form on the left to schedule a video.",
                font=ctk.CTkFont(family="Segoe UI", size=11),
                text_color="#7f849c",
                justify="center"
            )
            self.scheduler_placeholder.pack(pady=100)
            return
            
        for task in reversed(tasks):
            card = ctk.CTkFrame(
                self.scheduler_scroll,
                fg_color="#1e1e2e",
                border_color="#313244",
                border_width=1,
                corner_radius=8
            )
            card.pack(fill="x", pady=4, padx=5)
            
            meta_frame = ctk.CTkFrame(card, fg_color="transparent")
            meta_frame.pack(side="left", fill="both", expand=True, padx=10, pady=8)
            
            file_name = os.path.basename(task["video_path"])
            file_display = file_name if len(file_name) <= 24 else file_name[:21] + "..."
            
            name_lbl = ctk.CTkLabel(
                meta_frame,
                text=file_display,
                font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                text_color="#cdd6f4",
                anchor="w"
            )
            name_lbl.pack(anchor="w")
            
            plat_text = "YouTube Shorts" if task["platform"] == "youtube" else "Instagram Reels"
            plat_color = "#f38ba8" if task["platform"] == "youtube" else "#f5c2e7"
            
            details_lbl = ctk.CTkLabel(
                meta_frame,
                text=f"{plat_text} | {task['scheduled_time']}",
                font=ctk.CTkFont(family="Segoe UI", size=10),
                text_color=plat_color,
                anchor="w"
            )
            details_lbl.pack(anchor="w", pady=(2, 0))
            
            control_frame = ctk.CTkFrame(card, fg_color="transparent")
            control_frame.pack(side="right", padx=10, pady=8)
            
            status = task["status"]
            status_text = status.upper()
            status_color = "#a6e3a1"
            if status == "scheduled":
                status_color = "#f9e2af"
            elif status == "uploading":
                status_color = "#fab387"
            elif status == "failed":
                status_color = "#f38ba8"
                
            status_lbl = ctk.CTkLabel(
                control_frame,
                text=status_text,
                font=ctk.CTkFont(family="Segoe UI", size=9, weight="bold"),
                text_color=status_color
            )
            status_lbl.pack(side="left", padx=5)
            
            if status in ["scheduled", "failed"]:
                pub_btn = ctk.CTkButton(
                    control_frame,
                    text="🚀",
                    width=24,
                    height=24,
                    fg_color="#45475a",
                    hover_color="#a6e3a1",
                    text_color="#cdd6f4",
                    command=lambda t_id=task["id"]: self.trigger_publish_now(t_id),
                    corner_radius=4,
                    font=ctk.CTkFont(size=10)
                )
                pub_btn.pack(side="left", padx=2)
                
            cancel_btn = ctk.CTkButton(
                control_frame,
                text="❌",
                width=24,
                height=24,
                fg_color="#45475a",
                hover_color="#f38ba8",
                text_color="#cdd6f4",
                command=lambda t_id=task["id"]: self.trigger_cancel_task(t_id),
                corner_radius=4,
                font=ctk.CTkFont(size=10)
            )
            cancel_btn.pack(side="left", padx=2)

    def trigger_publish_now(self, task_id):
        import scheduler_db
        tasks = scheduler_db.load_schedule()
        for task in tasks:
            if task["id"] == task_id:
                scheduler_db.update_task_status(task_id, "uploading")
                self.refresh_scheduler_queue()
                self.add_scheduler_log(f"Forcing immediate upload for task {task_id}...")
                threading.Thread(target=self.execute_upload_worker, args=(task,), daemon=True).start()
                break

    def trigger_cancel_task(self, task_id):
        import scheduler_db
        scheduler_db.delete_task(task_id)
        self.add_scheduler_log(f"Task {task_id} cancelled.")
        self.refresh_scheduler_queue()

    def start_scheduler_loop(self):
        threading.Thread(target=self.scheduler_loop_worker, daemon=True).start()

    def scheduler_loop_worker(self):
        import scheduler_db
        from datetime import datetime
        import time
        
        while True:
            try:
                tasks = scheduler_db.load_schedule()
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                now_dt = datetime.strptime(now_str, "%Y-%m-%d %H:%M")
                
                for task in tasks:
                    if task["status"] == "scheduled":
                        try:
                            task_time_dt = datetime.strptime(task["scheduled_time"], "%Y-%m-%d %H:%M")
                            if now_dt >= task_time_dt:
                                scheduler_db.update_task_status(task["id"], "uploading")
                                self.refresh_scheduler_queue()
                                self.add_scheduler_log(f"Starting scheduled upload for task {task['id']}...")
                                threading.Thread(target=self.execute_upload_worker, args=(task,), daemon=True).start()
                        except Exception as e:
                            print(f"Error checking schedule: {e}")
            except Exception as e:
                print(f"Scheduler loop error: {e}")
            time.sleep(15)

    def execute_upload_worker(self, task):
        import scheduler_db
        import uploader
        import os
        
        task_id = task["id"]
        video_path = task["video_path"]
        platform = task["platform"]
        caption = task["caption"]
        opts = task["uniquifier_opts"]
        
        processed_path = video_path
        if any(opts.values()):
            try:
                dir_name = os.path.dirname(video_path)
                base_name = os.path.basename(video_path)
                processed_path = os.path.join(dir_name, f"unique_{task_id}_{base_name}")
                
                uploader.uniquify_video(
                    input_path=video_path,
                    output_path=processed_path,
                    mirror=opts.get("mirror", False),
                    speed=opts.get("speed", False),
                    contrast=opts.get("contrast", False),
                    scrub=opts.get("scrub", True),
                    log_callback=lambda msg: self.add_scheduler_log(msg)
                )
            except Exception as e:
                self.add_scheduler_log(f"Uniquifier failed: {e}")
                scheduler_db.update_task_status(task_id, "failed", f"Uniquifier failed: {e}")
                self.refresh_scheduler_queue()
                return
                
        try:
            if platform == "instagram":
                uploader.upload_to_instagram(
                    video_path=processed_path,
                    caption=caption,
                    log_callback=lambda msg: self.add_scheduler_log(msg)
                )
            elif platform == "youtube":
                title = os.path.splitext(os.path.basename(video_path))[0]
                uploader.upload_to_youtube(
                    video_path=processed_path,
                    title=title,
                    caption=caption,
                    log_callback=lambda msg: self.add_scheduler_log(msg)
                )
                
            scheduler_db.update_task_status(task_id, "published")
            self.add_scheduler_log(f"Task {task_id} uploaded successfully!")
            
            if processed_path != video_path and os.path.exists(processed_path):
                try:
                    os.remove(processed_path)
                except:
                    pass
                    
        except Exception as ex:
            self.add_scheduler_log(f"Upload failed: {ex}")
            scheduler_db.update_task_status(task_id, "failed", f"Upload failed: {ex}")
            
            if processed_path != video_path and os.path.exists(processed_path):
                try:
                    os.remove(processed_path)
                except:
                    pass
                    
        self.refresh_scheduler_queue()

    def browse_folder(self):
        chosen = filedialog.askdirectory(initialdir=self.download_dir.get())
        if chosen:
            self.download_dir.set(chosen)
            
    # YouTube downloader logical flows
    def start_fetch(self):
        url = self.url_entry.get().strip()
        if not url:
            self.update_status("Please enter a YouTube channel URL.", 0, error=True)
            return
            
        if self.is_processing:
            return
            
        self.is_processing = True
        self.fetch_btn.configure(state="disabled")
        self.download_btn.configure(state="disabled")
        
        for card in self.cards:
            card.pack_forget()
            card.destroy()
        self.cards.clear()
        self.shorts_list.clear()
        
        self.placeholder_label.pack_forget()
        
        self.status_label.configure(text_color="#a6adc8")
        self.fetch_progress.configure(mode="indeterminate")
        self.fetch_progress.start()
        self.update_status("Connecting to YouTube...", 0.1)
        
        threading.Thread(target=self.fetch_thread_fn, args=(url,), daemon=True).start()
        
    def update_status(self, text, progress_val, error=False):
        self.status_label.configure(text=text)
        if error:
            self.status_label.configure(text_color="#f38ba8")
            self.fetch_progress.configure(progress_color="#f38ba8")
            self.fetch_progress.stop()
            self.fetch_progress.configure(mode="determinate")
            self.fetch_progress.set(0)
        else:
            self.status_label.configure(text_color="#a6adc8")
            self.fetch_progress.configure(progress_color="#f9e2af")
            
        if self.fetch_progress.cget("mode") == "determinate":
            self.fetch_progress.set(progress_val)
            
    def fetch_thread_fn(self, url):
        try:
            def on_progress(message, pct):
                self.after(0, lambda: self.update_status(message, pct))
            shorts = downloader.get_top_shorts(url, progress_callback=on_progress)
            self.after(0, lambda: self.display_results(shorts))
        except Exception as e:
            err_msg = str(e)
            if "HTTP Error 404" in err_msg or "Requested entity was not found" in err_msg:
                user_msg = "Channel not found. Check spelling or URL handle."
            else:
                user_msg = "Error scanning channel. Verify handle link."
            self.after(0, lambda: self.handle_fetch_error(user_msg))
            
    def handle_fetch_error(self, message):
        self.is_processing = False
        self.fetch_btn.configure(state="normal")
        self.update_status(message, 1.0, error=True)
        self.placeholder_label.configure(text=message, text_color="#f38ba8")
        self.placeholder_label.pack(expand=True, fill="both", pady=100)
        
    def display_results(self, shorts):
        self.is_processing = False
        self.fetch_btn.configure(state="normal")
        self.fetch_progress.stop()
        self.fetch_progress.configure(mode="determinate")
        self.fetch_progress.set(1.0)
        
        if not shorts:
            self.update_status("No shorts found on this channel.", 1.0, error=True)
            self.placeholder_label.configure(text="No Shorts found for this channel.\nVerify it has Shorts uploaded.", text_color="#f38ba8")
            self.placeholder_label.pack(expand=True, fill="both", pady=100)
            return
            
        self.shorts_list = shorts
        self.update_status(f"Found {len(shorts)} top shorts successfully.", 1.0)
        
        for idx, short in enumerate(shorts):
            card = ShortCard(self.scroll_frame, short)
            self.cards.append(card)
            self.after(idx * 60, lambda c=card: c.pack(fill="x", padx=5, pady=5))
            
        self.download_btn.configure(state="normal")
        
    def start_download(self):
        selected_shorts = []
        for idx, card in enumerate(self.cards):
            if card.is_selected():
                selected_shorts.append(self.shorts_list[idx])
                
        if not selected_shorts:
            self.update_status("Please select at least one Short to download.", 1.0, error=True)
            return
            
        raw_channel_url = self.url_entry.get().strip()
        try:
            import downloader
            clean_url = downloader.clean_channel_url(raw_channel_url)
            parts = clean_url.split('/')
            page_id = parts[-2] if len(parts) >= 2 else raw_channel_url
        except Exception:
            page_id = raw_channel_url
            
        for short in selected_shorts:
            self.add_to_download_queue(short['title'], short['url'], "youtube", "short", page_id=page_id)
            
        self.update_status(f"Added {len(selected_shorts)} Shorts to download queue.", 1.0)
        
    def update_download_progress(self, current_idx, total_count, title, state_dict):
        percent = state_dict.get('percent', 0.0)
        speed = state_dict.get('speed', 'N/A')
        eta = state_dict.get('eta', 'N/A')
        
        status_text = f"Downloading Short {current_idx} of {total_count}: \"{title[:30]}...\"\nProgress: {percent:.1f}% | Speed: {speed} | ETA: {eta}"
        self.down_status_label.configure(text=status_text)
        
        overall_pct = ((current_idx - 1) / total_count) + (percent / 100.0 / total_count)
        self.down_progress.set(overall_pct)
        
    def download_thread_fn(self, selected_shorts):
        total = len(selected_shorts)
        download_folder = self.download_dir.get()
        success_count = 0
        error_count = 0
        
        for idx, short in enumerate(selected_shorts, 1):
            title = short['title']
            url = short['url']
            def progress_cb(state_dict):
                self.after(0, lambda idx=idx, t=title, sd=state_dict: self.update_download_progress(idx, total, t, sd))
            try:
                downloader.download_short(url, download_folder, progress_callback=progress_cb)
                success_count += 1
            except Exception as e:
                print(f"Error downloading {title}: {e}")
                error_count += 1
                
        self.after(0, lambda s=success_count, f=error_count: self.finish_downloads(s, f))
        
    def finish_downloads(self, success_count, error_count):
        self.is_processing = False
        self.fetch_btn.configure(state="normal")
        self.download_btn.configure(state="normal")
        
        total = success_count + error_count
        summary_msg = f"Finished. Downloaded {success_count}/{total} shorts successfully."
        if error_count > 0:
            summary_msg += f" ({error_count} failed)"
            self.down_status_label.configure(text=summary_msg, text_color="#f38ba8")
        else:
            self.down_status_label.configure(text=summary_msg, text_color="#a6e3a1")
            
        self.down_progress.set(1.0)
        self.after(6000, self.clear_download_status_labels)
        
    def clear_download_status_labels(self):
        if not self.is_processing:
            self.down_status_label.grid_remove()
            self.down_progress.grid_remove()

    # Instagram Downloader Logic
    def start_insta_fetch(self):
        url = self.insta_url_entry.get().strip()
        if not url:
            self.update_insta_status("Please enter an Instagram Reel URL.", 0, error=True)
            return
            
        if self.is_processing:
            return
            
        self.is_processing = True
        self.insta_fetch_btn.configure(state="disabled")
        self.insta_download_btn.configure(state="disabled")
        
        # Clear previous card
        for card in self.insta_cards:
            card.pack_forget()
            card.destroy()
        self.insta_cards.clear()
        self.insta_reel_data = None
        
        self.insta_placeholder_label.pack_forget()
        
        self.insta_status_label.configure(text_color="#a6adc8")
        self.insta_fetch_progress.configure(mode="indeterminate")
        self.insta_fetch_progress.start()
        self.update_insta_status("Extracting Reel information...", 0.1)
        
        threading.Thread(target=self.insta_fetch_thread_fn, args=(url,), daemon=True).start()

    def update_insta_status(self, text, progress_val, error=False):
        self.insta_status_label.configure(text=text)
        if error:
            self.insta_status_label.configure(text_color="#f38ba8")
            self.insta_fetch_progress.configure(progress_color="#f38ba8")
            self.insta_fetch_progress.stop()
            self.insta_fetch_progress.configure(mode="determinate")
            self.insta_fetch_progress.set(0)
        else:
            self.insta_status_label.configure(text_color="#a6adc8")
            self.insta_fetch_progress.configure(progress_color="#f9e2af")
            
        if self.insta_fetch_progress.cget("mode") == "determinate":
            self.insta_fetch_progress.set(progress_val)

    def insta_fetch_thread_fn(self, url):
        try:
            reel_data = downloader.get_insta_reel_info(url)
            self.after(0, lambda: self.display_insta_results(reel_data))
        except Exception as e:
            err_msg = str(e)
            if "Instagram blocked anonymous access" in err_msg:
                user_msg = "Blocked by Instagram. Please log in on Chrome/Edge or use cookies."
            else:
                user_msg = "Error reading Reel link. Check connection or link spelling."
            self.after(0, lambda: self.handle_insta_fetch_error(user_msg))

    def handle_insta_fetch_error(self, message):
        self.is_processing = False
        self.insta_fetch_btn.configure(state="normal")
        self.update_insta_status(message, 1.0, error=True)
        self.insta_placeholder_label.configure(text=message, text_color="#f38ba8")
        self.insta_placeholder_label.pack(expand=True, fill="both", pady=100)
        self.prompt_insta_relogin(message)

    def display_insta_results(self, reel_data):
        self.is_processing = False
        self.insta_fetch_btn.configure(state="normal")
        self.insta_fetch_progress.stop()
        self.insta_fetch_progress.configure(mode="determinate")
        self.insta_fetch_progress.set(1.0)
        
        self.insta_reel_data = reel_data
        self.update_insta_status("Reel analyzed successfully.", 1.0)
        
        # Display ReelCard (Smooth Staggered animation style)
        card = ReelCard(self.insta_scroll_frame, reel_data)
        self.insta_cards.append(card)
        self.after(100, lambda: card.pack(fill="x", padx=5, pady=5))
        
        self.insta_download_btn.configure(state="normal")

    def start_insta_download(self):
        if not self.insta_cards or not self.insta_cards[0].is_selected():
            self.update_insta_status("Please select the Reel to download.", 1.0, error=True)
            return
            
        self.add_to_download_queue(self.insta_reel_data['title'], self.insta_reel_data['url'], "instagram", "reel")
        self.update_insta_status("Added Reel to download queue.", 1.0)

    def update_insta_download_progress(self, title, state_dict):
        percent = state_dict.get('percent', 0.0)
        speed = state_dict.get('speed', 'N/A')
        eta = state_dict.get('eta', 'N/A')
        
        status_text = f"Downloading: \"{title[:30]}...\"\nProgress: {percent:.1f}% | Speed: {speed} | ETA: {eta}"
        self.insta_down_status_label.configure(text=status_text)
        self.insta_down_progress.set(percent / 100.0)

    def insta_download_thread_fn(self, reel_data):
        title = reel_data['title']
        url = reel_data['url']
        opts = reel_data.get('ydl_opts')
        download_folder = self.download_dir.get()
        
        def progress_cb(state_dict):
            self.after(0, lambda t=title, sd=state_dict: self.update_insta_download_progress(t, sd))
            
        success = False
        try:
            downloader.download_insta_reel(url, download_folder, ydl_opts=opts, progress_callback=progress_cb)
            success = True
        except Exception as e:
            print(f"Error downloading Reel: {e}")
            
        self.after(0, lambda s=success: self.finish_insta_downloads(s))

    def finish_insta_downloads(self, success):
        self.is_processing = False
        self.insta_fetch_btn.configure(state="normal")
        self.insta_download_btn.configure(state="normal")
        
        if success:
            self.insta_down_status_label.configure(text="Finished. Downloaded Reel successfully.", text_color="#a6e3a1")
        else:
            self.insta_down_status_label.configure(text="Failed to download Reel. Verify uploader rules or cookies.", text_color="#f38ba8")
            
        self.insta_down_progress.set(1.0)
        self.after(6000, self.clear_insta_download_status_labels)

    def clear_insta_download_status_labels(self):
        if not self.is_processing:
            self.insta_down_status_label.grid_remove()
            self.insta_down_progress.grid_remove()

    def open_insta_login_window(self):
        # Open the top-level credentials window
        InstaLoginWindow(self)

    def prompt_insta_relogin(self, context_msg=""):
        from tkinter import messagebox
        res = messagebox.askyesno(
            "Instagram Login Required",
            f"Your Instagram login session has expired or requires authentication.\n\n"
            f"Reason: {context_msg}\n\n"
            f"Would you like to open the Login Settings window now to enter your password and reconnect?"
        )
        if res:
            self.open_insta_login_window()

    def on_yt_tab_changed(self, value):
        # Hide all tab frames
        self.tab_channel_frame.pack_forget()
        self.tab_hashtag_frame.pack_forget()
        self.tab_video_frame.pack_forget()
        
        # Reset overall download progress bar
        self.down_status_label.grid_remove()
        self.down_progress.grid_remove()
        self.download_btn.configure(text="Download Selected", state="disabled")
        
        if value == "Channel Shorts":
            self.tab_channel_frame.pack(fill="both", expand=True)
            self.download_btn.configure(text="Download Selected Shorts", command=self.start_download)
            if self.cards:
                self.download_btn.configure(state="normal")
        elif value == "Hashtag Shorts":
            self.tab_hashtag_frame.pack(fill="both", expand=True)
            self.download_btn.configure(text="Download Selected Shorts", command=self.start_hashtag_download)
            if self.hash_cards:
                self.download_btn.configure(state="normal")
        elif value == "Video Downloader":
            self.tab_video_frame.pack(fill="both", expand=True)
            self.download_btn.configure(text="Download Video", command=self.start_video_download)
            if self.video_data:
                self.download_btn.configure(state="normal")

    def start_hashtag_fetch(self):
        hashtags = self.hash_entry.get().strip()
        sort_by = self.sort_option.get()
        if not hashtags:
            self.update_hash_status("Please enter at least one hashtag.", 0, error=True)
            return
            
        if self.is_processing:
            return
            
        self.is_processing = True
        self.hash_fetch_btn.configure(state="disabled")
        self.download_btn.configure(state="disabled")
        
        for card in self.hash_cards:
            card.pack_forget()
            card.destroy()
        self.hash_cards.clear()
        self.hash_shorts_list.clear()
        
        self.hash_placeholder_label.pack_forget()
        
        self.hash_status_label.configure(text_color="#a6adc8")
        self.hash_progress.configure(mode="indeterminate")
        self.hash_progress.start()
        self.update_hash_status("Searching YouTube hashtags...", 0.1)
        
        threading.Thread(target=self.hashtag_fetch_thread_fn, args=(hashtags, sort_by), daemon=True).start()

    def update_hash_status(self, text, progress_val, error=False):
        self.hash_status_label.configure(text=text)
        if error:
            self.hash_status_label.configure(text_color="#f38ba8")
            self.hash_progress.configure(progress_color="#f38ba8")
            self.hash_progress.stop()
            self.hash_progress.configure(mode="determinate")
            self.hash_progress.set(0)
        else:
            self.hash_status_label.configure(text_color="#a6adc8")
            self.hash_progress.configure(progress_color="#f9e2af")
            
        if self.hash_progress.cget("mode") == "determinate":
            self.hash_progress.set(progress_val)
            
    def hashtag_fetch_thread_fn(self, hashtags, sort_by):
        try:
            shorts = downloader.get_shorts_by_hashtags(hashtags, sort_by)
            self.after(0, lambda: self.display_hashtag_results(shorts))
        except Exception as e:
            self.after(0, lambda: self.handle_hash_fetch_error(f"Error fetching hashtags: {e}"))
            
    def handle_hash_fetch_error(self, message):
        self.is_processing = False
        self.hash_fetch_btn.configure(state="normal")
        self.update_hash_status(message, 1.0, error=True)
        self.hash_placeholder_label.configure(text=message, text_color="#f38ba8")
        self.hash_placeholder_label.pack(expand=True, fill="both", pady=100)
        
    def display_hashtag_results(self, shorts):
        self.is_processing = False
        self.hash_fetch_btn.configure(state="normal")
        self.hash_progress.stop()
        self.hash_progress.configure(mode="determinate")
        self.hash_progress.set(1.0)
        
        if not shorts:
            self.update_hash_status("No shorts found for these hashtags.", 1.0, error=True)
            self.hash_placeholder_label.configure(text="No Shorts found matching these hashtags.\nTry different tags.", text_color="#f38ba8")
            self.hash_placeholder_label.pack(expand=True, fill="both", pady=100)
            return
            
        self.hash_shorts_list = shorts
        self.update_hash_status(f"Found {len(shorts)} aggregated shorts successfully.", 1.0)
        
        for idx, short in enumerate(shorts):
            card = ShortCard(self.hash_scroll_frame, short)
            self.hash_cards.append(card)
            self.after(idx * 60, lambda c=card: c.pack(fill="x", padx=5, pady=5))
            
        self.download_btn.configure(state="normal")

    def start_hashtag_download(self):
        selected_shorts = []
        for idx, card in enumerate(self.hash_cards):
            if card.is_selected():
                selected_shorts.append(self.hash_shorts_list[idx])
                
        if not selected_shorts:
            self.update_status("Please select at least one Short to download.", 1.0, error=True)
            return
            
        self.is_processing = True
        self.hash_fetch_btn.configure(state="disabled")
        self.download_btn.configure(state="disabled")
        
        self.down_status_label.grid()
        self.down_progress.grid()
        
        threading.Thread(target=self.download_thread_fn, args=(selected_shorts,), daemon=True).start()

    def start_video_fetch(self):
        url = self.vid_url_entry.get().strip()
        if not url:
            self.update_video_status("Please enter a YouTube video URL.", 0, error=True)
            return
            
        if self.is_processing:
            return
            
        self.is_processing = True
        self.vid_fetch_btn.configure(state="disabled")
        self.download_btn.configure(state="disabled")
        
        if self.video_card:
            self.video_card.pack_forget()
            self.video_card.destroy()
            self.video_card = None
        self.video_data = None
        
        self.vid_placeholder_label.pack_forget()
        
        self.vid_status_label.configure(text_color="#a6adc8")
        self.vid_progress.configure(mode="indeterminate")
        self.vid_progress.start()
        self.update_video_status("Connecting to YouTube...", 0.1)
        
        threading.Thread(target=self.video_fetch_thread_fn, args=(url,), daemon=True).start()

    def update_video_status(self, text, progress_val, error=False):
        self.vid_status_label.configure(text=text)
        if error:
            self.vid_status_label.configure(text_color="#f38ba8")
            self.vid_progress.configure(progress_color="#f38ba8")
            self.vid_progress.stop()
            self.vid_progress.configure(mode="determinate")
            self.vid_progress.set(0)
        else:
            self.vid_status_label.configure(text_color="#a6adc8")
            self.vid_progress.configure(progress_color="#f9e2af")
            
        if self.vid_progress.cget("mode") == "determinate":
            self.vid_progress.set(progress_val)

    def video_fetch_thread_fn(self, url):
        try:
            info = downloader.get_youtube_video_info(url)
            self.after(0, lambda: self.display_video_results(info))
        except Exception as e:
            self.after(0, lambda: self.handle_video_fetch_error(f"Error fetching video info: {e}"))
            
    def handle_video_fetch_error(self, message):
        self.is_processing = False
        self.vid_fetch_btn.configure(state="normal")
        self.update_video_status(message, 1.0, error=True)
        self.vid_placeholder_label.configure(text=message, text_color="#f38ba8")
        self.vid_placeholder_label.pack(expand=True, fill="both", pady=100)

    def display_video_results(self, info):
        self.is_processing = False
        self.vid_fetch_btn.configure(state="normal")
        self.vid_progress.stop()
        self.vid_progress.configure(mode="determinate")
        self.vid_progress.set(1.0)
        
        self.video_data = info
        self.update_video_status("Video loaded successfully.", 1.0)
        
        self.video_card = VideoCard(self.vid_card_frame, info)
        self.video_card.pack(fill="x", padx=15, pady=15)
        
        self.download_btn.configure(state="normal")

    def start_video_download(self):
        if not self.video_data:
            return
            
        self.add_to_download_queue(self.video_data['title'], self.video_data['url'], "youtube", "video")
        self.update_video_status("Added video to download queue.", 1.0)

    def video_download_thread_fn(self, url):
        download_folder = self.download_dir.get()
        title = self.video_data['title']
        
        def progress_cb(state_dict):
            self.after(0, lambda t=title, sd=state_dict: self.update_video_download_progress(t, sd))
            
        success = False
        try:
            downloader.download_youtube_video(url, download_folder, progress_callback=progress_cb)
            success = True
        except Exception as e:
            print(f"Error downloading video: {e}")
            
        self.after(0, lambda s=success: self.finish_video_download(s))

    def update_video_download_progress(self, title, state_dict):
        percent = state_dict.get('percent', 0.0)
        speed = state_dict.get('speed', 'N/A')
        eta = state_dict.get('eta', 'N/A')
        
        status_text = f"Downloading Video: \"{title[:30]}...\"\nProgress: {percent:.1f}% | Speed: {speed} | ETA: {eta}"
        self.down_status_label.configure(text=status_text)
        self.down_progress.set(percent / 100.0)

    def finish_video_download(self, success):
        self.is_processing = False
        self.vid_fetch_btn.configure(state="normal")
        self.download_btn.configure(state="normal")
        
        if success:
            self.down_status_label.configure(text="Download finished successfully!", text_color="#a6e3a1")
            self.down_progress.set(1.0)
        else:
            self.down_status_label.configure(text="Download failed. Check URL or connection.", text_color="#f38ba8")
            self.down_progress.set(0)

    # --- TABS FOR INSTAGRAM SCREEN ---
    def on_insta_tab_changed(self, value):
        if value == "Single Reel":
            self.tab_insta_profile_frame.pack_forget()
            self.tab_insta_single_frame.pack(fill="both", expand=True)
            self.insta_download_btn.configure(text="Download Reel", command=self.start_insta_download)
            if self.insta_reel_data:
                self.insta_download_btn.configure(state="normal")
            else:
                self.insta_download_btn.configure(state="disabled")
        elif value == "Profile Scraper":
            self.tab_insta_single_frame.pack_forget()
            self.tab_insta_profile_frame.pack(fill="both", expand=True)
            self.insta_download_btn.configure(text="Download Selected Reels", command=self.start_insta_profile_download)
            if self.insta_profile_cards:
                self.insta_download_btn.configure(state="normal")
            else:
                self.insta_download_btn.configure(state="disabled")

    # --- INSTAGRAM PROFILE SCRAPER ---
    def start_insta_profile_fetch(self):
        raw_input = self.insta_profile_entry.get().strip()
        if not raw_input:
            self.update_insta_profile_status("Please enter a username or profile URL.", 1.0, error=True)
            return
            
        # Extract username if a URL or handle is provided
        username = raw_input
        if "instagram.com/" in username or "http" in username:
            parts = username.split("instagram.com/")
            if len(parts) > 1:
                path = parts[1]
            else:
                from urllib.parse import urlparse
                path = urlparse(username).path.lstrip('/')
            username = path.split('?')[0].split('/')[0].strip()
        elif username.startswith('@'):
            username = username[1:]
            
        if not username:
            self.update_insta_profile_status("Invalid username or URL.", 1.0, error=True)
            return
            
        self.is_processing = True
        self.insta_profile_fetch_btn.configure(state="disabled")
        self.insta_profile_progress.configure(mode="indeterminate")
        self.insta_profile_progress.start()
        self.update_insta_profile_status(f"Scraping Reels from @{username}...", 0.5)
        
        threading.Thread(target=self.insta_profile_fetch_worker, args=(username,), daemon=True).start()

    def update_insta_profile_status(self, text, progress_val, error=False):
        self.insta_profile_status_label.configure(
            text=text,
            text_color="#f38ba8" if error else ("#a6e3a1" if progress_val == 1.0 else "#f9e2af")
        )
        self.insta_profile_progress.set(progress_val)

    def insta_profile_fetch_worker(self, username):
        # Read saved auth credentials
        auth_username = None
        auth_password = None
        config_path = os.path.join(os.path.expanduser("~"), ".yt_shorts_downloader_insta")
        if os.path.exists(config_path):
            try:
                import crypto_utils
                with open(config_path, "r", encoding="utf-8") as f:
                    enc_str = f.read().strip()
                creds = crypto_utils.decrypt_credentials(enc_str)
                if creds:
                    auth_username = creds[0]
                    auth_password = creds[1] if len(creds) > 1 else None
            except Exception as e:
                print(f"Error loading credentials: {e}")
                
        session_dir = os.path.join(
            os.environ.get("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local")),
            "Instaloader"
        )
        
        try:
            import downloader
            reels = downloader.get_insta_profile_reels(
                username, session_dir, auth_username, auth_password
            )
            self.after(0, lambda r=reels: self.finish_insta_profile_fetch(r))
        except downloader.SessionExpiredError as e:
            self.after(0, lambda msg=str(e): self.finish_insta_profile_fetch_error(
                f"Session expired: {msg}"
            ))
        except Exception as e:
            self.after(0, lambda msg=str(e): self.finish_insta_profile_fetch_error(msg))

    def finish_insta_profile_fetch(self, reels):
        self.is_processing = False
        self.insta_profile_fetch_btn.configure(state="normal")
        self.insta_profile_progress.stop()
        self.insta_profile_progress.configure(mode="determinate")
        self.insta_profile_progress.set(1.0)
        
        # Clear old scroll widgets
        for widget in self.insta_profile_scroll_frame.winfo_children():
            widget.destroy()
            
        self.insta_profile_cards = []
        self.insta_profile_reels_list = reels
        
        if not reels:
            self.update_insta_profile_status("No video posts / Reels found on profile.", 1.0, error=True)
            self.insta_download_btn.configure(state="disabled")
            return
            
        self.update_insta_profile_status(f"Found {len(reels)} Reels.", 1.0)
        
        for reel in reels:
            card = ReelCard(self.insta_profile_scroll_frame, reel)
            card.pack(fill="x", padx=10, pady=5)
            self.insta_profile_cards.append(card)
            
        self.insta_download_btn.configure(state="normal")

    def finish_insta_profile_fetch_error(self, msg):
        self.is_processing = False
        self.insta_profile_fetch_btn.configure(state="normal")
        self.insta_profile_progress.stop()
        self.insta_profile_progress.configure(mode="determinate")
        self.insta_profile_progress.set(0)
        self.update_insta_profile_status(f"Error: {msg}", 1.0, error=True)
        self.insta_download_btn.configure(state="disabled")
        self.prompt_insta_relogin(msg)

    def start_insta_profile_download(self):
        selected_reels = []
        for idx, card in enumerate(self.insta_profile_cards):
            if card.is_selected():
                selected_reels.append(self.insta_profile_reels_list[idx])
                
        if not selected_reels:
            self.update_insta_profile_status("Please select at least one Reel to download.", 1.0, error=True)
            return
            
        page_id = self.insta_profile_entry.get().strip()
        
        for reel in selected_reels:
            self.add_to_download_queue(reel['title'], reel['url'], "instagram", "reel", page_id=page_id)
            
        self.update_insta_profile_status(f"Added {len(selected_reels)} Reels to download queue.", 1.0)

    # --- AUTO-CLIPBOARD DETECT ---
    def toggle_clipboard_monitor(self):
        if self.monitor_clipboard.get():
            self.last_clipboard_text = ""
            threading.Thread(target=self.clipboard_monitor_thread, daemon=True).start()

    def clipboard_monitor_thread(self):
        import time
        while self.monitor_clipboard.get():
            try:
                text = self.clipboard_get().strip()
                if text and text != self.last_clipboard_text:
                    self.last_clipboard_text = text
                    # Simple validation
                    is_yt = "youtube.com" in text or "youtu.be" in text
                    is_insta = "instagram.com" in text
                    
                    if is_yt:
                        self.after(0, lambda url=text: self.handle_clipboard_link(url, "youtube"))
                    elif is_insta:
                        self.after(0, lambda url=text: self.handle_clipboard_link(url, "instagram"))
            except Exception:
                pass
            time.sleep(1.5)

    def handle_clipboard_link(self, url, platform):
        if platform == "youtube":
            self.show_youtube_downloader()
            self.yt_tab_control.set("Video Downloader")
            self.on_yt_tab_changed("Video Downloader")
            self.vid_url_entry.delete(0, "end")
            self.vid_url_entry.insert(0, url)
            self.start_video_fetch()
        elif platform == "instagram":
            self.show_instagram_downloader()
            self.insta_tab_control.set("Single Reel")
            self.on_insta_tab_changed("Single Reel")
            self.insta_url_entry.delete(0, "end")
            self.insta_url_entry.insert(0, url)
            self.start_insta_fetch()

    # --- PARALLEL QUEUE MANAGER ---
    def show_queue_panel(self):
        if not self.queue_frame.winfo_manager():
            self.queue_frame.pack(side="bottom", fill="x", padx=20, pady=(5, 10))

    def hide_queue_panel(self):
        if self.queue_frame.winfo_manager():
            self.queue_frame.pack_forget()

    def add_to_download_queue(self, title, url, platform, download_type, page_id=None):
        self.task_counter += 1
        task_id = f"task_{self.task_counter}"
        
        self.show_queue_panel()
        
        row = ctk.CTkFrame(self.queue_scroll, fg_color="transparent")
        row.pack(fill="x", pady=2, padx=5)
        
        display_title = title if len(title) <= 35 else title[:32] + "..."
        title_lbl = ctk.CTkLabel(row, text=display_title, font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color="#cdd6f4", anchor="w")
        title_lbl.pack(side="left", padx=5)
        
        info_frame = ctk.CTkFrame(row, fg_color="transparent")
        info_frame.pack(side="right", fill="y", padx=5)
        
        status_lbl = ctk.CTkLabel(info_frame, text="Queued...", font=ctk.CTkFont(family="Segoe UI", size=10), text_color="#a6adc8", width=160, anchor="e")
        status_lbl.pack(side="left", padx=5)
        
        prog_bar = ctk.CTkProgressBar(info_frame, width=100, height=8, fg_color="#313244", progress_color="#a6e3a1")
        prog_bar.pack(side="right", padx=5, pady=6)
        prog_bar.set(0)
        
        self.queue_tasks[task_id] = {
            'row': row,
            'title_lbl': title_lbl,
            'status_lbl': status_lbl,
            'prog_bar': prog_bar,
            'status': 'queued'
        }
        
        dest_dir = self.download_dir.get()
        format_preset = self.format_option.get() if platform == "instagram" else self.yt_format_option.get()
        
        self.executor.submit(self.queue_download_worker, task_id, title, url, platform, download_type, format_preset, dest_dir, page_id)

    def queue_download_worker(self, task_id, title, url, platform, download_type, format_preset, dest_dir, page_id=None):
        def progress_cb(d):
            if d['status'] == 'downloading':
                percent = d.get('percent', 0.0)
                speed = d.get('speed', 'N/A')
                eta = d.get('eta', 'N/A')
                self.after(0, lambda: self.update_queue_ui(task_id, percent, speed, eta, 'downloading'))
            elif d['status'] == 'finished':
                self.after(0, lambda: self.update_queue_ui(task_id, 100.0, '0', '0', 'finishing'))
                
        self.after(0, lambda: self.update_queue_ui(task_id, 0.0, 'N/A', 'N/A', 'downloading'))
        
        # Jitter delay staggered start to emulate human behavior
        import random
        import time
        time.sleep(random.uniform(1.0, 4.0))
        
        # Creator subfolder routing
        dest_dir_to_use = dest_dir
        if page_id:
            use_subfolder = False
            if platform == "youtube" and hasattr(self, 'organize_subfolders') and self.organize_subfolders.get():
                use_subfolder = True
            elif platform == "instagram" and hasattr(self, 'insta_organize_subfolders') and self.insta_organize_subfolders.get():
                use_subfolder = True
                
            if use_subfolder:
                import re
                clean_page_id = re.sub(r'[\\/*?:"<>|]', "", page_id).strip()
                folder_name = f"{platform}_{clean_page_id}"
                sub_dest_dir = os.path.join(dest_dir, folder_name)
                os.makedirs(sub_dest_dir, exist_ok=True)
                dest_dir_to_use = sub_dest_dir
        
        success = False
        try:
            import downloader
            if platform == "youtube":
                if download_type == "short":
                    downloader.download_short(url, dest_dir_to_use, progress_callback=progress_cb, format_preset=format_preset)
                else:
                    downloader.download_youtube_video(url, dest_dir_to_use, progress_callback=progress_cb, format_preset=format_preset)
            elif platform == "instagram":
                # Check cookies session setup
                ydl_opts = None
                if hasattr(self, 'insta_session_dir') and hasattr(self, 'insta_username'):
                    session_file = os.path.join(self.insta_session_dir, f"session-{self.insta_username}")
                    if os.path.exists(session_file):
                        pass
                downloader.download_insta_reel(url, dest_dir_to_use, ydl_opts=ydl_opts, progress_callback=progress_cb, format_preset=format_preset)
            success = True
            
            # Record in download history
            if success and page_id:
                try:
                    if platform == "youtube":
                        video_id = url.split('/')[-1]
                    elif platform == "instagram":
                        # url matches format like: https://www.instagram.com/reel/{code}/
                        parts = url.strip('/').split('/')
                        video_id = parts[-1]
                    downloader.add_to_history(platform, page_id, video_id)
                except Exception as ex:
                    print(f"Error logging download to history: {ex}")
                    
        except Exception as e:
            print(f"Queue download error: {e}")
            
        status = 'completed' if success else 'failed'
        self.after(0, lambda: self.update_queue_ui(task_id, 100.0 if success else 0.0, '', '', status))

    def update_queue_ui(self, task_id, percent, speed, eta, status):
        task = self.queue_tasks.get(task_id)
        if not task:
            return
            
        task['status'] = status
        
        if status == 'downloading':
            task['prog_bar'].set(percent / 100.0)
            task['status_lbl'].configure(text=f"{percent:.1f}% | {speed} | {eta}", text_color="#f9e2af")
        elif status == 'finishing':
            task['prog_bar'].set(1.0)
            task['status_lbl'].configure(text="Processing/Merging...", text_color="#89b4fa")
        elif status == 'completed':
            task['prog_bar'].set(1.0)
            task['prog_bar'].configure(progress_color="#a6e3a1")
            task['status_lbl'].configure(text="Finished! ✅", text_color="#a6e3a1")
            self.after(5000, lambda: self.remove_task_from_queue_ui(task_id))
        elif status == 'failed':
            task['prog_bar'].set(0)
            task['prog_bar'].configure(progress_color="#f38ba8")
            task['status_lbl'].configure(text="Failed ❌", text_color="#f38ba8")
            self.after(5000, lambda: self.remove_task_from_queue_ui(task_id))

    def remove_task_from_queue_ui(self, task_id):
        task = self.queue_tasks.pop(task_id, None)
        if task:
            try:
                task['row'].pack_forget()
                task['row'].destroy()
            except:
                pass
        
        if not self.queue_tasks:
            self.hide_queue_panel()

if __name__ == "__main__":
    import traceback
    
    # Check for webview-login argument (used to bypass GUI thread conflicts)
    if "--webview-login" in sys.argv:
        try:
            import webview
            import time
            import json
            
            def check_cookies(window):
                while True:
                    try:
                        cookies = window.get_cookies()
                        sessionid = None
                        cookies_dict = {}
                        for c in cookies:
                            if "instagram.com" in c.domain:
                                cookies_dict[c.name] = {
                                    "value": c.value,
                                    "domain": c.domain,
                                    "path": c.path,
                                }
                                if c.name == 'sessionid':
                                    sessionid = c.value
                        
                        if sessionid:
                            temp_path = os.path.join(os.path.expanduser("~"), ".yt_shorts_downloader_insta_temp_cookies.json")
                            with open(temp_path, "w", encoding="utf-8") as f:
                                json.dump(cookies_dict, f)
                            print("SUCCESS")
                            window.destroy()
                            break
                    except Exception:
                        pass
                    time.sleep(1.0)

            window = webview.create_window(
                'Instagram Secure Login',
                'https://www.instagram.com/accounts/login/',
                width=500,
                height=650,
                resizable=True
            )
            import downloader
            proxy = downloader.get_configured_proxy()
            webview.start(check_cookies, window, http_proxy=proxy)
        except Exception as err:
            print(f"Webview error: {err}")
        sys.exit(0)
        
    # Determine the directory of the executable or script
    if getattr(sys, 'frozen', False):
        log_dir = os.path.dirname(sys.executable)
    else:
        log_dir = os.path.dirname(os.path.abspath(__file__))
        
    log_path = os.path.join(log_dir, "shorts_downloader_debug.log")
    
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write("\n=== App Starting ===\n")
            
        # Check terms acceptance first
        if not check_terms_accepted():
            terms_win = TermsWindow()
            terms_win.mainloop()
            if not terms_win.accepted:
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write("Terms declined. Exiting.\n")
                sys.exit(0)
            else:
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write("Terms accepted.\n")
                    
        app = App()
        
        # Log successful window initialization
        with open(log_path, "a", encoding="utf-8") as f:
            f.write("Window initialized successfully. Entering mainloop.\n")
            
        app.mainloop()
        
        with open(log_path, "a", encoding="utf-8") as f:
            f.write("App closed normally.\n")
            
    except Exception as e:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"CRITICAL EXCEPTION: {e}\n")
            traceback.print_exc(file=f)
        # Re-raise for terminal visibility
        raise e


