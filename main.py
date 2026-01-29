import italy_parser
import spain_parser
import france_gov_parser
import france_js_parse
import camera_check
import asyncio
from utils import CONSTANTS

SEP = CONSTANTS.COMMON.SEPARATOR


def check_cameras(data, download=True):
    # Set 'download' to False to not verify based on image similarity
    asyncio.run(camera_check.main(camera_json=data, download=download))


def get_spain_data(output_file=None):
    print(SEP)
    print("Downloading Spain data...")
    print(SEP)
    return spain_parser.get_parsed_data(output_file)


def get_france_data(output_file=None):
    print(SEP)
    print("Downloading France data...")
    print(SEP)
    return france_gov_parser.get_parsed_data(output_file)


def get_france_js_data(output_file=None):
    print(SEP)
    print("Downloading France JS data...")
    print(SEP)
    return france_js_parse.get_parsed_data(output_file)


def get_italy_data(output_file=None):
    print(SEP)
    print("Downloading Italy data...")
    print(SEP)
    return italy_parser.get_parsed_data(output_file)


def main():
    # Set the output file variable below to save the pre-parsed data too
    check_cameras(data=get_spain_data())
    check_cameras(data=get_france_data())
    check_cameras(data=get_france_js_data())
    check_cameras(data=get_italy_data())


if __name__ == "__main__":
    main()
