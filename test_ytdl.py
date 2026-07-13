import yt_dlp
import json

def test_extract():
    url = "https://www.youtube.com/@MrBeast/shorts"
    ydl_opts = {
        'extract_flat': True,
        'playlistend': 50, # get up to 50 to see
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            print("Successfully extracted channel shorts playlist.")
            print(f"Playlist Title: {info.get('title')}")
            entries = info.get('entries', [])
            print(f"Number of entries found: {len(entries)}")
            
            if entries:
                print("First entry sample:")
                print(json.dumps(entries[0], indent=2))
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    test_extract()
