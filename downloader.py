import yt_dlp
import os
import re
import sys

def clean_channel_url(url):
    """Normalize YouTube channel URL to point to the /shorts tab."""
    url = url.strip()
    # Remove trailing slashes
    url = re.sub(r'/+$', '', url)
    
    # If it doesn't contain youtube.com or youtu.be, assume it's a handle
    if not (url.startswith('http://') or url.startswith('https://')):
        if url.startswith('@'):
            url = f"https://www.youtube.com/{url}"
        else:
            url = f"https://www.youtube.com/@{url}"
            
    # Append /shorts if not present
    if not url.endswith('/shorts'):
        # If it ends with /videos or /featured etc, replace it or append
        if any(url.endswith(tab) for tab in ['/videos', '/featured', '/playlists', '/community', '/about']):
            url = re.sub(r'/(videos|featured|playlists|community|about)$', '/shorts', url)
        else:
            url = f"{url}/shorts"
            
    return url

def get_top_shorts(channel_url, progress_callback=None, limit=100):
    """
    Scrapes the channel's shorts page, fetches up to `limit` entries,
    sorts them by view count, and returns the top 10.
    """
    clean_url = clean_channel_url(channel_url)
    if progress_callback:
        progress_callback("Connecting to YouTube...", 0.1)
        
    ydl_opts = {
        'extract_flat': True,
        'playlistend': limit,
        'quiet': True,
        'no_warnings': True,
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        if progress_callback:
            progress_callback("Fetching shorts list...", 0.4)
        info = ydl.extract_info(clean_url, download=False)
        
        entries = info.get('entries', [])
        if progress_callback:
            progress_callback(f"Found {len(entries)} shorts. Sorting...", 0.8)
            
        # Filter entries and get view count safely
        valid_shorts = []
        for entry in entries:
            if not entry:
                continue
            # Ensure it is a short video (URL usually contains /shorts/)
            url = entry.get('url') or ''
            if '/shorts/' in url or entry.get('id'):
                title = entry.get('title', 'Untitled Short')
                views = entry.get('view_count')
                # If view_count is missing, default to 0
                views_int = int(views) if views is not None else 0
                
                # Get best thumbnail URL
                thumbnails = entry.get('thumbnails', [])
                thumb_url = ""
                if thumbnails:
                    # Try to get the last thumbnail (usually highest res)
                    thumb_url = thumbnails[-1].get('url', '')
                
                video_id = entry.get('id') or url.split('/')[-1]
                short_url = f"https://www.youtube.com/shorts/{video_id}"
                
                valid_shorts.append({
                    'id': video_id,
                    'title': title,
                    'views': views_int,
                    'url': short_url,
                    'thumbnail': thumb_url
                })
        
        # Sort by view count descending
        valid_shorts.sort(key=lambda x: x['views'], reverse=True)
        
        # Return top 10
        top_10 = valid_shorts[:10]
        
        if progress_callback:
            progress_callback("Done!", 1.0)
            
        return top_10

def download_short(video_url, download_dir, progress_callback=None):
    """
    Downloads a single short using yt-dlp.
    progress_callback receives a dictionary with progress info.
    """
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)
        
    def ytdl_hook(d):
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            downloaded = d.get('downloaded_bytes', 0)
            percent = (downloaded / total * 100) if total > 0 else 0
            speed = d.get('_speed_str', 'N/A')
            eta = d.get('_eta_str', 'N/A')
            if progress_callback:
                progress_callback({
                    'status': 'downloading',
                    'percent': percent,
                    'speed': speed,
                    'eta': eta
                })
        elif d['status'] == 'finished':
            if progress_callback:
                progress_callback({
                    'status': 'finished',
                    'percent': 100.0,
                    'speed': '0',
                    'eta': '0'
                })

    ydl_opts = {
        'outtmpl': os.path.join(download_dir, '%(title)s.%(ext)s'),
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'merge_output_format': 'mp4',
        'progress_hooks': [ytdl_hook],
        'quiet': True,
        'no_warnings': True,
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=True)
        filename = ydl.prepare_filename(info)
        # Handle case where file extension changes during merge (e.g. mkv/mp4)
        base, _ = os.path.splitext(filename)
        # Search if the file exists with another extension, or check the actual file written
        if os.path.exists(filename):
            return filename
        # Fallback search
        for ext in ['.mp4', '.mkv', '.webm']:
            if os.path.exists(base + ext):
                return base + ext
        return filename

def export_instaloader_cookies(username):
    try:
        import instaloader
        L = instaloader.Instaloader()
        session_file = os.path.join(
            os.environ.get("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local")),
            "Instaloader",
            f"session-{username}"
        )
        if os.path.exists(session_file):
            L.load_session_from_file(username, filename=session_file)
            cookie_jar = L.context._session.cookies
            
            cookies_txt_path = os.path.join(os.path.expanduser("~"), ".yt_shorts_downloader_insta_cookies.txt")
            with open(cookies_txt_path, "w", encoding="utf-8") as f:
                f.write("# Netscape HTTP Cookie File\n")
                f.write("# http://curl.haxx.se/rfc/cookie_spec.html\n")
                f.write("# This is a generated file! Do not edit.\n\n")
                for cookie in cookie_jar:
                    domain = cookie.domain
                    flag = "TRUE" if domain.startswith(".") else "FALSE"
                    path = cookie.path
                    secure = "TRUE" if cookie.secure else "FALSE"
                    expiration = str(cookie.expires or 0)
                    name = cookie.name
                    value = cookie.value
                    f.write(f"{domain}\t{flag}\t{path}\t{secure}\t{expiration}\t{name}\t{value}\n")
            return cookies_txt_path
    except Exception as e:
        print(f"Error exporting Instaloader cookies: {e}")
    return None

