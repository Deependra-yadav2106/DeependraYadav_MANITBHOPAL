import requests
import os
import tempfile
from urllib.parse import urlparse

def download_file(url: str) -> str:
    """
    Downloads a file from a URL to a temporary file and returns the path.
    """
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        

        parsed_url = urlparse(url)
        path = parsed_url.path
        ext = os.path.splitext(path)[1]
        
        if not ext:
            content_type = response.headers.get('content-type')
            if content_type == 'application/pdf':
                ext = '.pdf'
            elif content_type in ['image/jpeg', 'image/jpg']:
                ext = '.jpg'
            elif content_type == 'image/png':
                ext = '.png'
            else:
                ext = ''


        fd, temp_path = tempfile.mkstemp(suffix=ext)
        with os.fdopen(fd, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        return temp_path
    except Exception as e:
        raise Exception(f"Failed to download file: {str(e)}")

def cleanup_file(path: str):
    """
    Removes the temporary file.
    """
    if os.path.exists(path):
        os.remove(path)
