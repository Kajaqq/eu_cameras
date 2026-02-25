import math
from pathlib import Path
from tools.utils import load_json, get_country
from config import CONSTANTS

# ==========================================
# MASTER HIGHWAY SORTING LISTS
# ==========================================
UK_NORTH_SOUTH = CONSTANTS.UK.HighwaySort.NORTH_SOUTH
UK_EAST_WEST = CONSTANTS.UK.HighwaySort.EAST_WEST
UK_RINGS = CONSTANTS.UK.HighwaySort.RINGS

ES_NORTH_SOUTH = CONSTANTS.SPAIN.HighwaySort.NORTH_SOUTH
ES_EAST_WEST = CONSTANTS.SPAIN.HighwaySort.EAST_WEST
ES_RINGS = CONSTANTS.SPAIN.HighwaySort.RINGS

FR_NORTH_SOUTH = CONSTANTS.FRANCE.HighwaySort.NORTH_SOUTH
FR_EAST_WEST = CONSTANTS.FRANCE.HighwaySort.EAST_WEST
FR_RINGS = CONSTANTS.FRANCE.HighwaySort.RINGS

IT_NORTH_SOUTH = CONSTANTS.ITALY.HighwaySort.NORTH_SOUTH
IT_EAST_WEST = CONSTANTS.ITALY.HighwaySort.EAST_WEST
IT_RINGS = CONSTANTS.ITALY.HighwaySort.RINGS

COUNTRY_SORT_MAP = {
    "UK": (UK_NORTH_SOUTH, UK_EAST_WEST, UK_RINGS),
    "ES": (ES_NORTH_SOUTH, ES_EAST_WEST, ES_RINGS),
    "FR": (FR_NORTH_SOUTH, FR_EAST_WEST, FR_RINGS),
    "IT": (IT_NORTH_SOUTH, IT_EAST_WEST, IT_RINGS),
}

# ==========================================
# LOOP CONSTANTS
# ==========================================
SEP = CONSTANTS.COMMON.SEPARATOR
DEFAULT_INTERVAL = CONSTANTS.COMMON.SLIDESHOW_INTERVAL
COUNTRY_MAP = CONSTANTS.COMMON.COUNTRY_MAP
DATA_DIR = CONSTANTS.COMMON.DATA_DIR

# A ~10 minute(~90 cameras) loop of the most important highways of the country
HIGHWAY_SEQUENCES = {
    "Spain": CONSTANTS.SPAIN.HIGHWAY_SEQUENCE,
    "France": CONSTANTS.FRANCE.HIGHWAY_SEQUENCE,
    "Italy": CONSTANTS.ITALY.HIGHWAY_SEQUENCE,
    "UK": CONSTANTS.UK.HIGHWAY_SEQUENCE,
}


def get_ring_cameras_angle(cameras):
    """Sorts clockwise around geographic center"""
    if not cameras:
        return lambda cam: 0

    center_x = sum(cam["coords"]["X"] for cam in cameras) / len(cameras)
    center_y = sum(cam["coords"]["Y"] for cam in cameras) / len(cameras)

    def get_clockwise_angle(cam):
        angle = math.atan2(cam["coords"]["X"] - center_x, cam["coords"]["Y"] - center_y)
        if angle < 0:
            angle += 2 * math.pi
        return angle

    return get_clockwise_angle


def get_sort_order(country_code: str = "UK"):
    # Returns empty lists if country code is not found, preventing crashes
    return COUNTRY_SORT_MAP.get(country_code.upper(), ([], [], []))


def sort_cameras(cameras,country, highway: str):
    if not cameras:
        return []

    ns, ew, rings = get_sort_order(country)

    if highway in ns:
        cameras.sort(key=lambda cam: cam["coords"]["Y"])
        return cameras

    elif highway in ew:
        cameras.sort(key=lambda cam: cam["coords"]["X"])
        return cameras

    elif highway in rings:
        cameras.sort(key=get_ring_cameras_angle(cameras))
        return cameras

    else:
        print(
            f"  [Info] Highway {highway} not explicitly categorized. Defaulting to Y-sort."
        )
        cameras.sort(key=lambda cam: cam["coords"]["Y"])
        return cameras


def sample_cameras(cameras, target_count, highway_name=None):
    if not cameras or target_count <= 0:
        return []
    cameras_len = len(cameras)
    if target_count >= cameras_len:
        print( f"[WARN] Camera allocation for {highway_name} exceeds or equals camera count. Expected: {target_count} Got: {cameras_len}")
        print(f"{highway_name}: Returning all {cameras_len} cameras.")
        return cameras
    print(f"{highway_name}: Selecting {target_count} cameras from {cameras_len} available.")
    step = cameras_len / target_count
    return [cameras[int(i * step)] for i in range(target_count)]


def process_highway_sequence(cameras, sequence_list):
    data_map = {item["highway"]["name"]: item["highway"]["cameras"] for item in cameras}
    country = get_country(cameras)
    final_playlist = []

    for highway_name, count in sequence_list:
        base_name = highway_name.split("_")[0]  # Split cameras support "A04_WEST" --> "A04"

        if base_name not in data_map:
            print(f"[WARN]: Highway {base_name} not found in JSON data.")
            continue

        raw_cameras = data_map[base_name]
        filtered_cameras = raw_cameras  # Default to all cameras

        # Italy A4 special case
        if base_name == "A04" and country == "IT":
            if "WEST" in highway_name:
                filtered_cameras = [c for c in raw_cameras if c["coords"]["X"] < 9.2]
            elif "CENTER" in highway_name:
                filtered_cameras = [
                    c for c in raw_cameras if 10.0 < c["coords"]["X"] < 12.0
                ]
            elif "EAST" in highway_name:
                filtered_cameras = [c for c in raw_cameras if c["coords"]["X"] > 12.0]

        if not filtered_cameras:
            print(f"[WARN] Coordinate filter for {highway_name} returned 0 cameras. Skipping." )
            continue

        # 1. SORT
        sorted_cams = sort_cameras(filtered_cameras, country, base_name)

        # 2. SAMPLE
        sampled = sample_cameras(sorted_cams, count, highway_name)

        final_playlist.extend(sampled)

    return final_playlist


def main(data, loop_data=None):
    data = load_json(data)
    country = get_country(data)
    country_name = COUNTRY_MAP[country]
    print(SEP)
    print(f"Creating loop for {country_name}...")
    print(SEP)
    if not loop_data:
        loop_data = HIGHWAY_SEQUENCES[country_name]
    selected_cameras = process_highway_sequence(data, loop_data)
    camera_ids = []
    print(SEP)
    print(f"Successfully compiled loop with {len(selected_cameras)} total cameras:")
    print(SEP)
    camera_ids.extend(cam["camera_id"] for cam in selected_cameras)
    return camera_ids


if __name__ == "__main__":
    json_file = Path(__file__).parent / "data" / "cameras_uk_online.json"
    uk_loop_sequence = [("M20", 5), ("A282", 2),("M25", 8),]
    main(json_file, uk_loop_sequence)