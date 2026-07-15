import os
import sys
import json
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

import downloader
import uploader
import scheduler_db

# Log queue for the live console
log_lock = threading.Lock()
scheduler_logs = []

def add_log(msg):
    with log_lock:
        print(f"[LOG] {msg}")
        scheduler_logs.append(f"[{time.strftime('%H:%M:%S')}] {msg}")
        if len(scheduler_logs) > 200:
            scheduler_logs.pop(0)

# Global active downloads registry to track progress
download_progress = {}
progress_lock = threading.Lock()

def update_progress(task_id, percent, speed, eta, status):
    with progress_lock:
        download_progress[task_id] = {
            "percent": percent,
            "speed": speed,
            "slate": eta, # fallback mapping
            "eta": eta,
            "status": status
        }

# Background scheduler loop
def scheduler_loop_worker():
    add_log("Background scheduler daemon started.")
    while True:
        try:
            tasks = scheduler_db.load_schedule()
            from datetime import datetime
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            now_dt = datetime.strptime(now_str, "%Y-%m-%d %H:%M")
            
            for task in tasks:
                if task["status"] == "scheduled":
                    try:
                        task_time_dt = datetime.strptime(task["scheduled_time"], "%Y-%m-%d %H:%M")
                        if now_dt >= task_time_dt:
                            scheduler_db.update_task_status(task["id"], "uploading")
                            add_log(f"Starting scheduled upload for task {task['id']}...")
                            threading.Thread(target=execute_upload_worker, args=(task,), daemon=True).start()
                    except Exception as e:
                        print(f"Error checking task schedule: {e}")
        except Exception as e:
            print(f"Scheduler daemon loop error: {e}")
        time.sleep(15)

def execute_upload_worker(task):
    task_id = task["id"]
    video_path = task["video_path"]
    platform = task["platform"]
    caption = task["caption"]
    opts = task["uniquifier_opts"]
    publish_at = task.get("publish_at")
    
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
                log_callback=lambda msg: add_log(msg)
            )
        except Exception as e:
            add_log(f"Uniquifier failed: {e}")
            scheduler_db.update_task_status(task_id, "failed", f"Uniquifier failed: {e}")
            return
            
    try:
        if platform == "instagram":
            uploader.upload_to_instagram(
                video_path=processed_path,
                caption=caption,
                log_callback=lambda msg: add_log(msg)
            )
        elif platform == "youtube":
            title = os.path.splitext(os.path.basename(video_path))[0]
            uploader.upload_to_youtube(
                video_path=processed_path,
                title=title,
                caption=caption,
                publish_at=publish_at,
                log_callback=lambda msg: add_log(msg)
            )
            
        scheduler_db.update_task_status(task_id, "published")
        add_log(f"Task {task_id} uploaded successfully!")
        
        if processed_path != video_path and os.path.exists(processed_path):
            try:
                os.remove(processed_path)
            except:
                pass
    except Exception as ex:
        add_log(f"Upload failed: {ex}")
        scheduler_db.update_task_status(task_id, "failed", f"Upload failed: {ex}")
        if processed_path != video_path and os.path.exists(processed_path):
            try:
                os.remove(processed_path)
            except:
                pass

