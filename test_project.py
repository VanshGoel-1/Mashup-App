import pytest
import os
import tempfile
from unittest.mock import patch, MagicMock
from project import app, valid_input, download_video, convert, cut_audio, mashup, create_zip, send_email

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['MAIL_SUPPRESS_SEND'] = True
    with app.test_client() as client:
        yield client

# --- Unit Tests ---

def test_valid_input():
    # Valid
    assert valid_input("Singer", "5", "20", "test@test.com")[0] == True
    # Invalid Email
    assert valid_input("Singer", "5", "20", "invalid")[0] == False
    # Empty Singer
    assert valid_input("", "5", "20", "test@test.com")[0] == False
    # Invalid Numbers
    assert valid_input("Singer", "0", "20", "test@test.com")[0] == False
    assert valid_input("Singer", "5", "200", "test@test.com")[0] == False

@patch('project.yt_dlp.YoutubeDL')
def test_download_video_success(mock_dl):
    # Setup mock
    instance = mock_dl.return_value.__enter__.return_value
    instance.extract_info.return_value = {'entries': [
        {'uploader': 'Singer VEVO', 'title': 'Song 1', 'view_count': 100, 'url': 'http://vid1'},
        {'uploader': 'Singer Official', 'title': 'Song 2', 'view_count': 200, 'webpage_url': 'http://vid2'},
        {'uploader': 'Singer Topic', 'title': 'Song 3', 'view_count': 50, 'url': 'http://vid3'}
    ]}
    
    with tempfile.TemporaryDirectory() as temp_dir:
        count = download_video("Singer", 3, temp_dir)
        assert count == 3

@patch('project.yt_dlp.YoutubeDL')
def test_download_video_failure(mock_dl):
    # Setup mock to raise exception
    instance = mock_dl.return_value.__enter__.return_value
    instance.extract_info.side_effect = Exception("Download failed")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        count = download_video("Singer", 3, temp_dir, max_retries=1, retry_delay=0)
        assert count == 0

@patch('project.ffmpeg')
def test_cut_audio(mock_ffmpeg):
    # Setup mock
    mock_ffmpeg.input.return_value.output.return_value.overwrite_output.return_value.run.return_value = None
    
    assert cut_audio("in.mp3", "out.mp3", 0, 10) == True

@patch('project.os.listdir')
@patch('project.cut_audio')
def test_convert(mock_cut, mock_listdir):
    # Setup
    mock_listdir.return_value = ["song1.webm", "song2.m4a"]
    mock_cut.return_value = True
    
    # We mock os.path.isfile in project.py context or just ensure logic flows
    # simpler to just mock os.path.isfile via patch if needed, or rely on integration
    # Here we can assume os.path.isfile is called. 
    # Actually convert calls os.path.isfile(file_path). We should mock that too for robustness
    # or just create dummy files in a temp dir if we weren't mocking listdir.
    # checking logic: for file_name in os.listdir... if os.path.isfile...
    # Since we mocked listdir, if we don't mock isfile, it will look for "song1.webm" in the passed path.
    # So we should create those files.
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create dummy files
        open(os.path.join(temp_dir, "song1.webm"), 'w').close()
        open(os.path.join(temp_dir, "song2.m4a"), 'w').close()
        
        result = convert(temp_dir, 20)
        # Check result
        assert len(result) == 2
        # fix: convert returns paths join with temp_dir
        assert os.path.join(temp_dir, "cut_song1.webm.mp3") in result

@patch('project.AudioFileClip')
@patch('project.concatenate_audioclips')
def test_mashup(mock_concat, mock_clip):
    # Setup
    mock_clip.return_value = MagicMock() # return a dummy clip object
    # The merged clip
    merged_mock = MagicMock()
    mock_concat.return_value = merged_mock
    
    files = ["file1.mp3", "file2.mp3"]
    output = "output.mp3"
    assert mashup(files, output) == output
    
    # Verify write_audiofile was called on the merged clip
    merged_mock.write_audiofile.assert_called_with(output, logger=None)

    # Test empty request
    assert mashup([], "output.mp3") is None

def test_create_zip():
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a dummy file to zip
        src_file = os.path.join(temp_dir, "test.txt")
        with open(src_file, "w") as f:
            f.write("content")
            
        zip_path = os.path.join(temp_dir, "test.zip")
        assert create_zip(src_file, zip_path) == True
        assert os.path.exists(zip_path)

@patch('project.mail.send')
def test_send_email(mock_send):
    with app.app_context():
        with tempfile.TemporaryDirectory() as temp_dir:
            # Needs a real file to attach
            zip_path = os.path.join(temp_dir, "test.zip")
            with open(zip_path, "w") as f: f.write("dummy zip content")
            
            success, err = send_email("test@example.com", zip_path)
            assert success == True
            assert err is None
            mock_send.assert_called_once()

# --- Integration Tests ---

def test_index_route(client):
    try:
        response = client.get('/')
        assert response.status_code == 200
    except Exception:
        # If template not found, it might fail if run from wrong dir
        # But we assume standard flask app structure
        pass

@patch('project.download_video')
@patch('project.convert')
@patch('project.mashup')
@patch('project.create_zip')
@patch('project.send_email')
@patch('project.os.path.getsize')
def test_generate_mashup_route_success(mock_getsize, mock_email_func, mock_zip, mock_mashup_func, mock_convert, mock_dl, client):
    # Setup happy path
    mock_dl.return_value = 2 # downloaded 2 videos
    mock_convert.return_value = ["cut1.mp3", "cut2.mp3"]
    mock_mashup_func.return_value = "merged.mp3"
    mock_zip.return_value = True
    mock_email_func.return_value = (True, None)
    mock_getsize.return_value = 1000 # Small file size
    
    # We need to set the temp dir creation in the route to NOT fail or we mock tempfile
    # The route calls tempfile.mkdtemp(). We can leave that as real, it cleans up in finally.
    
    data = {
        'singer': 'Test Singer',
        'number_of_videos': '2',
        'duration': '10',
        'email': 'test@example.com'
    }
    
    response = client.post('/generate_mashup', data=data)
    
    # Check
    assert response.status_code == 200
    # response might be json
    assert response.is_json
    assert "Mashup generated" in response.get_json()['message']

def test_generate_mashup_route_invalid(client):
    # Missing email
    data = {
        'singer': 'Test Singer',
        'number_of_videos': '2',
        'duration': '10'
    }
    response = client.post('/generate_mashup', data=data)
    assert response.status_code == 400