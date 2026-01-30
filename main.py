import asyncio

import italy_parser
import spain_parser
import france_gov_parser
import france_js_parse
import camera_check

from utils import CONSTANTS

SEP = CONSTANTS.COMMON.SEPARATOR
DEFAULT_RATE_LIMIT = CONSTANTS.COMMON.RATE_LIMIT
SPAIN_RATE_LIMIT = CONSTANTS.SPAIN.RATE_LIMIT
ITALY_RATE_LIMIT = CONSTANTS.ITALY.RATE_LIMIT


async def check_cameras(data, rate_limit=DEFAULT_RATE_LIMIT, download=True):
    # Set 'download' to False to not verify based on image similarity
    await camera_check.main(camera_json=data, download=download, rate_limit=rate_limit)


async def get_spain_data(output_file=None):
    print(SEP)
    print("Downloading Spain data...")
    print(SEP)
    return await spain_parser.get_parsed_data(output_file)


async def get_france_data(output_file=None):
    print(SEP)
    print("Downloading France data...")
    print(SEP)
    return await france_gov_parser.get_parsed_data(output_file)


async def get_france_js_data(output_file=None):
    print(SEP)
    print("Downloading France JS data...")
    print(SEP)
    return await france_js_parse.get_parsed_data(output_file)


async def get_italy_data(output_file=None):
    print(SEP)
    print("Downloading Italy data...")
    print(SEP)
    return await italy_parser.get_parsed_data(output_file)


async def main():
    # Set the output file variable below to save the pre-parsed data too
    await check_cameras(data=await get_spain_data(), rate_limit=SPAIN_RATE_LIMIT)
    await check_cameras(data=await get_france_data())
    await check_cameras(data=await get_france_js_data())
    await check_cameras(data=await get_italy_data(), rate_limit=ITALY_RATE_LIMIT)


if __name__ == "__main__":
    asyncio.run(main())
