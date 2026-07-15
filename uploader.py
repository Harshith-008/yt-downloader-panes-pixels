import os
import json
import pickle
import subprocess
import requests
import downloader
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from instagrapi import Client

def uniquify_video(input_path, output_path, mirror=False, speed=False, contrast=False, scrub=True, log_callback=None):
    """
    Applies FFmpeg visual adjustments to make the video appear unique to algorithms.
    """
    if log_callback:
        log_callback("Applying visual uniquifier adjustments via FFmpeg...")
        
    vf_filters = []
    if mirror:
        vf_filters.append("hflip")
    if contrast:
        vf_filters.append("eq=contrast=1.02:saturation=1.01")
        
    # Build first command with speed and audio (if audio exists)
    success = False
    last_err = None
    
    if speed:
        v_filter = ",".join(vf_filters) if vf_filters else "copy"
        v_filter = f"{v_filter},setpts=0.99*PTS" if v_filter != "copy" else "setpts=0.99*PTS"
        
        # Try processing both video and audio
        cmd = ["ffmpeg", "-y", "-i", input_path, "-filter_complex", f"[0:v]{v_filter}[v];[0:a]atempo=1.01[a]", "-map", "[v]", "-map", "[a]"]
        if scrub:
            cmd.extend(["-map_metadata", "-1"])
        cmd.append(output_path)
        
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, check=True)
            success = True
        except Exception as e:
            last_err = e
            
        if not success:
            # Fall back to video only (in case audio is missing or incompatible)
            if log_callback:
                log_callback("Audio speed adjustment failed (likely silent video). Retrying video-only...")
            cmd = ["ffmpeg", "-y", "-i", input_path]
            v_filter = ",".join(vf_filters) if vf_filters else "copy"
            v_filter = f"{v_filter},setpts=0.99*PTS" if v_filter != "copy" else "setpts=0.99*PTS"
            cmd.extend(["-vf", v_filter])
            if scrub:
                cmd.extend(["-map_metadata", "-1"])
            cmd.append(output_path)
            
            try:
                subprocess.run(cmd, capture_output=True, text=True, check=True)
                success = True
            except Exception as e2:
                last_err = e2
    else:
        # Standard filter without speed
        cmd = ["ffmpeg", "-y", "-i", input_path]
        if vf_filters:
            cmd.extend(["-vf", ",".join(vf_filters)])
        if scrub:
            cmd.extend(["-map_metadata", "-1"])
        cmd.append(output_path)
        
        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            success = True
        except Exception as e:
            last_err = e
            
    if not success:
        raise Exception(f"FFmpeg processing failed: {last_err}")
        
    if log_callback:
        log_callback("Uniquifier complete!")


def upload_to_instagram(video_path, caption, log_callback=None):
    """
    Uploads a video to Instagram Reels using the active web session cookies.
    """
    if log_callback:
        log_callback("Connecting to Instagram private API...")
        
    config_path = os.path.join(os.path.expanduser("~"), ".yt_shorts_downloader_insta")
    if not os.path.exists(config_path):
        raise Exception("Instagram credentials not found. Please login in Settings first.")
        
    import crypto_utils
    with open(config_path, "r", encoding="utf-8") as f:
        enc_str = f.read().strip()
    creds = crypto_utils.decrypt_credentials(enc_str)
    if not creds:
        raise Exception("Could not decrypt saved credentials.")
        
    username = creds[0]
    session_dir = os.path.join(
        os.environ.get("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local")),
        "Instaloader"
    )
    session_file = os.path.join(session_dir, f"insta_web_session_{username}.json")
    if not os.path.exists(session_file):
        raise Exception(f"Instagram session file for {username} not found. Please login in Settings first.")
        
    with open(session_file, "r", encoding="utf-8") as f:
        cookies_dict = json.load(f)
        
    cl = Client()
    proxy = downloader.get_configured_proxy()
    if proxy:
        cl.set_proxy(proxy)
        if log_callback:
            log_callback(f"Using proxy: {proxy}")
            
    cookie_jar = requests.cookies.RequestsCookieJar()
    for name, info in cookies_dict.items():
        cookie_jar.set(name, info["value"], domain=info["domain"], path=info["path"])
        
    cl.set_cookies(cookie_jar)
    
    if log_callback:
        log_callback("Uploading Reels media payload (this can take 1-2 minutes)...")
        
    # Upload video clip
    media = cl.clip_upload(video_path, caption)
    
    if log_callback:
        log_callback(f"Instagram upload successful! Media ID: {media.pk}")
    return media.pk


def upload_to_youtube(video_path, title, caption, publish_at=None, log_callback=None):
    """
    Uploads a video to YouTube Shorts using the official YouTube Data API v3.
    """
    if log_callback:
        log_callback("Connecting to YouTube Data API...")
        
    SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
    token_path = os.path.join(os.path.expanduser("~"), ".yt_shorts_downloader_yt_token.pickle")
    creds = None
    
    if os.path.exists(token_path):
        try:
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)
        except Exception:
            pass
            
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            if log_callback:
                log_callback("Refreshing expired YouTube OAuth credentials...")
            creds.refresh(Request())
        else:
            if log_callback:
                log_callback("OAuth credentials missing/invalid. Authorizing via browser...")
                
            secrets_paths = [
                os.path.join(os.path.expanduser("~"), "client_secrets.json"),
                os.path.join(os.path.expanduser("~"), "Downloads", "client_secrets.json"),
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "client_secrets.json")
            ]
            secrets_file = None
            for p in secrets_paths:
                if os.path.exists(p):
                    secrets_file = p
                    break
            if not secrets_file:
                raise Exception(
                    "client_secrets.json not found! Please download your client_secrets.json "
                    "from Google Cloud Developer Console and place it in your User folder."
                )
                
            flow = InstalledAppFlow.from_client_secrets_file(secrets_file, SCOPES)
            # Run local server flow to open browser login tab
            creds = flow.run_local_server(port=0)
            
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)
            
    youtube = build('youtube', 'v3', credentials=creds)
    
    # Ensure title fits within YouTube's 100 character limit
    safe_title = title if len(title) <= 100 else title[:97] + "..."
    
    # If scheduled to publish at a future date/time, status must be private
    privacy_status = 'private' if publish_at else 'public'
    
    body = {
        'snippet': {
            'title': safe_title,
            'description': caption,
            'categoryId': '22'  # People & Blogs
        },
        'status': {
            'privacyStatus': privacy_status,
            'selfDeclaredMadeForKids': False
        }
    }
    
    if publish_at:
        body['status']['publishAt'] = publish_at
        if log_callback:
            log_callback(f"Setting YouTube Studio schedule: {publish_at}")
    
    media = MediaFileUpload(video_path, chunksize=1024*1024, resumable=True, mimetype='video/*')
    request = youtube.videos().insert(
        part='snippet,status',
        body=body,
        media_body=media
    )
    
    if log_callback:
        log_callback("Uploading video bytes to YouTube servers...")
        
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status and log_callback:
            log_callback(f"YouTube Upload Progress: {int(status.progress() * 100)}%")
            
    video_id = response.get('id', 'Unknown')
    if log_callback:
        log_callback(f"YouTube upload successful! Video ID: {video_id}")
    return video_id
