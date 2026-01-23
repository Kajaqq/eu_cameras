import spain_parser
import france_gov_parser
import camera_check
import asyncio


def check_cameras(data, download=True):
    # Set 'download' to False to not verify based on image similarity
    asyncio.run(camera_check.main(camera_json=data, download=download))

def get_spain_data(output_file = None):
    print('=' * 36)
    print("Downloading Spain data...")
    print('=' * 36)
    return spain_parser.get_parsed_data(output_file)

def get_france_data(output_file = None):
    print('=' * 36)
    print("Downloading France data...")
    print('=' * 36)
    return france_gov_parser.get_parsed_data(output_file)

def main():
    # Set the output file variable below to save the pre-parsed data too
    check_cameras(data=get_spain_data())
    check_cameras(data=get_france_data())

if __name__ == "__main__":
    main()

