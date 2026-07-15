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

import json

HISTORY_FILE = os.path.join(os.path.expanduser("~"), ".yt_shorts_downloader_history.json")

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"youtube": {}, "instagram": {}}

def save_history(history):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        print(f"Error saving download history: {e}")

def add_to_history(platform, page_id, video_id):
    history = load_history()
    if platform not in history:
        history[platform] = {}
    
    # Normalize page_id
    page_id = page_id.lower().strip()
    if page_id not in history[platform]:
        history[platform][page_id] = []
        
    if video_id not in history[platform][page_id]:
        history[platform][page_id].append(video_id)
        save_history(history)

def is_downloaded(platform, page_id, video_id):
    history = load_history()
    page_id = page_id.lower().strip()
    return video_id in history.get(platform, {}).get(page_id, [])

def get_configured_proxy():
    config_path = os.path.join(os.path.expanduser("~"), ".yt_shorts_downloader_insta")
    if os.path.exists(config_path):
        try:
            import crypto_utils
            with open(config_path, "r", encoding="utf-8") as f:
                enc_str = f.read().strip()
            creds = crypto_utils.decrypt_credentials(enc_str)
            if creds and len(creds) > 2:
                proxy = creds[2].strip()
                return proxy if proxy else None
        except Exception:
            pass
    return None

def apply_proxy_to_ydl_opts(opts):
    proxy = get_configured_proxy()
    if proxy:
        opts['proxy'] = proxy
    return opts

