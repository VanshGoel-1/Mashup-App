import os
import yt_dlp
import time
from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.audio.io.AudioFileClip import AudioFileClip
from moviepy.audio.AudioClip import concatenate_audioclips
from moviepy.audio.AudioClip import AudioArrayClip
import numpy as np
import zipfile
from flask import Flask, request, render_template, jsonify
from flask_mail import Mail, Message
import ffmpeg
import soundfile as sf
import tempfile
from dotenv import load_dotenv
from flask_cors import CORS

load_dotenv()

app = Flask(__name__)

# Advanced CORS Configuration
# allowing all origins for now, but configured to be easily restricted
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')
mail = Mail(app)

def valid_input(singer, number_of_videos, duration, email):
    if not singer or not number_of_videos or not email:
        return False, "Please provide singer name, number of videos, and email.", None
    if not singer.strip():
        return False, "Singer name cannot be empty.", None
    if '@' not in email or '.' not in email:
        return False, "Please provide a valid email address.", None

    try:
        num_videos = int(number_of_videos)
        dur = int(duration)

        if num_videos <= 0 or num_videos > 20:
            return False, "Number of videos must be between 1 and 20.", None
        if dur <= 0 or dur > 120:
            return False, "Duration must be between 1 and 120 seconds.", None
        return True, None, (num_videos, dur)

    except Exception as e:
        print(f"Error: {e}")
        return None

