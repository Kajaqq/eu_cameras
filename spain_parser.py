import json
from base64 import b64decode
from collections import defaultdict

from utils import download_post, save_json, xor_decode, CONSTANTS

BASE_URL = CONSTANTS.SPAIN.BASE_URL
DATA_URL = BASE_URL + CONSTANTS.SPAIN.CAMERA_API
XOR_KEY = CONSTANTS.SPAIN.XOR_KEY



def get_camera_data():
    download_link = DATA_URL
    data = download_post(download_link)
    decoded_data = decode_data(data)
    return decoded_data


def decode_data(camaras_data):
    try:
        decoded_bytes = b64decode(camaras_data, validate=True)
    except Exception as exc:
        raise ValueError(f"Base64 decode failed: {exc}") from exc

    json_text = xor_decode(decoded_bytes, XOR_KEY)

    print("Successfully downloaded camera data.")
    return json_text


def parse_camera_data(json_data, output_file=None):
    try:
        raw_data = json.loads(json_data)

        grouped_highways = defaultdict(list)
        camaras = raw_data.get('camaras') or []
        for cam in camaras:
            highway_name = cam.get('carretera') or 'Unknown'
            grouped_highways[highway_name].append({
                "camera_id": cam.get('idCamara'),
                "camera_km_point": cam.get('pk'),
                "camera_view": cam.get('sentido'),
                "camera_type": "",
                "coords": {
                    "X": cam.get('coordX'),
                    "Y": cam.get('coordY')
                }
            })

        final_output = [
            {
                "highway": {
                    "name": name,
                    "country": "ES",
                    "cameras": cameras
                }
            }
            for name, cameras in grouped_highways.items()
        ]


        print(f"Successfully parsed {len(camaras)} cameras.")
        print(f"Data grouped by {len(final_output)} highways.")
        if output_file:
            print(f"Output saved to '{output_file}'.")
            save_json(final_output, output_file)
        return final_output
    except json.JSONDecodeError:
        print("Error: Failed to decode the input JSON file.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


def get_parsed_data(output_file=None):
    camera_data = get_camera_data()
    spain_data = parse_camera_data(camera_data, output_file)
    return spain_data

if __name__ == "__main__":
    OUTPUT_DIR = 'data/cameras_es_gov.json'
    camera_data = get_camera_data()
    parse_camera_data(camera_data, OUTPUT_DIR)