def get_top_shorts(channel_url, progress_callback=None, limit=100):
    """
    Scrapes the channel's shorts page, fetches up to `limit` entries,
    filters out already downloaded ones, sorts them by view count,
    and returns the top 10.
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
    ydl_opts = apply_proxy_to_ydl_opts(ydl_opts)
    
    # Extract channel identifier for history lookup
    # e.g., https://www.youtube.com/@handle/shorts -> @handle
    parts = clean_url.split('/')
    page_id = (parts[-2] if len(parts) >= 2 else channel_url).lower().strip()
    
    # Load downloaded history for this channel
    history = load_history()
    downloaded_ids = history.get("youtube", {}).get(page_id, [])
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        if progress_callback:
            progress_callback("Fetching shorts list...", 0.4)
        info = ydl.extract_info(clean_url, download=False)
        
        entries = info.get('entries', [])
        if progress_callback:
            progress_callback(f"Found {len(entries)} shorts. Sorting...", 0.8)
            
        valid_shorts = []
        for entry in entries:
            if not entry:
                continue
            url = entry.get('url') or ''
            if '/shorts/' in url or entry.get('id'):
                video_id = entry.get('id') or url.split('/')[-1]
                
                # Exclude already downloaded shorts
                if video_id in downloaded_ids:
                    continue
                    
                title = entry.get('title', 'Untitled Short')
                views = entry.get('view_count')
                views_int = int(views) if views is not None else 0
                
                thumbnails = entry.get('thumbnails', [])
                thumb_url = ""
                if thumbnails:
                    thumb_url = thumbnails[-1].get('url', '')
                
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

def get_ydl_format_options(format_preset):
    opts = {}
    if format_preset == "Audio Only (MP3)":
        opts['format'] = 'bestaudio/best'
        opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
    elif format_preset == "1080p (Video)":
        opts['format'] = 'bestvideo[height<=1080]+bestaudio/best'
        opts['merge_output_format'] = 'mp4'
    elif format_preset == "720p (Video)":
        opts['format'] = 'bestvideo[height<=720]+bestaudio/best'
        opts['merge_output_format'] = 'mp4'
    elif format_preset == "480p (Video)":
        opts['format'] = 'bestvideo[height<=480]+bestaudio/best'
        opts['merge_output_format'] = 'mp4'
    else:
        opts['format'] = 'bestvideo+bestaudio/best'
        opts['merge_output_format'] = 'mp4'
    return opts

def download_short(video_url, download_dir, progress_callback=None, format_preset="Best Quality (Video)"):
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
        'progress_hooks': [ytdl_hook],
        'quiet': True,
        'no_warnings': True,
    }
    
    # Merge format options based on preset
    ydl_opts.update(get_ydl_format_options(format_preset))
    ydl_opts = apply_proxy_to_ydl_opts(ydl_opts)
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=True)
        filename = ydl.prepare_filename(info)
        base, _ = os.path.splitext(filename)
        if os.path.exists(filename):
            return filename
        for ext in ['.mp4', '.mkv', '.webm', '.mp3']:
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
        opts = apply_proxy_to_ydl_opts(opts)
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

def download_insta_reel_via_instaloader(reel_url, download_dir, session_dir, auth_username=None, progress_callback=None):
    import instaloader
    import re
    
    match = re.search(r'/(?:reel|p|reels)/([a-zA-Z0-9_-]+)', reel_url)
    if not match:
        raise Exception("Invalid Instagram Reel URL format.")
    shortcode = match.group(1)
    
    L = instaloader.Instaloader(
        dirname_pattern=download_dir,
        filename_pattern='{shortcode}',
        download_video_thumbnails=False,
        download_geotags=False,
        download_comments=False,
        save_metadata=False,
        post_metadata_txt_pattern='',
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    )
    proxy = get_configured_proxy()
    if proxy:
        L.context._session.proxies = {"http": proxy, "https": proxy}
    
    session_loaded = False
    if auth_username and session_dir:
        session_file = os.path.join(session_dir, f"session-{auth_username}")
        if os.path.exists(session_file):
            try:
                L.load_session_from_file(auth_username, filename=session_file)
                session_loaded = True
            except Exception as e:
                print(f"Error loading session in Instaloader download: {e}")
                
    if not session_loaded:
        load_cookies_to_instaloader(L)
        
    try:
        post = instaloader.Post.from_shortcode(L.context, shortcode)
        if not post.is_video:
            raise Exception("This Instagram post is not a video.")
            
        if progress_callback:
            progress_callback({'status': 'downloading', 'percent': 50.0, 'speed': 'N/A', 'eta': 'N/A'})
            
        L.download_post(post, target=download_dir)
        
        if progress_callback:
            progress_callback({'status': 'finished', 'percent': 100.0, 'speed': '0', 'eta': '0'})
            
        expected_file = os.path.join(download_dir, f"{shortcode}.mp4")
        if os.path.exists(expected_file):
            title = post.caption or f"instagram_reel_{shortcode}"
            title = re.sub(r'[\\/*?:"<>|]', "", title).split('\n')[0].strip()
            if len(title) > 60:
                title = title[:60]
            new_file = os.path.join(download_dir, f"{title}.mp4")
            try:
                if os.path.exists(new_file):
                    os.remove(new_file)
                os.rename(expected_file, new_file)
                return new_file
            except:
                return expected_file
        return expected_file
    except Exception as e:
        raise Exception(f"Instaloader download failed: {e}")

def download_insta_reel(reel_url, download_dir, ydl_opts=None, progress_callback=None, format_preset="Best Quality (Video)"):
    """
    Downloads a single Instagram Reel. 
    Tries Instaloader first (using active sessions/cookies), falls back to yt-dlp.
    """
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)
        
    # Read saved auth credentials for Instaloader
    auth_username = None
    config_path = os.path.join(os.path.expanduser("~"), ".yt_shorts_downloader_insta")
    if os.path.exists(config_path):
        try:
            import crypto_utils
            with open(config_path, "r", encoding="utf-8") as f:
                enc_str = f.read().strip()
            creds = crypto_utils.decrypt_credentials(enc_str)
            if creds:
                auth_username = creds[0]
        except Exception as e:
            print(f"Error loading username for Instaloader downloader: {e}")
            
    session_dir = os.path.join(
        os.environ.get("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local")),
        "Instaloader"
    )
    
    # Try Instaloader first
    try:
        print("Attempting Reel download via Instaloader...")
        file_path = download_insta_reel_via_instaloader(reel_url, download_dir, session_dir, auth_username, progress_callback)
        return file_path
    except Exception as insta_err:
        print(f"Instaloader download failed: {insta_err}. Falling back to yt-dlp...")
        
    # Fallback to yt-dlp
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
        'progress_hooks': [ytdl_hook],
        'quiet': True,
        'no_warnings': True,
    })
    opts.update(get_ydl_format_options(format_preset))
    opts = apply_proxy_to_ydl_opts(opts)
    
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(reel_url, download=True)
        filename = ydl.prepare_filename(info)
        base, _ = os.path.splitext(filename)
        if os.path.exists(filename):
            return filename
        for ext in ['.mp4', '.mkv', '.webm', '.mp3']:
            if os.path.exists(base + ext):
                return base + ext
        return filename

def get_shorts_by_hashtags(hashtags_str, sort_by):
    """
    Given a comma-separated string of hashtags, queries all of them,
    deduplicates the shorts, and sorts them according to the user's preference.
    """
    import concurrent.futures
    
    tags = [t.strip().lstrip('#') for t in hashtags_str.split(',') if t.strip()]
    if not tags:
        return []
        
    all_shorts = {}
    
    def fetch_tag(tag):
        url = f"https://www.youtube.com/hashtag/{tag}"
        ydl_opts = {
            'extract_flat': True,
            'playlistend': 50,
            'quiet': True,
            'no_warnings': True,
        }
        ydl_opts = apply_proxy_to_ydl_opts(ydl_opts)
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                entries = info.get('entries', [])
                results = []
                for entry in entries:
                    video_id = entry.get('id')
                    is_short = False
                    entry_url = entry.get('url', '')
                    if '/shorts/' in entry_url:
                        is_short = True
                    elif entry.get('duration') and entry.get('duration') <= 60:
                        is_short = True
                    
                    if is_short and video_id:
                        thumbnails = entry.get('thumbnails', [])
                        thumb = thumbnails[-1].get('url', '') if thumbnails else f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
                        
                        results.append({
                            'id': video_id,
                            'title': entry.get('title') or 'YouTube Short',
                            'views': entry.get('view_count') or 0,
                            'duration': entry.get('duration') or 0,
                            'uploader': entry.get('uploader') or 'Unknown',
                            'url': f"https://www.youtube.com/shorts/{video_id}",
                            'thumbnail': thumb
                        })
                return results
        except Exception as e:
            print(f"Error fetching hashtag #{tag}: {e}")
            return []

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(fetch_tag, tag): tag for tag in tags}
        for future in concurrent.futures.as_completed(futures):
            results = future.result()
            for item in results:
                video_id = item['id']
                if video_id not in all_shorts or item['views'] > all_shorts[video_id]['views']:
                    all_shorts[video_id] = item
                    
    shorts_list = list(all_shorts.values())
    
    if sort_by == "Views (High to Low)":
        shorts_list.sort(key=lambda x: x.get('views', 0), reverse=True)
    elif sort_by == "Views (Low to High)":
        shorts_list.sort(key=lambda x: x.get('views', 0))
    elif sort_by == "Title (A-Z)":
        shorts_list.sort(key=lambda x: x.get('title', '').lower())
    elif sort_by == "Duration (Short to Long)":
        shorts_list.sort(key=lambda x: x.get('duration', 0))
        
    return shorts_list[:20]

def get_youtube_video_info(video_url):
    """
    Fetches info for a regular YouTube video.
    """
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
    }
    ydl_opts = apply_proxy_to_ydl_opts(ydl_opts)
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=False)
        title = info.get('title') or 'YouTube Video'
        title = title.split('\n')[0].strip()
        if len(title) > 80:
            title = title[:80] + "..."
            
        thumbnails = info.get('thumbnails', [])
        thumb_url = info.get('thumbnail', '')
        if not thumb_url and thumbnails:
            thumb_url = thumbnails[-1].get('url', '')
            
        return {
            'id': info.get('id'),
            'title': title,
            'views': info.get('view_count', 0),
            'uploader': info.get('uploader') or 'Unknown',
            'duration': info.get('duration', 0),
            'thumbnail': thumb_url,
            'url': video_url
        }

def download_youtube_video(video_url, download_dir, progress_callback=None, format_preset="Best Quality (Video)"):
    """
    Downloads a regular YouTube video using a progress callback.
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

    opts = {
        'outtmpl': os.path.join(download_dir, '%(title)s.%(ext)s'),
        'progress_hooks': [ytdl_hook],
        'quiet': True,
        'no_warnings': True,
    }
    opts.update(get_ydl_format_options(format_preset))
    opts = apply_proxy_to_ydl_opts(opts)
    
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(video_url, download=True)
        filename = ydl.prepare_filename(info)
        base, _ = os.path.splitext(filename)
        if os.path.exists(filename):
            return filename
        for ext in ['.mp4', '.mkv', '.webm', '.mp3']:
            if os.path.exists(base + ext):
                return base + ext
        return filename