def get_insta_reel_info(reel_url):
    """
    Extracts metadata from a public Instagram Reel.
    Attempts using saved encrypted credentials first, then without cookies, and finally browser fallbacks.
    """
    browsers = ['chrome', 'edge', 'firefox', 'opera', 'brave', 'vivaldi']
    
    # Try list of options (No cookies first, then different browser cookies)
    ydl_opts_list = [{'quiet': True, 'no_warnings': True}]
    
    # Check for saved credentials
    config_path = os.path.join(os.path.expanduser("~"), ".yt_shorts_downloader_insta")
    if os.path.exists(config_path):
        try:
            import crypto_utils
            with open(config_path, "r", encoding="utf-8") as f:
                enc_str = f.read().strip()
            creds = crypto_utils.decrypt_credentials(enc_str)
            if creds:
                user, pw = creds
                cookies_path = export_instaloader_cookies(user)
                if cookies_path and os.path.exists(cookies_path):
                    ydl_opts_list.insert(0, {
                        'cookiefile': cookies_path,
                        'quiet': True,
                        'no_warnings': True,
                    })
        except Exception as e:
            print(f"Error loading saved Instagram credentials: {e}")
            
    # Check if a manual cookies.txt file is present in the app/executable directory
    if getattr(sys, 'frozen', False):
        app_dir = os.path.dirname(sys.executable)
    else:
        app_dir = os.path.dirname(os.path.abspath(__file__))
        
    manual_cookies = os.path.join(app_dir, "cookies.txt")
    if os.path.exists(manual_cookies):
        # Insert cookies.txt at the very beginning of the fallback chain (after credentials if present)
        idx = 1 if len(ydl_opts_list) > 1 else 0
        ydl_opts_list.insert(idx, {
            'cookiefile': manual_cookies,
            'quiet': True,
            'no_warnings': True,
        })
        
    for b in browsers:
        ydl_opts_list.append({
            'cookiesfrombrowser': (b,),
            'quiet': True,
            'no_warnings': True,
        })
        
    last_err = None
    for opts in ydl_opts_list:
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(reel_url, download=False)
                
                title = info.get('title') or info.get('description') or 'Instagram Reel'
                # Clean up title if it contains huge descriptions/hashtags
                title = title.split('\n')[0].strip() # Take first line
                if len(title) > 80:
                    title = title[:80] + "..."
                if not title:
                    title = "Instagram Reel"
                    
                thumbnails = info.get('thumbnails', [])
                thumb_url = info.get('thumbnail', '')
                if not thumb_url and thumbnails:
                    thumb_url = thumbnails[-1].get('url', '')
                    
                # Extract clean video ID from URL
                video_id = info.get('id')
                if not video_id:
                    # Fallback URL extraction
                    match = re.search(r'/reel/([^/?#]+)', reel_url)
                    video_id = match.group(1) if match else "reel"
                
                return {
                    'id': video_id,
                    'title': title,
                    'views': info.get('view_count', 0) or 0,
                    'url': reel_url,
                    'thumbnail': thumb_url,
                    'uploader': info.get('uploader') or info.get('owner_username') or 'Unknown',
                    'duration': info.get('duration', 0) or 0,
                    'ydl_opts': opts # Save options that worked for downloading
                }
        except Exception as e:
            last_err = e
            continue
            
    # If all options fail
    err_str = str(last_err)
    if "Instagram sent an empty media response" in err_str:
        raise Exception("Instagram blocked anonymous access. Make sure you are logged into Instagram in Chrome or Edge, or try a different link.")
    raise Exception(f"Failed to fetch Reel: {last_err}")

def download_insta_reel(reel_url, download_dir, ydl_opts=None, progress_callback=None):
    """
    Downloads a single Instagram Reel using working ydl_opts.
    """
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)
        
    def ytdl_hook(d):
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            downloaded = d.get('downloaded_bytes', 0)
            percent = (downloaded / total * 100) if total > 0 else 0
            speed = d.get('_speed_str', 'N/A')
            eta = d.get('_eta_str', 'N/A')
            if progress_callback:
                progress_callback({
                    'status': 'downloading',
                    'percent': percent,
                    'speed': speed,
                    'eta': eta
                })
        elif d['status'] == 'finished':
            if progress_callback:
                progress_callback({
                    'status': 'finished',
                    'percent': 100.0,
                    'speed': '0',
                    'eta': '0'
                })

    opts = ydl_opts.copy() if ydl_opts else {'quiet': True, 'no_warnings': True}
    opts.update({
        'outtmpl': os.path.join(download_dir, '%(title)s.%(ext)s'),
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'merge_output_format': 'mp4',
        'progress_hooks': [ytdl_hook],
        'quiet': True,
        'no_warnings': True,
    })
    
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(reel_url, download=True)
        filename = ydl.prepare_filename(info)
        base, _ = os.path.splitext(filename)
        if os.path.exists(filename):
            return filename
        for ext in ['.mp4', '.mkv', '.webm']:
            if os.path.exists(base + ext):
                return base + ext
        return filename

