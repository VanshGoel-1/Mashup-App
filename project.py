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

app = Flask(__name__)

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'goelvansh1001@gmail.com'
app.config['MAIL_PASSWORD'] = 'cvrg742'
app.config['MAIL_DEFAULT_SENDER'] = 'vgoel_be22@thapar.edu'
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

def download_video(singer, number_of_videos, max_retries=3, retry_delay=5):
    download_path = os.getcwd()
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': os.path.join(download_path, '%(title)s.%(ext)s'),
        'noplaylist': True,
        'merge_output_format': 'mp4',
        'quiet': True,
    }

    search_url = f"ytsearch{number_of_videos}:{singer}"
    for attempt in range(max_retries):
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                result = ydl.extract_info(search_url, download=True)
                num_downloaded = len(result['entries']) if 'entries' in result else 0
                if num_downloaded > 0:
                    return num_downloaded

        except Exception as e:
            print(f"Download attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)

    return 0

def convert(download_path, duration, start_time_seconds=20):
    audio_file_paths = []
    for file_name in os.listdir(download_path):
        if file_name.endswith('.mp4'):
            video_file_path = os.path.join(download_path, file_name)
            audio_file_path = convert_audio(video_file_path)
            if audio_file_path and os.path.exists(audio_file_path):
                success = cut_audio(audio_file_path, start_time_seconds, duration)
                if success:
                    audio_file_paths.append(audio_file_path)
                else:
                    if os.path.exists(audio_file_path):
                        os.remove(audio_file_path)
    return audio_file_paths

def convert_audio(video_file_path):
    audio_file_path = os.path.splitext(video_file_path)[0] + ".mp3"

    try:
        video_clip = VideoFileClip(video_file_path)
        audio_clip = video_clip.audio
        audio_clip.write_audiofile(audio_file_path, logger=None)
        audio_clip.close()
        video_clip.close()

        if os.path.exists(video_file_path):
            os.remove(video_file_path)
        return audio_file_path
    except Exception as e:
        print(f"Error converting {video_file_path} to audio: {e}")
        return None

def cut_audio(audio_file_path, start_time_seconds, duration_seconds):
    try:
        temp_output = tempfile.mktemp(suffix=".mp3")
        (
            ffmpeg
            .input(audio_file_path, ss=start_time_seconds, t=duration_seconds)
            .output(temp_output, format='mp3')
            .overwrite_output()
            .run(quiet=True)
        )
        temp_wav = tempfile.mktemp(suffix=".wav")
        (
            ffmpeg
            .input(temp_output)
            .output(temp_wav, format='wav')
            .overwrite_output()
            .run(quiet=True)
        )
        data, samplerate = sf.read(temp_wav)
        os.remove(temp_wav)
        if data.size == 0:
            print(f"Extracted audio has no data: {audio_file_path}")
            os.remove(temp_output)
            return False
        os.replace(temp_output, audio_file_path)
        print(f"Audio trimmed and saved: {audio_file_path}")
        return True
    except Exception as e:
        print(f"Error cutting audio with ffmpeg: {e}")
        return False

def mashup(audio_file_paths, output_path='static/merged_audio.mp3'):
    if not audio_file_paths:
        print("No audio files to merge")
        return None
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    try:
        audio_clips = []
        for file_path in audio_file_paths:
            if os.path.exists(file_path):
                try:
                    audio_clip = AudioFileClip(file_path)
                    audio_clips.append(audio_clip)
                    print(f"Loaded audio file: {file_path}")
                except Exception as e:
                    print(f"Error loading file {file_path}: {e}")
        if not audio_clips:
            print("No audio clips loaded successfully")
            return None
        final_audio = concatenate_audioclips(audio_clips)
        final_audio.write_audiofile(output_path, logger=None)
        print(f"Merged audio file created at: {output_path}")
        for clip in audio_clips:
            clip.close()
        final_audio.close()
        for file_path in audio_file_paths:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    print(f"Removed file: {file_path}")
                except Exception as e:
                    print(f"Error removing file {file_path}: {e}")
        return output_path
    except Exception as e:
        print(f"Error creating audio mashup: {e}")
        for clip in audio_clips:
            try:
                clip.close()
            except:
                pass
        return None

def create_zip(file_path, zip_name='static/merged_audio.zip'):
    try:
        os.makedirs(os.path.dirname(zip_name), exist_ok=True)
        with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(file_path, os.path.basename(file_path))
        print(f"Zipped file created at: {zip_name}")
        return True
    except Exception as e:
        print(f"Error creating ZIP file: {e}")
        return False

def send_email(email, zip_path):
    try:
        if not os.path.exists(zip_path):
            print(f"ZIP file does not exist: {zip_path}")
            return False
        msg = Message(subject='Your Mashup Audio', recipients=[email])
        msg.body = 'Attached is the zip file containing your mashup audio.'
        with open(zip_path, 'rb') as f:
            msg.attach('merged_audio.zip', 'application/zip', f.read())
        mail.send(msg)
        print(f"Email sent successfully to {email}")
        return True
    except Exception as e:
        print(f"Error sending email to {email}: {e}")
        return False

def cleanup(*file_paths):
    for file_path in file_paths:
        try:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
                print(f"Cleaned up file: {file_path}")
        except Exception as e:
            print(f"Error cleaning up file {file_path}: {e}")

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
    try:
        print(f"Attempting to download {num_videos} videos for {singer}")
        num_downloaded = download_video(singer, num_videos)
        if num_downloaded == 0:
            return jsonify({"error": "Failed to download any videos. Please try a different singer."}), 500
        print(f"Successfully downloaded {num_downloaded} videos")
        download_path = os.getcwd()
        audio_file_paths = convert(download_path, dur)
        if not audio_file_paths:
            return jsonify({"error": "Failed to process any audio files."}), 500
        print(f"Processed {len(audio_file_paths)} audio files")
        merged_audio_path = mashup(audio_file_paths)
        if not merged_audio_path or not os.path.exists(merged_audio_path):
            return jsonify({"error": "Failed to create audio mashup."}), 500
        zip_path = 'static/merged_audio.zip'
        if not create_zip(merged_audio_path, zip_path):
            cleanup(merged_audio_path)
            return jsonify({"error": "Failed to create ZIP package."}), 500
        if not send_email(email, zip_path):
            cleanup(merged_audio_path, zip_path)
            return jsonify({"error": "Failed to send email. Please check your email address."}), 500
        cleanup(merged_audio_path, zip_path)
        return jsonify({"message": "Mashup generated and emailed successfully!"}), 200
    except Exception as e:
        print(f"Unexpected error in generate_mashup: {e}")
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500

def main():
    os.makedirs('static', exist_ok=True)
    app.run(debug=True)

if __name__ == "__main__":
    main()
