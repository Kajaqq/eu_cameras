import json
import re
from collections import defaultdict

import aiohttp
from lambert import Lambert93, convertToWGS84Deg

from utils import download, french_timestamp, save_json, CONSTANTS, get_http_settings

BASE_URL = CONSTANTS.FRANCE.BASE_URL
TIMESTAMP_URL = BASE_URL + CONSTANTS.FRANCE.TIMESTAMP_URL
CAMERA_URL = BASE_URL + CONSTANTS.FRANCE.CAMERA_API


ROAD_REGEX = re.compile(r"\b([A|N|D|M])(\d+)\b")
PR_REGEX = re.compile(r"PR\s*(\d+)(?:\+(\d+))?")


async def get_url(session):
    timestamp = await download(url=TIMESTAMP_URL, session=session)
    timestamp = int(timestamp[1:-1])
    timestamp = french_timestamp(timestamp)
    download_link = CAMERA_URL.format(datetime=timestamp)
    return download_link


async def get_camera_data(session):
    download_link = await get_url(session)
    data = await download(url=download_link, session=session)
    return data


def convert_to_wgs84(lon, lat):
    pt = convertToWGS84Deg(lon, lat, Lambert93)
    return pt.getX(), pt.getY()


def parse_gov_cameras(baguettes, output_file):
    try:
        raw_data = json.loads(baguettes)

        grouped_highways = defaultdict(list)
        features = raw_data.get("features") or []

        for feature in features:
            props = feature.get("properties") or {}
            geometry = feature.get("geometry") or {}

            camera_id = feature.get("id", "")
            full_label = props.get("libelleCamera") or "Unknown"

            road_match = ROAD_REGEX.search(full_label)
            highway_name = (
                f"{road_match.group(1)}-{road_match.group(2)}"
                if road_match
                else "Unknown"
            )

            km_point = 0.0
            pr_match = PR_REGEX.search(full_label)
            if pr_match:
                km = int(pr_match.group(1))
                meters = int(pr_match.group(2)) if pr_match.group(2) else 0
                km_point = km + (meters / 1000.0)

            flux_type = props.get("typeFlux") or ""
            cam_type = (
                "vid"
                if flux_type == "VIDEO"
                else "img"
                if flux_type == "IMAGE"
                else "unknown"
            )

            coords_in = geometry.get("coordinates") or []
            if len(coords_in) >= 2:
                lon, lat = convert_to_wgs84(coords_in[0], coords_in[1])
            else:
                lon, lat = 0.0, 0.0

            grouped_highways[highway_name].append(
                {
                    "camera_id": camera_id,
                    "camera_km_point": round(km_point, 3),
                    "camera_view": "*",
                    "camera_type": cam_type,
                    "coords": {"X": round(lon, 6), "Y": round(lat, 6)},
                }
            )

        final_output = [
            {"highway": {"name": name, "country": "FR", "cameras": cameras}}
            for name, cameras in grouped_highways.items()
        ]

        print(f"Successfully parsed {len(features)} cameras.")
        print(f"Grouped into {len(final_output)} highways.")
        if output_file:
            save_json(final_output, output_file)
            print(f"Saved to '{output_file}'.")
        return final_output
    except json.JSONDecodeError:
        print("Error: Failed to decode the input JSON file.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


async def get_parsed_data(output_file=None):
    timeout, connector = get_http_settings()
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        camera_data = await get_camera_data(session=session)
    france_cameras = parse_gov_cameras(camera_data, output_file)
    return france_cameras


if __name__ == "__main__":
    import asyncio

    OUTPUT_DIR = "data/cameras_fr_gov.json"
    asyncio.run(get_parsed_data(output_file=OUTPUT_DIR))