def load_cookies_to_instaloader(L):
    import sys
    import http.cookiejar
    
    app_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
    possible_paths = [
        os.path.join(app_dir, "cookies.txt"),
        os.path.join(os.path.expanduser("~"), "cookies.txt"),
        os.path.join(os.path.expanduser("~"), "Downloads", "cookies.txt"),
        os.path.join(os.path.expanduser("~"), ".yt_shorts_downloader_insta_cookies.txt")
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            try:
                cookie_jar = http.cookiejar.MozillaCookieJar(path)
                cookie_jar.load(ignore_discard=True, ignore_expires=True)
                for cookie in cookie_jar:
                    if "instagram.com" in cookie.domain:
                        L.context._session.cookies.set_cookie(cookie)
                print(f"Successfully loaded cookies into Instaloader from {path}")
                return True
            except Exception as e:
                print(f"Error loading cookies from {path}: {e}")
    return False


class SessionExpiredError(Exception):
    """Raised when the Instagram session is expired and re-login is needed."""
    pass


def instagram_web_login(username, password):
    """
    Login to Instagram via the web AJAX endpoint (same flow as the browser).
    Returns a requests.Session with valid cookies on success.
    Raises Exception with descriptive message on failure.
    """
    import requests
    import time
    import json
    
    session = requests.Session()
    proxy = get_configured_proxy()
    if proxy:
        session.proxies = {"http": proxy, "https": proxy}
        
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://www.instagram.com/',
    })
    
    # Step 1: Get CSRF token from homepage
    r1 = session.get("https://www.instagram.com/", timeout=15)
    csrf = session.cookies.get("csrftoken", "")
    if not csrf:
        match = re.search(r'"csrf_token":"([^"]+)"', r1.text)
        if match:
            csrf = match.group(1)
    if not csrf:
        raise Exception("Could not get CSRF token from Instagram. Please try again later.")
    
    # Step 2: Send login request
    login_data = {
        "username": username,
        "enc_password": f"#PWD_INSTAGRAM_BROWSER:0:{int(time.time())}:{password}",
        "queryParams": "{}",
        "optIntoOneTap": "false",
        "stopDeletionNonce": "",
        "trustedDeviceRecords": "{}",
    }
    login_headers = {
        'X-CSRFToken': csrf,
        'X-Requested-With': 'XMLHttpRequest',
        'X-IG-App-ID': '936619743392459',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Referer': 'https://www.instagram.com/accounts/login/',
    }
    
    r2 = session.post("https://www.instagram.com/accounts/login/ajax/",
                      data=login_data, headers=login_headers, timeout=15)
    
    try:
        resp = r2.json()
    except Exception:
        raise Exception(f"Instagram returned an unexpected response (HTTP {r2.status_code}). Please try again later.")
    
    if resp.get("authenticated"):
        print("Instagram web login succeeded!")
        return session
    elif resp.get("two_factor_required"):
        raise Exception("TWO_FACTOR_REQUIRED")
    elif resp.get("checkpoint_url"):
        raise Exception(
            f"Instagram requires a security checkpoint. Please open Instagram in your browser, "
            f"complete the checkpoint at {resp.get('checkpoint_url')}, then try again."
        )
    elif resp.get("error_type") == "UserInvalidCredentials":
        raise Exception("Incorrect password. Please check your password and try again.")
    else:
        msg = resp.get("message") or resp.get("error_type") or "Unknown error"
        raise Exception(f"Login failed: {msg}")


