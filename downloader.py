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

def download_insta_reel(reel_url, download_dir, ydl_opts=None, progress_callback=None, format_preset="Best Quality (Video)"):
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
        'progress_hooks': [ytdl_hook],
        'quiet': True,
        'no_warnings': True,
    })
    opts.update(get_ydl_format_options(format_preset))
    
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

def get_insta_profile_reels(target_username, session_dir, auth_username=None):
    """
    Scrapes the 12 most recent Reels/videos from an Instagram profile.
    Uses saved login session if available.
    """
    import instaloader
    L = instaloader.Instaloader(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    if auth_username and session_dir:
        session_file = os.path.join(session_dir, f"session-{auth_username}")
        if os.path.exists(session_file):
            try:
                L.load_session_from_file(auth_username, filename=session_file)
            except Exception as e:
                print(f"Error loading session in profile scraper: {e}")
                
    try:
        profile = instaloader.Profile.from_username(L.context, target_username)
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
                if count >= 12:
                    break
        return reels_list
    except Exception as e:
        raise Exception(f"Failed to load profile details: {e}")

