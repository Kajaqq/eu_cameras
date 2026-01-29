import ast
import json
import re
import france_js_download
from collections import defaultdict
from utils import save_json

def get_parsed_data(output_file, input_data=None):
    if not input_data:
        input_data = france_js_download.main()
    final_output = []
    try:
        data_string = input_data.strip()

        data_string = re.sub(r"^var\s+\w+\s*=\s*", "", data_string)
        data_string = re.sub(r";\s*\w+\.\w+\(.*\);?$", "", data_string)

        try:
            parsed_data = ast.literal_eval(data_string)
        except Exception as e:
            print(f"Parsing error: {e}")
            return

        road_regex = re.compile(r"\b(A|N|RN)(\d+)\b", re.IGNORECASE)
        grouped_highways = defaultdict(list)

        for item in parsed_data:
            # New structure: [coords, mystery_list, type_code, description, metadata]
            coords, _, _, description, metadata = item
            match = road_regex.search(description)

            # Normalize highway name (e.g., RN 205 -> N-205, A132 -> A-132)
            if match:
                prefix = "N" if match.group(1).upper() in ["N", "RN"] else "A"
                highway_name = f"{prefix}-{match.group(2)}"
            else:
                highway_name = "Unknown"

            grouped_highways[highway_name].append(
                {
                    "camera_id": metadata.get("id"),
                    "camera_km_point": 0.0,
                    "camera_view": "*",
                    "camera_type": "other",
                    "coords": {
                        "X": coords[1],
                        "Y": coords[0],
                    },
                }
            )

        final_output = [
            {
                "highway": {
                    "name": name,
                    "country": "FR",
                    "cameras": cameras,
                }
            }
            for name, cameras in grouped_highways.items()
        ]
        if output_file:
            save_json(final_output, output_file)
        print(
            f"Successfully parsed {sum(len(v) for v in grouped_highways.values())} cameras."
        )
        print(f"Data grouped by {len(final_output)} highways.")
    except json.JSONDecodeError:
        print("Error: Failed to decode the input JSON file.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    return final_output

if __name__ == "__main__":
    get_parsed_data("data/cameras_fr_other.json")