def save_instagram_session(session, username, session_dir):
    """Save a requests.Session's Instagram cookies to disk for reuse."""
    import json
    os.makedirs(session_dir, exist_ok=True)
    session_file = os.path.join(session_dir, f"insta_web_session_{username}.json")
    
    cookies_dict = {}
    for c in session.cookies:
        if "instagram.com" in c.domain:
            cookies_dict[c.name] = {
                "value": c.value,
                "domain": c.domain,
                "path": c.path,
            }
    
    with open(session_file, "w", encoding="utf-8") as f:
        json.dump(cookies_dict, f)
    print(f"Saved Instagram web session to {session_file}")


def load_instagram_session(username, session_dir):
    """
    Load a previously saved Instagram web session from disk.
    Returns a requests.Session with cookies set, or None if not found/invalid.
    """
    import json
    import requests
    
    session_file = os.path.join(session_dir, f"insta_web_session_{username}.json")
    if not os.path.exists(session_file):
        return None
    
    try:
        with open(session_file, "r", encoding="utf-8") as f:
            cookies_dict = json.load(f)
        
        if not cookies_dict.get("sessionid"):
            return None
        
        session = requests.Session()
        proxy = get_configured_proxy()
        if proxy:
            session.proxies = {"http": proxy, "https": proxy}
            
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
        })
        for name, info in cookies_dict.items():
            session.cookies.set(name, info["value"], domain=info["domain"], path=info["path"])
        
        print(f"Loaded Instagram web session for {username}")
        return session
    except Exception as e:
        print(f"Failed to load session: {e}")
        return None


