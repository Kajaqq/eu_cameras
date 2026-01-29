import datetime
import json
import math
import pathlib
from typing import Optional, Union
from zoneinfo import ZoneInfo

import httpx


class CONSTANTS:
    class COMMON:
        HTTPS_PREFIX = "https:"
        SEPARATOR = '=' * 36
        VIDEO_EXTENSIONS = ['.mp4', '.flv']
        IMAGE_EXTENSIONS = ['.jpg', '.jpeg' ,'.png']

    class FRANCE:
        BASE_URL = 'https://www.bison-fute.gouv.fr/'
        TIMESTAMP_URL = 'data/iteration/date.json'
        CAMERA_API = 'data/data-{datetime}/trafic/maintenant/camerasOL6/camerasOL6.json'
        CAMERA_URL = 'https://www.bison-fute.gouv.fr/camera-upload/'
        CAMERA_URL_OTHER = 'https://gieat.viewsurf.com?id={camera_id}&action=mediaRedirect'
        VIDEO_EXT = '.mp4'
        IMAGE_EXT = '.png'

    class SPAIN:
        BASE_URL = 'https://etraffic.dgt.es/etrafficWEB/api/'
        CAMERA_URL = 'https://infocar.dgt.es/etraffic/data/camaras/'
        CAMERA_API = 'cache/getCamaras'
        XOR_KEY = 'K'
        IMAGE_EXT = '.jpg'
    class COMMON:
        NON_DOWNLOADABLE = ['vid', 'other']


class HTTPError(Exception):
    """Custom exception for HTTP errors"""
    pass


def download(url: str, timeout: float = 30.0) -> str:
    """Download content from URL with proper error handling and timeout"""
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(url)
            response.raise_for_status()
            return response.text
    except httpx.RequestError as e:
        raise HTTPError(f"Request failed for {url}: {e}") from e
    except httpx.HTTPStatusError as e:
        raise HTTPError(f"HTTP {e.response.status_code} for {url}") from e


def download_post(url: str, data: Optional[dict] = None, timeout: float = 30.0) -> str:
    """Download content via POST with proper error handling and timeout"""
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(url, json=data)
            response.raise_for_status()
            return response.text
    except httpx.RequestError as e:
        raise HTTPError(f"POST request failed for {url}: {e}") from e
    except httpx.HTTPStatusError as e:
        raise HTTPError(f"HTTP {e.response.status_code} for {url}") from e


def unix_to_datetime(timestamp: Union[int, float, str]) -> datetime.datetime:
    """Convert Unix timestamp to datetime with timezone normalization"""
    normalized_timestamp = timestamp_normalize(float(timestamp))
    timezone = ZoneInfo("Europe/Paris")
    return datetime.datetime.fromtimestamp(normalized_timestamp, timezone)


def french_timestamp(timestamp: Union[int, float, str]) -> str:
    """Convert Unix timestamp to French-formatted timestamp string"""
    dt = unix_to_datetime(timestamp)
    return dt.strftime("%Y%m%d-%H%M%S")


def xor_decode(msg: bytes, key: str) -> str:
    """XOR decode message with a given key"""

    # Using bytearray for faster XOR operations
    key = key.encode('utf-8')
    key_len = len(key)

    decoded = bytearray(len(msg))
    for i in range(len(msg)):
        decoded[i] = msg[i] ^ key[i % key_len]

    return decoded.decode('utf-8')


def save_json(json_data: Union[str, dict, list], output: Path) -> None:
    """Save JSON data to a file with proper error handling"""
    output_dir = pathlib.Path(output).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    if output.exists():
        output=output.with_name(f"{output.stem}_other.json")
    try:
        # Handle both string and already parsed JSON data
        if isinstance(json_data, str):
            with open(output, 'w', encoding='utf-8') as outfile:
                outfile.write(json_data)
        else:
            with open(output, 'w', encoding='utf-8') as outfile:
                json.dump(json_data, outfile, indent=4, ensure_ascii=False)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON data: {e}") from e
    except IOError as e:
        raise IOError(f"Failed to write file {output}: {e}") from e


def load_json(filename: str) -> dict:
    """Load JSON data from a file with proper error handling"""
    try:
        with open(filename, 'r', encoding='utf-8') as infile:
            return json.load(infile)
    except IOError as e:
        raise IOError(f"Failed to read file {filename}: {e}") from e
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON data: {e}") from e


def create_url(base, camera_id, camera_type):
    ext = ''
    if base == "FR":
        base_url = CONSTANTS.FRANCE.CAMERA_URL
        if camera_type == 'vid':
            ext = CONSTANTS.FRANCE.VIDEO_EXT
        elif camera_type == 'img':
            ext = CONSTANTS.FRANCE.IMAGE_EXT
        elif camera_type == 'other':
            base_url = CONSTANTS.FRANCE.OTHER.CAMERA_URL
            ext = CONSTANTS.FRANCE.OTHER.VIDEO_EXT
            return base_url.format(camera_id=camera_id), ext
    elif base == "ES":
        base_url = CONSTANTS.SPAIN.CAMERA_URL
        ext = CONSTANTS.SPAIN.IMAGE_EXT
    else:
        return Exception("Invalid data")
    return f"{base_url}{camera_id}{ext}", ext


def timestamp_normalize(timestamp: Union[int, float]) -> float:
    """Normalize timestamp to 10-digit Unix timestamp"""
    if timestamp <= 0:
        raise ValueError("Timestamp must be positive")

    timestamp_len = number_len(int(timestamp))

    # If the timestamp has more than 10 digits (milliseconds, microseconds, etc.)
    if timestamp_len > 10:
        zeros_to_remove = timestamp_len - 10
        divisor = 10 ** zeros_to_remove
        return float(timestamp) / divisor

    return float(timestamp)


def number_len(number: int) -> int:
    """Calculate the number of digits in a number efficiently"""
    if number == 0:
        return 1
    return math.floor(math.log10(abs(number))) + 1
