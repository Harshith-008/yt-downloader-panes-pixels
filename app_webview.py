import os
import sys

# Ensure the application directory is in the import path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import threading
import time
import webview
import server

# Resolve local resource paths cleanly
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def start_backend():
    # Run the HTTP api server on 127.0.0.1:49152
    try:
        server.run_server(port=49152)
    except Exception as e:
        print(f"Error starting API server: {e}")

def main():
    # Start the backend API server thread
    backend_thread = threading.Thread(target=start_backend, daemon=True)
    backend_thread.start()
    
    # Wait for the backend server to bind
    time.sleep(0.5)
    
    # Determine the URL/path to load
    is_frozen = getattr(sys, 'frozen', False)
    if is_frozen:
        # Loaded by PyInstaller bundle - point to local index.html
        url = resource_path(os.path.join("dist_web", "index.html"))
        if not os.path.exists(url):
            # Fallback path check
            url = resource_path("index.html")
    else:
        # In development, try Vite dev server if running, else load local build
        # Let's test if Vite server is up or default to Vite address
        url = "http://localhost:5173"
        
    print(f"Loading webview content from: {url}")
    
    # Create the native OS window
    window = webview.create_window(
        title="YT Downloader by Panes & Pixels",
        url=url,
        width=740,
        height=820,
        min_size=(680, 720),
        background_color="#11111b"
    )
    
    # Start the webview loop
    # On Windows, this runs the Edge Chromium (WebView2) runtime
    webview.start(debug=not is_frozen)

if __name__ == '__main__':
    main()
