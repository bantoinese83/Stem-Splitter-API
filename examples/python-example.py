"""
Python Example - Stem Splitter API

This example demonstrates how to use the Stem Splitter API from Python.
"""

import requests
import os
from pathlib import Path


def separate_audio(file_path: str, api_url: str = "https://stem-splitter-api-production.up.railway.app", stems: int = 2):
    """
    Separate an audio file into stems.
    
    Args:
        file_path: Path to the audio file
        api_url: API base URL
        stems: Number of stems (2, 4, or 5)
    
    Returns:
        Tuple of (success: bool, output_path: str, error_message: str)
    """
    if not os.path.exists(file_path):
        return False, None, f"File not found: {file_path}"
    
    if stems not in [2, 4, 5]:
        return False, None, "Stems must be 2, 4, or 5"
    
    try:
        # Check API health
        print("Checking API health...")
        health_response = requests.get(f"{api_url}/health", timeout=5)
        if health_response.status_code == 200:
            health = health_response.json()
            print(f"API Status: {health['status']}")
            print(f"Max file size: {health['max_file_size_mb']} MB")
            print(f"Allowed formats: {', '.join(health['allowed_extensions'])}")
        else:
            print(f"Warning: Health check failed ({health_response.status_code})")
        
        # Prepare file upload
        print(f"\nSeparating audio: {file_path}")
        print("This may take a few minutes...")
        
        with open(file_path, 'rb') as audio_file:
            files = {'file': (os.path.basename(file_path), audio_file, 'audio/mpeg')}
            data = {'stems': stems}
            
            # Make request
            response = requests.post(
                f"{api_url}/separate",
                files=files,
                data=data,
                timeout=600,  # 10 minutes timeout
                stream=True
            )
        
        if response.status_code == 200:
            # Save output
            output_path = f"output_{stems}stems.zip"
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            request_id = response.headers.get('X-Request-ID', 'unknown')
            print(f"\n✅ Success!")
            print(f"Saved to: {output_path}")
            print(f"Request ID: {request_id}")
            return True, output_path, None
        else:
            error_detail = "Unknown error"
            try:
                error_json = response.json()
                error_detail = error_json.get('detail', error_detail)
            except:
                error_detail = response.text or error_detail
            
            return False, None, f"API error ({response.status_code}): {error_detail}"
            
    except requests.exceptions.Timeout:
        return False, None, "Request timed out. File may be too large or processing too slow."
    except requests.exceptions.ConnectionError:
        return False, None, f"Could not connect to API at {api_url}"
    except Exception as e:
        return False, None, f"Unexpected error: {str(e)}"


def main():
    """Main example function."""
    # Configuration
    API_URL = os.getenv("STEM_SPLITTER_API_URL", "https://stem-splitter-api-production.up.railway.app")
    AUDIO_FILE = "./data/audio_example.mp3"  # Change to your audio file
    STEMS = 2  # Options: 2, 4, or 5
    
    # Check if file exists
    if not os.path.exists(AUDIO_FILE):
        print(f"❌ Error: Audio file not found: {AUDIO_FILE}")
        print("\nPlease update AUDIO_FILE variable or place an audio file at that path.")
        return
    
    # Separate audio
    success, output_path, error = separate_audio(AUDIO_FILE, API_URL, STEMS)
    
    if success:
        print(f"\n🎉 Audio separated successfully!")
        print(f"Output file: {output_path}")
    else:
        print(f"\n❌ Error: {error}")


if __name__ == "__main__":
    main()