def verify_instagram_session(session):
    """Check if an Instagram web session is still valid. Returns True/False."""
    try:
        r = session.get("https://www.instagram.com/accounts/edit/", 
                        headers={'X-IG-App-ID': '936619743392459'},
                        timeout=10, allow_redirects=False)
        # If it redirects to login, session is expired
        if r.status_code in (301, 302) and "login" in r.headers.get("Location", ""):
            return False
        return r.status_code == 200
    except Exception:
        return False


def get_instagram_user_id(session, username):
    """
    Get an Instagram user's numeric ID using multiple strategies.
    Requires an authenticated requests.Session.
    Returns (user_id, user_info_dict) on success.
    Raises SessionExpiredError if the session is invalid.
    Raises Exception if the user cannot be found.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
        'X-IG-App-ID': '936619743392459',
        'X-Requested-With': 'XMLHttpRequest',
        'Referer': 'https://www.instagram.com/',
    }
    csrf = session.cookies.get("csrftoken", "")
    if csrf:
        headers['X-CSRFToken'] = csrf
    
    # Strategy 1: web_profile_info API
    print(f"[Profile Lookup] Strategy 1: web_profile_info for '{username}'...")
    try:
        url = f"https://i.instagram.com/api/v1/users/web_profile_info/?username={username}"
        r = session.get(url, headers=headers, timeout=10)
        print(f"  Status: {r.status_code}")
        
        if r.status_code == 200:
            data = r.json()
            user = data.get("data", {}).get("user")
            if user and user.get("id"):
                uid = int(user["id"])
                print(f"  Found user ID: {uid}")
                return uid, user
        elif r.status_code in (401, 403):
            print("  Session appears expired (401/403)")
            raise SessionExpiredError("Instagram session expired. Please re-login.")
        elif r.status_code == 429:
            print("  Rate limited (429), trying next strategy...")
    except SessionExpiredError:
        raise
    except Exception as e:
        print(f"  web_profile_info failed: {e}")
    
    # Strategy 2: topsearch API
    print(f"[Profile Lookup] Strategy 2: topsearch for '{username}'...")
    try:
        search_url = f"https://www.instagram.com/web/search/topsearch/?query={username}&context=user"
        r2 = session.get(search_url, headers=headers, timeout=10)
        print(f"  Status: {r2.status_code}")
        
        if r2.status_code == 200:
            data2 = r2.json()
            for u in data2.get("users", []):
                user_node = u.get("user", {})
                if user_node.get("username", "").lower() == username.lower():
                    uid = int(user_node.get("pk") or user_node.get("id", 0))
                    if uid:
                        print(f"  Found exact match: ID={uid}")
                        return uid, user_node
            # If no exact match, try the first result
            if data2.get("users"):
                first = data2["users"][0].get("user", {})
                if first.get("username", "").lower() == username.lower():
                    uid = int(first.get("pk") or first.get("id", 0))
                    if uid:
                        print(f"  Found first match: ID={uid}")
                        return uid, first
        elif r2.status_code in (401, 403):
            raise SessionExpiredError("Instagram session expired. Please re-login.")
    except SessionExpiredError:
        raise
    except Exception as e:
        print(f"  topsearch failed: {e}")
    
    # Strategy 3: Scrape profile HTML page for user ID
    print(f"[Profile Lookup] Strategy 3: HTML scraping for '{username}'...")
    try:
        page_url = f"https://www.instagram.com/{username}/"
        r3 = session.get(page_url, headers={
            'User-Agent': headers['User-Agent'],
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }, timeout=10)
        print(f"  Page status: {r3.status_code}")
        
        if r3.status_code == 200:
            html = r3.text
            
            # Pattern: profilePage_USERID
            match = re.search(r'profilePage_([0-9]+)', html)
            if match:
                uid = int(match.group(1))
                print(f"  Found via profilePage pattern: {uid}")
                return uid, {"id": str(uid), "username": username}
            
            # Pattern: "user_id":"USERID"
            match = re.search(r'"user_id"\s*:\s*"([0-9]+)"', html)
            if match:
                uid = int(match.group(1))
                print(f"  Found via user_id pattern: {uid}")
                return uid, {"id": str(uid), "username": username}
            
            # Pattern: in script tags
            scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
            for script in scripts:
                if username.lower() in script.lower():
                    match = re.search(r'"id"\s*:\s*"([0-9]{5,})"', script)
                    if match:
                        uid = int(match.group(1))
                        print(f"  Found via script tag: {uid}")
                        return uid, {"id": str(uid), "username": username}
        elif r3.status_code in (401, 403):
            raise SessionExpiredError("Instagram session expired. Please re-login.")
    except SessionExpiredError:
        raise
    except Exception as e:
        print(f"  HTML scraping failed: {e}")
    
    raise Exception(
        f"Could not find Instagram profile '{username}'. "
        f"Please verify the username is correct and the account is public."
    )


def get_user_reels_via_api(session, user_id, username, max_count=12):
    """
    Fetch recent reels/video posts from a user using Instagram's API.
    Returns a list of reel dicts with id, title, views, duration, thumbnail, url.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
        'X-IG-App-ID': '936619743392459',
        'X-Requested-With': 'XMLHttpRequest',
        'Referer': f'https://www.instagram.com/{username}/',
    }
    csrf = session.cookies.get("csrftoken", "")
    if csrf:
        headers['X-CSRFToken'] = csrf
    
    reels_list = []
    
    # Strategy 1: Try clips (reels) endpoint
    print(f"[Reels] Fetching clips for user_id={user_id}...")
    try:
        clips_url = f"https://i.instagram.com/api/v1/clips/user/"
        clips_data = {
            "target_user_id": str(user_id),
            "page_size": str(max_count),
            "include_feed_video": "true",
        }
        r = session.post(clips_url, data=clips_data, headers=headers, timeout=15)
        print(f"  Clips endpoint status: {r.status_code}")
        
        if r.status_code == 200:
            data = r.json()
            items = data.get("items", [])
            for item in items[:max_count]:
                media = item.get("media", {})
                if media:
                    code = media.get("code", "")
                    caption_obj = media.get("caption")
                    caption = caption_obj.get("text", "Instagram Reel") if caption_obj else "Instagram Reel"
                    caption = caption.split('\n')[0].strip()
                    if len(caption) > 80:
                        caption = caption[:80] + "..."
                    
                    thumb = ""
                    candidates = media.get("image_versions2", {}).get("candidates", [])
                    if candidates:
                        thumb = candidates[0].get("url", "")
                    
                    reels_list.append({
                        'id': code,
                        'title': caption,
                        'views': media.get("play_count") or media.get("view_count") or 0,
                        'duration': int(media.get("video_duration", 0)),
                        'thumbnail': thumb,
                        'url': f"https://www.instagram.com/reel/{code}/"
                    })
            
            if reels_list:
                print(f"  Got {len(reels_list)} reels from clips endpoint.")
                return reels_list
        elif r.status_code in (401, 403):
            raise SessionExpiredError("Instagram session expired. Please re-login.")
    except SessionExpiredError:
        raise
    except Exception as e:
        print(f"  Clips endpoint failed: {e}")
    
    # Strategy 2: Fall back to user feed (timeline media)
    print(f"[Reels] Falling back to user feed endpoint...")
    try:
        feed_url = f"https://i.instagram.com/api/v1/feed/user/{user_id}/?count={max_count * 2}"
        r2 = session.get(feed_url, headers=headers, timeout=15)
        print(f"  Feed endpoint status: {r2.status_code}")
        
        if r2.status_code == 200:
            data2 = r2.json()
            items = data2.get("items", [])
            for item in items:
                if item.get("media_type") == 2 or item.get("video_versions"):  # video
                    code = item.get("code", "")
                    caption_obj = item.get("caption")
                    caption = caption_obj.get("text", "Instagram Video") if caption_obj else "Instagram Video"
                    caption = caption.split('\n')[0].strip()
                    if len(caption) > 80:
                        caption = caption[:80] + "..."
                    
                    thumb = ""
                    candidates = item.get("image_versions2", {}).get("candidates", [])
                    if candidates:
                        thumb = candidates[0].get("url", "")
                    
                    reels_list.append({
                        'id': code,
                        'title': caption,
                        'views': item.get("play_count") or item.get("view_count") or 0,
                        'duration': int(item.get("video_duration", 0)),
                        'thumbnail': thumb,
                        'url': f"https://www.instagram.com/reel/{code}/"
                    })
                    
                    if len(reels_list) >= max_count:
                        break
            
            if reels_list:
                print(f"  Got {len(reels_list)} videos from feed endpoint.")
                return reels_list
        elif r2.status_code in (401, 403):
            raise SessionExpiredError("Instagram session expired. Please re-login.")
    except SessionExpiredError:
        raise
    except Exception as e:
        print(f"  Feed endpoint failed: {e}")
    
    return reels_list


