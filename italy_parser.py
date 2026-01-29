import json
from collections import defaultdict
from pathlib import Path

from utils import CONSTANTS, download, save_json

BASE_URL = CONSTANTS.ITALY.BASE_URL
CAMERA_BASE_URL = CONSTANTS.ITALY.CAMERA_URL

def get_camera_data(url=BASE_URL):
    json_data = download(url)
    return json.loads(json_data)

def parse_italy_cameras(raw_data):
    grouped_highways = defaultdict(list)
    
    # The raw data contains a "webcams" list
    webcams = raw_data.get("webcams", [])
    
    for cam in webcams:
        highway_name = cam.get("c_str", "Unknown")

        # Get the video URL fragment from frames -> V -> t_url
        video_fragment = cam.get("frames", {}).get("V", {}).get("t_url", "")

        if video_fragment:
            full_url = f"{CAMERA_BASE_URL}{video_fragment}"
        else:
            continue

        # Determine a direction (+ ascending, - descending, * unknown)
        km_ini = cam.get("n_prg_km_ini")
        km_fin = cam.get("n_prg_km_fin")
        
        if km_ini is not None and km_fin is not None:
            if km_ini < km_fin:
                direction = "+"
            elif km_ini > km_fin:
                direction = "-"
            else:
                direction = "*"
        else:
            direction = "*"

        camera_entry = {
            "camera_id": str(cam.get("c_tel")),
            "camera_km_point": cam.get("n_prg_km", 0.0),
            "camera_view": direction,
            "camera_type": "vid",
            "url": full_url,
            "coords": {
                "X": cam.get("n_crd_lon"),
                "Y": cam.get("n_crd_lat"),
            },
        }
        grouped_highways[highway_name].append(camera_entry)

    # Format into the standard highway structure used in other parsers
    final_output = [
        {
            "highway": {
                "name": name,
                "country": "IT",
                "cameras": cameras,
            }
        }
        for name, cameras in grouped_highways.items()
    ]
    print(
        f"Successfully parsed {sum(len(v) for v in grouped_highways.values())} cameras."
    )
    print(f"Data grouped by {len(final_output)} highways.")
    return final_output

def get_parsed_data(output_file=None):
    raw_data = get_camera_data()
    parsed_data = parse_italy_cameras(raw_data)
    if output_file:
        save_json(parsed_data, output_file)
    return parsed_data

if __name__ == "__main__":
    output = Path('data/cameras_it.json')
    get_parsed_data(output)