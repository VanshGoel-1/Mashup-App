# Audio Mashup Generator

## Description

The Audio Mashup Generator is a web-based application that automatically creates personalized audio mashups from YouTube videos. Users simply enter an artist's name, specify the number of videos, duration, and their email. The application parses the request, downloads the audio, merges it, and emails the result as a ZIP file.

## Features

- **Smart Audio Processing**: Downloads audio directly using `yt-dlp` for efficiency.
- **Privacy Focused**: Uses environment variables for sensitive credentials.
- **Secure**: Implements CORS policies and security headers.
- **Reliable**: Uses isolated temporary directories for processing to prevent file conflicts.
- **Email Delivery**: Automatically emails the final ZIP file to the user.

## Setup & Installation

1.  **Clone the repository**
2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
    *Note: Requires `ffmpeg` installed on your system.*

3.  **Environment Configuration**:
    Create a `.env` file in the root directory:
    ```env
    MAIL_USERNAME=your_email@gmail.com
    MAIL_PASSWORD=your_app_password
    MAIL_DEFAULT_SENDER=your_email@gmail.com
    ```

4.  **Run the Application**:
    ```bash
    python project.py
    ```

## Architecture

- **Backend**: Flask
- **Downloading**: yt-dlp (Audio-only mode)
- **Processing**: MoviePy & FFmpeg (Direct cutting and merging)
- **Email**: Flask-Mail

## API Endpoints

- `GET /`: Renders the submission form.
- `POST /generate_mashup`: Accepts `singer`, `number_of_videos`, `duration`, `email`. Returns JSON status.
