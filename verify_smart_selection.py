import os
import shutil
import tempfile
from project import download_video

def test_smart_selection():
    singer = "Arijit Singh"
    num_videos = 3
    temp_dir = tempfile.mkdtemp()
    
    print(f"Testing Smart Selection for: {singer}")
    print(f"Target: Top {num_videos} videos from Original Artist (or best match)")
    print("-" * 50)
    
    try:
        # We call download_video. 
        # Note: This WILL attempt to download, but we can verify the logs for selection.
        # to save time/bandwidth in a real test you might mock yt_dlp, 
        # but here we want to see if the real logic works with the real API.
        count = download_video(singer, num_videos, temp_dir)
        
        print("-" * 50)
        print(f"Downloaded {count} videos.")
        print("Files in temp dir:")
        for f in os.listdir(temp_dir):
            print(f" - {f}")
            
    except Exception as e:
        print(f"Verification Failed: {e}")
    finally:
        shutil.rmtree(temp_dir)
        print("-" * 50)
        print("Cleaned up temp dir.")

if __name__ == "__main__":
    test_smart_selection()
