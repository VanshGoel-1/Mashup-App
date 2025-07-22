# Audio Mashup Generator

#### Description:

The Audio Mashup Generator is a web-based application that automatically creates personalized audio mashups from YouTube videos of any artist or singer. Users simply enter an artist's name, specify how many videos they want included, set the duration for each song segment, and provide their email address. The application then downloads videos, extracts audio segments, merges them into a single mashup file, and emails the result as a ZIP file to the user.

This project combines web scraping, audio processing, and email automation to create a seamless user experience for generating custom music mashups. The application is built using Flask for the web framework and leverages several powerful Python libraries for media processing and web scraping.

## Project Architecture and Files

### Core Application Files

**`project.py`** - This is the main application file containing the Flask web application and all core functionality. The file is structured with multiple well-defined functions that handle different aspects of the mashup generation process:

- `valid_input()` - Performs input validation, makingsure that user inputs are safe and within range
- `download_video()` - Uses yt-dlp to search and download YouTube videos with built-in retry logic for reliability
- `convert()` - Converts the content of downloaded videos to audio format
- `convert_single_video_to_audio()` - Handles individual video-to-audio conversion using MoviePy
- `cut_audio()` - Extracts specific time segments from audio files using PyDub
- `mashup()` - Merges multiple audio segments into a single cohesive mashup
- `create_zip()` - Packages the final audio file into a ZIP archive for easy distribution
- `send_email()` - Sends the completed mashup to users via email using Flask-Mail
- `cleanup()` - Manages temporary file cleanup to prevent storage bloat
- `main()` - Entry point function that initializes the Flask application

The Flask routes handle the web interface, with the main route `/generate_mashup` processing POST requests and coordinating the entire mashup generation pipeline.

**`form.html`** - Located in the `templates/` directory, this HTML template provides the user interface for the application. It features a responsive Bootstrap-based design with real-time form validation, progress indicators, and error handling. The form includes input fields for artist name, number of videos, segment duration, and email address. JavaScript enhances the user experience with loading states, progress bars, and AJAX form submission.

**`test_project.py`** - Contains comprehensive unit tests for all major functions in the project. Each function is tested with various scenarios including success cases, failure cases, and edge cases. The tests use Python's unittest framework with extensive mocking to isolate functions and test them independently.

**`requirements.txt`** - Lists all Python dependencies required to run the project, ensuring consistent environments across different deployments.

## Design Decisions and Technical Choices

### Modular Function Design
I chose to break the original monolithic code into multiple focused functions for several key reasons. First, this approach significantly improves testability - each function can be unit tested independently with clear inputs and outputs. Second, it enhances maintainability by creating clear separation of concerns where each function has a single responsibility. Third, it improves error handling by allowing specific error management for each operation phase.

### Retry Mechanism for Downloads
The video download function includes a retry mechanism because YouTube downloads can be unreliable due to network issues, rate limiting, or temporary server problems. The retry logic with exponential backoff ensures better success rates while being respectful of the service.

### Input Validation Strategy
I implemented comprehensive input validation both on the client side (HTML5 and JavaScript) and server side (Python function). This dual-layer approach provides immediate user feedback while maintaining security and data integrity. The validation includes checks for email format, numeric ranges, and string lengths to prevent both user errors and potential security issues.

### Audio Processing Pipeline
The audio processing follows a clear pipeline: download → convert → cut → merge → package → email. This linear approach makes the process predictable and easier to debug. Each step includes error handling to gracefully handle failures at any point in the pipeline.

### Resource Management
The application includes automatic cleanup of temporary files to prevent storage accumulation. This is crucial for a web application that processes media files, as these can quickly consume significant disk space.

### Email Integration
Rather than requiring users to download files directly, the email delivery system provides a better user experience. Users can start the process and continue with other tasks while the mashup generates in the background. The ZIP packaging ensures the audio file is compressed and easy to handle.

### Web Interface Design
The Bootstrap-based interface provides a professional, responsive design that works across devices. The real-time validation and progress indicators keep users informed about the process status, which is important given that mashup generation can take several minutes.

This architecture creates a robust, user-friendly application that handles the complex process of creating audio mashups while providing a smooth user experience and maintainable codebase.
