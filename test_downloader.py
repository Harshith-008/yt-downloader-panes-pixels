import downloader
import os

def test_downloader():
    channel = "https://www.youtube.com/@MrBeast"
    print(f"Testing channel link normalization: {downloader.clean_channel_url(channel)}")
    
    def prog(msg, pct):
        print(f"Progress: {msg} ({pct*100:.1f}%)")
        
    print("\nFetching top 10 shorts...")
    shorts = downloader.get_top_shorts(channel, progress_callback=prog, limit=50)
    
    print("\nTop 10 Shorts found:")
    for idx, s in enumerate(shorts, 1):
        print(f"{idx}. Title: {s['title']}")
        print(f"   Views: {s['views']:,}")
        print(f"   URL: {s['url']}")
        print(f"   Thumbnail: {s['thumbnail']}")
        print("-" * 40)

if __name__ == "__main__":
    test_downloader()