class APIHandler(BaseHTTPRequestHandler):
    def end_headers(self):
        # Enable CORS
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200, "OK")
        self.end_headers()

    def respond_json(self, status_code, data):
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def read_json_body(self):
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length == 0:
            return {}
        body = self.rfile.read(content_length)
        return json.loads(body.decode('utf-8'))

    def do_GET(self):
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        
        if path == "/api/scheduler/list":
            tasks = scheduler_db.load_schedule()
            self.respond_json(200, tasks)
            
        elif path == "/api/scheduler/logs":
            with log_lock:
                self.respond_json(200, {"logs": list(scheduler_logs)})
                
        elif path == "/api/downloads/progress":
            with progress_lock:
                self.respond_json(200, dict(download_progress))
                
        elif path == "/api/config/dir":
            default_dir = os.path.join(os.path.expanduser("~"), "Downloads")
            self.respond_json(200, {"download_dir": default_dir})
            
        else:
            self.respond_json(404, {"error": "Not Found"})

    def do_POST(self):
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        
        try:
            body = self.read_json_body()
        except Exception as e:
            self.respond_json(400, {"error": f"Invalid JSON body: {e}"})
            return

        try:
            if path == "/api/yt/fetch":
                url = body.get("url")
                if not url:
                    self.respond_json(400, {"error": "URL parameter missing"})
                    return
                
                if "youtube.com" in url or "youtu.be" in url:
                    if "/shorts" in url or "/channel/" in url or "/c/" in url or "/@" in url or "youtube.com/user" in url:
                        cleaned = downloader.clean_channel_url(url)
                        shorts = downloader.get_top_shorts(cleaned, limit=50)
                        self.respond_json(200, {"type": "channel", "items": shorts})
                    else:
                        info = downloader.get_youtube_video_info(url)
                        self.respond_json(200, {"type": "video", "items": [info]})
                else:
                    self.respond_json(400, {"error": "Invalid YouTube URL"})

            elif path == "/api/yt/download":
                url = body.get("url")
                target_dir = body.get("download_dir", os.path.join(os.path.expanduser("~"), "Downloads"))
                task_id = body.get("task_id", f"dl_{int(time.time())}")
                
                if not url:
                    self.respond_json(400, {"error": "URL parameter missing"})
                    return
                
                def run_dl():
                    try:
                        update_progress(task_id, 0, "0 KB/s", "Unknown", "downloading")
                        
                        def progress_cb(d):
                            if d.get("status") == "downloading":
                                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                                downloaded = d.get("downloaded_bytes", 0)
                                pct = int((downloaded / total) * 100) if total else 0
                                speed = d.get("_speed_str", "0 KB/s")
                                eta = d.get("_eta_str", "Unknown")
                                update_progress(task_id, pct, speed, eta, "downloading")
                            elif d.get("status") == "finished":
                                update_progress(task_id, 100, "0 KB/s", "0s", "completed")
                                
                        if "/shorts/" in url or "youtube.com" not in url:
                            downloader.download_short(url, target_dir, progress_callback=progress_cb)
                        else:
                            downloader.download_youtube_video(url, target_dir, progress_callback=progress_cb)
                    except Exception as err:
                        update_progress(task_id, 0, "0 KB/s", "0s", f"error: {err}")
                
                threading.Thread(target=run_dl, daemon=True).start()
                self.respond_json(200, {"message": "Download started", "task_id": task_id})

            elif path == "/api/insta/fetch":
                url = body.get("url")
                if not url:
                    self.respond_json(400, {"error": "URL parameter missing"})
                    return
                
                if "instagram.com" in url:
                    if "/reel/" in url or "/p/" in url:
                        info = downloader.get_insta_reel_info(url)
                        self.respond_json(200, {"type": "reel", "items": [info]})
                    else:
                        clean_url = url.rstrip('/')
                        username = clean_url.split('/')[-1]
                        session_dir = os.path.join(
                            os.environ.get("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local")),
                            "Instaloader"
                        )
                        config_path = os.path.join(os.path.expanduser("~"), ".yt_shorts_downloader_insta")
                        auth_user = None
                        if os.path.exists(config_path):
                            try:
                                with open(config_path, "r", encoding="utf-8") as f:
                                    enc_str = f.read().strip()
                                import crypto_utils
                                creds = crypto_utils.decrypt_credentials(enc_str)
                                if creds:
                                    auth_user = creds[0]
                            except:
                                pass
                                
                        reels = downloader.get_insta_profile_reels(username, session_dir, auth_username=auth_user)
                        self.respond_json(200, {"type": "profile", "items": reels})
                else:
                    self.respond_json(400, {"error": "Invalid Instagram URL"})

            elif path == "/api/insta/download":
                url = body.get("url")
                target_dir = body.get("download_dir", os.path.join(os.path.expanduser("~"), "Downloads"))
                task_id = body.get("task_id", f"dl_{int(time.time())}")
                
                if not url:
                    self.respond_json(400, {"error": "URL parameter missing"})
                    return
                
                def run_insta_dl():
                    try:
                        update_progress(task_id, 0, "0 KB/s", "Unknown", "downloading")
                        
                        def progress_cb(d):
                            if d.get("status") == "downloading":
                                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                                downloaded = d.get("downloaded_bytes", 0)
                                pct = int((downloaded / total) * 100) if total else 0
                                speed = d.get("_speed_str", "0 KB/s")
                                eta = d.get("_eta_str", "Unknown")
                                update_progress(task_id, pct, speed, eta, "downloading")
                            elif d.get("status") == "finished":
                                update_progress(task_id, 100, "0 KB/s", "0s", "completed")
                                
                        downloader.download_insta_reel(url, target_dir, progress_callback=progress_cb)
                    except Exception as err:
                        update_progress(task_id, 0, "0 KB/s", "0s", f"error: {err}")
                        
                threading.Thread(target=run_insta_dl, daemon=True).start()
                self.respond_json(200, {"message": "Instagram download started", "task_id": task_id})

            elif path == "/api/scheduler/add":
                video_path = body.get("video_path")
                platform = body.get("platform")
                caption = body.get("caption", "")
                scheduled_time = body.get("scheduled_time")
                opts = body.get("uniquifier_opts", {"mirror": False, "speed": False, "contrast": False, "scrub": True})
                publish_at = body.get("publish_at")
                
                if not video_path or not platform or not scheduled_time:
                    self.respond_json(400, {"error": "Missing required parameters"})
                    return
                
                task = scheduler_db.add_task(
                    video_path=video_path,
                    platform=platform,
                    caption=caption,
                    scheduled_time_str=scheduled_time,
                    uniquifier_opts=opts,
                    publish_at=publish_at
                )
                
                if platform == "youtube":
                    task["status"] = "uploading"
                    scheduler_db.update_task_status(task["id"], "uploading")
                    add_log(f"Initiating background uploader for YouTube task {task['id']}...")
                    threading.Thread(target=execute_upload_worker, args=(task,), daemon=True).start()
                else:
                    add_log(f"Scheduled local upload for {os.path.basename(video_path)} at {scheduled_time}.")
                    
                self.respond_json(200, task)

            elif path == "/api/scheduler/cancel":
                task_id = body.get("task_id")
                if not task_id:
                    self.respond_json(400, {"error": "task_id parameter missing"})
                    return
                scheduler_db.delete_task(task_id)
                add_log(f"Cancelled task {task_id}")
                self.respond_json(200, {"status": "success"})

            elif path == "/api/scheduler/publish_now":
                task_id = body.get("task_id")
                if not task_id:
                    self.respond_json(400, {"error": "task_id parameter missing"})
                    return
                
                tasks = scheduler_db.load_schedule()
                target_task = None
                for t in tasks:
                    if t["id"] == task_id:
                        target_task = t
                        break
                
                if not target_task:
                    self.respond_json(404, {"error": "Task not found"})
                    return
                
                scheduler_db.update_task_status(task_id, "uploading")
                add_log(f"Bypassing scheduled timer, uploading task {task_id} now...")
                threading.Thread(target=execute_upload_worker, args=(target_task,), daemon=True).start()
                self.respond_json(200, {"status": "success"})

            elif path == "/api/insta/login":
                user = body.get("username")
                pw = body.get("password")
                proxy = body.get("proxy")
                
                if not user or not pw:
                    self.respond_json(400, {"error": "Username/Password missing"})
                    return
                
                def run_login():
                    try:
                        res = downloader.instagram_web_login(user, pw)
                        if res[0]:
                            add_log(f"Instagram login successful for {user}")
                        elif res[1]:
                            add_log(f"Instagram login for {user} requires 2FA verification")
                    except Exception as err:
                        add_log(f"Instagram login failed: {err}")
                        
                threading.Thread(target=run_login, daemon=True).start()
                self.respond_json(200, {"status": "initiated"})

            else:
                self.respond_json(404, {"error": "Not Found"})
                
        except Exception as e:
            self.respond_json(500, {"error": str(e)})

def run_server(port=49152):
    server_address = ('127.0.0.1', port)
    httpd = HTTPServer(server_address, APIHandler)
    print(f"Backend API server running on http://127.0.0.1:{port}")
    
    daemon = threading.Thread(target=scheduler_loop_worker, daemon=True)
    daemon.start()
    
    httpd.serve_forever()

if __name__ == '__main__':
    run_server()
