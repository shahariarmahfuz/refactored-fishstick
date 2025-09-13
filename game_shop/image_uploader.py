import requests

API_ENDPOINT = "https://xabi4545.pythonanywhere.com/upload"

def upload_image_to_xenko(file_storage):
    """
    Takes a FileStorage object from Flask, uploads it to the xenko API,
    and returns the public URL if successful, otherwise None.
    """
    if not file_storage or not file_storage.filename:
        return None

    files = {"file": (file_storage.filename, file_storage.read(), file_storage.content_type)}
    
    try:
        response = requests.post(API_ENDPOINT, files=files, timeout=30) # 30 second timeout
        response.raise_for_status()  # HTTP ارর থাকলে Exception raise করবে
        
        data = response.json()
        if data and 'url' in data:
            return data['url']
        else:
            print("API Error: 'url' not in response.", data)
            return None
    except requests.exceptions.RequestException as e:
        print(f"Failed to upload image: {e}")
        return None