def get_insta_profile_reels(target_username, session_dir, auth_username=None, auth_password=None):
    """
    Scrapes the 12 most recent Reels/videos from an Instagram profile.
    Uses a multi-strategy approach:
      1. Direct Instagram web session (web_profile_info + clips API)
      2. Instaloader with session as fallback
    
    Raises SessionExpiredError if re-login is needed.
    """
    import json
    
    # --- Resolve the session_dir for web sessions ---
    web_session_dir = session_dir or os.path.join(
        os.environ.get("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local")),
        "Instaloader"
    )
    
    # --- Step 1: Try to get or create a web session ---
    session = None
    
    # Try loading saved web session
    if auth_username:
        session = load_instagram_session(auth_username, web_session_dir)
    
    # If no saved session, try to create one if we have credentials
    if session is None and auth_username and auth_password:
        print("[Session] No saved session. Creating new one with credentials...")
        try:
            session = instagram_web_login(auth_username, auth_password)
            save_instagram_session(session, auth_username, web_session_dir)
        except Exception as e:
            err_msg = str(e)
            if "TWO_FACTOR_REQUIRED" in err_msg:
                raise
            print(f"[Session] Web login failed: {e}")
    
    # If we have a session, try the direct API approach
    if session:
        try:
            user_id, user_info = get_instagram_user_id(session, target_username)
            reels = get_user_reels_via_api(session, user_id, target_username, max_count=50)
            if reels:
                # Filter out downloaded reels
                history = load_history()
                downloaded_ids = history.get("instagram", {}).get(target_username.lower().strip(), [])
                filtered_reels = [r for r in reels if r['id'] not in downloaded_ids]
                
                # Sort by views descending
                filtered_reels.sort(key=lambda x: x['views'], reverse=True)
                
                # Return top 10
                return filtered_reels[:10]
            else:
                print("[Reels] Direct API returned no reels, trying instaloader fallback...")
        except SessionExpiredError:
            # Delete stale session file
            if auth_username:
                stale = os.path.join(web_session_dir, f"insta_web_session_{auth_username}.json")
                if os.path.exists(stale):
                    os.remove(stale)
            raise
        except Exception as e:
            print(f"[Direct API] Failed: {e}. Trying instaloader fallback...")
    
    # --- Step 2: Instaloader fallback ---
    print("[Fallback] Trying instaloader...")
    try:
        L = instaloader.Instaloader(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'
        )
        proxy = get_configured_proxy()
        if proxy:
            L.context._session.proxies = {"http": proxy, "https": proxy}
        
        # Load instaloader session
        if auth_username and session_dir:
            session_file = os.path.join(session_dir, f"session-{auth_username}")
            if os.path.exists(session_file):
                try:
                    L.load_session_from_file(auth_username, filename=session_file)
                except Exception as e:
                    print(f"[Instaloader] Error loading session: {e}")
        
        # If we got a user_id from the direct API, use from_id
        if session and 'user_id' in dir():
            try:
                profile = instaloader.Profile.from_id(L.context, user_id)
            except Exception:
                profile = None
        else:
            profile = None
        
        # Try from_username as last resort
        if profile is None:
            try:
                profile = instaloader.Profile.from_username(L.context, target_username)
            except Exception as e:
                # If everything failed and we have no session at all, ask for login
                if session is None:
                    raise SessionExpiredError(
                        "No active Instagram session. Please enter your Instagram credentials "
                        "in Login Settings to enable profile scraping."
                    )
                raise Exception(
                    f"Could not find profile '{target_username}'. "
                    f"Please verify the username is correct. Error: {e}"
                )
        
        # Fetch posts/reels
        posts = profile.get_posts()
        reels_list = []
        count = 0
        for post in posts:
            if post.is_video:
                caption = post.caption or "Instagram Reel"
                caption = caption.split('\n')[0].strip()
                if len(caption) > 80:
                    caption = caption[:80] + "..."
                
                reels_list.append({
                    'id': post.shortcode,
                    'title': caption,
                    'views': post.video_view_count or 0,
                    'duration': int(post.video_duration or 0),
                    'thumbnail': post.url,
                    'url': f"https://www.instagram.com/reel/{post.shortcode}/"
                })
                count += 1
                if count >= 50:
                    break
                    
        # Filter and sort fallback reels
        history = load_history()
        downloaded_ids = history.get("instagram", {}).get(target_username.lower().strip(), [])
        filtered_reels = [r for r in reels_list if r['id'] not in downloaded_ids]
        filtered_reels.sort(key=lambda x: x['views'], reverse=True)
        return filtered_reels[:10]
    except SessionExpiredError:
        raise
    except Exception as e:
        if session is None and not auth_username:
            raise SessionExpiredError(
                "No Instagram credentials configured. Please enter your Instagram "
                "username and password in Login Settings to use profile scraping."
            )
        raise Exception(f"Failed to fetch profile reels: {e}")


