import pytest
import os
import tempfile
from project import valid_input, create_zip, cleanup, mashup, cut_audio


def test_valid_input():
    """Test valid_input function with correct inputs"""
    result = valid_input("Arijit Singh", "5", "30", "test@example.com")
    assert result[0] == True


def test_valid_input_invalid_email():
    """Test valid_input function with invalid email"""
    result = valid_input("Arijit Singh", "5", "30", "invalid_email")
    assert result[0] == False


def test_valid_input_empty_singer():
    """Test valid_input function with empty singer name"""
    result = valid_input("", "5", "30", "test@example.com")
    assert result[0] == False


def test_create_zip():
    """Test create_zip function"""
    # Create a temporary file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as temp_file:
        temp_file.write("test content")
        temp_file_path = temp_file.name
    
    zip_path = temp_file_path + '.zip'
    result = create_zip(temp_file_path, zip_path)
    
    assert result == True
    
    # Clean up
    os.remove(temp_file_path)
    if os.path.exists(zip_path):
        os.remove(zip_path)


def test_mashup_empty_list():
    """Test mashup function with empty audio file list"""
    result = mashup([])
    assert result == None