def download_video(singer, number_of_videos, download_path, max_retries=3, retry_delay=5):
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(download_path, '%(title)s.%(ext)s'),
        'noplaylist': True,
        'quiet': True,
    }

    search_url = f"ytsearch{number_of_videos}:{singer}"
    for attempt in range(max_retries):
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                result = ydl.extract_info(search_url, download=True)
                # Check for 'entries' in result (playlist) or result itself (single video)
                if 'entries' in result:
                     num_downloaded = len(result['entries'])
                else:
                     num_downloaded = 1

                if num_downloaded > 0:
                    return num_downloaded

        except Exception as e:
            print(f"Download attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)

    return 0

def convert(download_path, duration, start_time_seconds=20):
    audio_file_paths = []
    # Since we download audio directly, we might not need heavy conversion,
    # but we still need to cut it to the specific duration.
    # yt-dlp usually downloads webm or m4a for audio best.
    
    for file_name in os.listdir(download_path):
        file_path = os.path.join(download_path, file_name)
        # Process any audio/video file that moviepy/ffmpeg can handle
        if os.path.isfile(file_path):
            # We will process all files in the temp dir as candidates
            try:
                # We need to cut the audio. 
                # Optimization: Use ffmpeg directly to cut without full re-encoding if possible, 
                # but for consistency with previous logic (and to ensure valid mp3 output for merging),
                # we'll use a reliable cut function.
                output_cut_path = os.path.join(download_path, f"cut_{file_name}.mp3")
                if cut_audio(file_path, output_cut_path, start_time_seconds, duration):
                     audio_file_paths.append(output_cut_path)
            except Exception as e:
                print(f"Error processing {file_name}: {e}")
                
    return audio_file_paths

def cut_audio(input_file_path, output_file_path, start_time_seconds, duration_seconds):
    try:
        (
            ffmpeg
            .input(input_file_path, ss=start_time_seconds, t=duration_seconds)
            .output(output_file_path, format='mp3', acodec='libmp3lame', q=4) # q=4 is good quality
            .overwrite_output()
            .run(quiet=True)
        )
        return True
    except Exception as e:
        print(f"Error cutting audio with ffmpeg for {input_file_path}: {e}")
        return False

def mashup(audio_file_paths, output_path):
    if not audio_file_paths:
        print("No audio files to merge")
        return None
    try:
        audio_clips = []
        for file_path in audio_file_paths:
            try:
                # Use AudioFileClip for robust merging
                audio_clip = AudioFileClip(file_path)
                audio_clips.append(audio_clip)
            except Exception as e:
                 print(f"Error loading clip {file_path}: {e}")

        if not audio_clips:
            return None
            
        final_audio = concatenate_audioclips(audio_clips)
        final_audio.write_audiofile(output_path, logger=None)
        
        for clip in audio_clips:
            clip.close()
        final_audio.close()
        
        return output_path
    except Exception as e:
        print(f"Error creating audio mashup: {e}")
        return None

def create_zip(file_path, zip_name):
    try:
        with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(file_path, os.path.basename(file_path))
        return True
    except Exception as e:
        print(f"Error creating ZIP file: {e}")
        return False

def send_email(email, zip_path):
    try:
        if not os.path.exists(zip_path):
            return False, "File not found"
        msg = Message(subject='Your Mashup Audio', recipients=[email])
        msg.body = 'Attached is the zip file containing your mashup audio.'
        with open(zip_path, 'rb') as f:
            msg.attach('merged_audio.zip', 'application/zip', f.read())
        mail.send(msg)
        return True, None
    except Exception as e:
        print(f"Error sending email to {email}: {e}")
        return False, str(e)

@app.route('/')
def index():
    return render_template('form.html')

@app.route('/generate_mashup', methods=['POST'])
def generate_mashup():
    singer = request.form.get('singer', '').strip()
    number_of_videos = request.form.get('number_of_videos')
    duration = request.form.get('duration', '10')
    email = request.form.get('email', '').strip()
    
    is_valid, error_message, parsed_values = valid_input(singer, number_of_videos, duration, email)
    if not is_valid:
        return jsonify({"error": error_message}), 400
    
    num_videos, dur = parsed_values
    
    # Create a temporary directory for this request
    temp_dir = tempfile.mkdtemp()
    try:
        print(f"Created temp dir: {temp_dir}")
        print(f"Attempting to download {num_videos} videos for {singer}")
        
        # Download Phase
        num_downloaded = download_video(singer, num_videos, temp_dir)
        if num_downloaded == 0:
             return jsonify({"error": "Failed to download videos."}), 500
             
        # Conversion/Cutting Phase
        # We re-use temp_dir for finding files
        audio_file_paths = convert(temp_dir, dur)
        if not audio_file_paths:
            return jsonify({"error": "Failed to process audio files."}), 500
            
        # Mashup Phase
        merged_output_path = os.path.join(temp_dir, "merged_audio.mp3")
        if not mashup(audio_file_paths, merged_output_path):
             return jsonify({"error": "Failed to create mashup."}), 500
             
        # Zip Phase
        zip_output_path = os.path.join(temp_dir, "merged_audio.zip")
        if not create_zip(merged_output_path, zip_output_path):
             return jsonify({"error": "Failed to create zip."}), 500
             
        # Custom File Size Check (Gmail limit is 25MB, we set 24MB for safety)
        file_size = os.path.getsize(zip_output_path)
        if file_size > 24 * 1024 * 1024:
             return jsonify({"error": f"Generated file is too large ({file_size / (1024*1024):.2f}MB). Email limit is 25MB. Try fewer videos or shorter duration."}), 500

        # Email Phase
        success, email_error = send_email(email, zip_output_path)
        if not success:
             return jsonify({"error": f"Failed to send email: {email_error}"}), 500
             
        return jsonify({"message": "Mashup generated and emailed successfully!"}), 200

    except Exception as e:

        print(f"Unexpected error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        # Cleanup everything in the temp dir
        try:
            for root, dirs, files in os.walk(temp_dir, topdown=False):
                for name in files:
                    os.remove(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
            os.rmdir(temp_dir)
            print(f"Cleaned up temp dir: {temp_dir}")
        except Exception as cleanup_error:
            print(f"Error cleaning up temp dir {temp_dir}: {cleanup_error}")

def main():
    os.makedirs('static', exist_ok=True)
    app.run(debug=True)

if __name__ == "__main__":
    main()
