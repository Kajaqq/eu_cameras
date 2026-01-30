import asyncio
from pathlib import Path
import aiofiles
import aiohttp
from tqdm.asyncio import tqdm

import diff_hash
from utils import save_json, load_json, create_url, CONSTANTS, get_http_settings

SEP = CONSTANTS.COMMON.SEPARATOR
DEFAULT_RATE_LIMIT = CONSTANTS.COMMON.RATE_LIMIT


def get_camera_data(json_data):
    country = json_data[0]["highway"]["country"]
    if country == "IT":
        camera_ids = [
            [camera["camera_id"], camera["url"]]
            for highway in json_data
            for camera in highway["highway"]["cameras"]
        ]
    else:
        camera_ids = [
            [camera["camera_id"], camera["camera_type"]]
            for highway in json_data
            for camera in highway["highway"]["cameras"]
        ]
    return [country, camera_ids]


async def check_camera_async(
    client, source, camera_id, camera_type, rate_limiter, download, output_dir
):
    if source in ["ES", "FR"]:
        url, ext = create_url(source, camera_id, camera_type)
    elif source in ["IT"]:
        url = camera_type
        ext = CONSTANTS.ITALY.VIDEO_EXT
    else:
        raise ValueError(f"Unknown source: {source}")
    async with rate_limiter:
        response_bytes = b""
        try:
            async with client.get(url, allow_redirects=True) as response:
                response.raise_for_status()
                response_bytes = await response.read()
                status_code = response.status
            if len(response_bytes) < 1000:
                raise aiohttp.ClientPayloadError(
                    f"Response too small: {len(response_bytes)} bytes"
                )
            if not download:
                return {"id": camera_id, "alive": status_code}
            filename = f"{camera_id}{ext}"
            file_path = Path.joinpath(output_dir, filename)
            async with aiofiles.open(file_path, mode="wb") as f:
                await f.write(response_bytes)
            return {"id": camera_id, "alive": status_code}

        except (
            aiohttp.ClientError,
            asyncio.TimeoutError,
            aiohttp.ClientPayloadError,
        ):
            # print(f'Error checking camera {camera_id}: {e}')
            return {"id": camera_id, "alive": False, "len": len(response_bytes)}


def remove_offline_cameras(camera_json, errored_cameras, output_file: Path):
    errored_ids = set(errored_cameras)
    removed_count = 0

    # We use a slice [:] to iterate over a copy so we can modify the original list
    for highway_item in camera_json[:]:
        highway = highway_item.get("highway", {})
        cameras = highway.get("cameras", [])

        original_count = len(cameras)
        highway["cameras"] = [c for c in cameras if c["camera_id"] not in errored_ids]

        diff = original_count - len(highway["cameras"])
        if diff > 0:
            removed_count += diff
            print(f"Removed {diff} cameras from {highway.get('name', 'Unknown')}")

        # Remove the whole highway object if no cameras are left
        if not highway["cameras"]:
            camera_json.remove(highway_item)
            print(f"Removed empty highway: {highway.get('name', 'Unknown')}")

    save_json(camera_json, output_file)
    print(SEP)
    print(f"Total removed: {removed_count}. Filtered data saved to {output_file}")


async def main(camera_json, rate_limit=DEFAULT_RATE_LIMIT, download=True):
    # Download camera data
    source, camera_ids = get_camera_data(camera_json)

    # Set up the output path
    output_dir = Path("data/images/")
    if download and not output_dir.exists():
        output_dir.mkdir(parents=True, exist_ok=True)

    rate_limiter = asyncio.Semaphore(rate_limit)

    # Set up aiohttp client
    timeout, connector = get_http_settings(rate_limit=rate_limit)

    # Run the checks
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as client:
        tasks = [
            check_camera_async(
                client, source, cam_id, cam_type, rate_limiter, download, output_dir
            )
            for cam_id, cam_type in camera_ids
        ]
        results = await tqdm.gather(*tasks, desc="Checking cameras", unit="cam")

    # Separate successful and failed cameras
    alive_cameras = [res["id"] for res in results if res["alive"]]
    errored_cameras = [res["id"] for res in results if not res["alive"]]
    probably_offline_cams = ""
    if download:
        print("Verifying sample images...")
        probably_offline_cams = diff_hash.folder_hash(output_dir)
        errored_cameras.extend(probably_offline_cams)
        alive_cameras = list(set(alive_cameras) - set(probably_offline_cams))

    if errored_cameras:
        print(SEP)
        print("Filtering offline cameras")
        print(SEP)
        output_dir = "data/"
        output_file = Path(output_dir + f"cameras_{source.lower()}_online.json")
        remove_offline_cameras(camera_json, errored_cameras, output_file)
        alive_percent = len(alive_cameras) / len(camera_ids) * 100
        print(
            f"{len(alive_cameras)}/{len(camera_ids)} ({alive_percent:.2f}%) cameras are online."
        )


if __name__ == "__main__":
    camera_file = load_json("data/cameras_fr.json")
    asyncio.run(main(camera_json=camera_file))
