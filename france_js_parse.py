import ast
import json
import os
import re
from collections import defaultdict


def parse_js_cameras(input_file, output_file):
    if not os.path.exists(input_file):
        print(f"Error: The file '{input_file}' was not found.")
        return

    try:
        with open(input_file, "r", encoding="utf-8") as f:
            data_string = f.read().strip()

        try:
            parsed_data = ast.literal_eval(f"[{data_string}]")
        except Exception as e:
            print(f"Parsing error: {e}")
            return

        road_regex = re.compile(r"\b(A)(\d+)\b")
        grouped_highways = defaultdict(list)

        for item in parsed_data:
            coords, description, metadata = item
            match = road_regex.search(description)
            highway_name = f"{match.group(1)}-{match.group(2)}" if match else "Unknown"

            grouped_highways[highway_name].append({
                "camera_id": metadata.get("id"),
                "camera_km_point": 0.0,
                "camera_view": "*",
                "camera_type": "other",
                "coords": {
                    "X": coords[1],
                    "Y": coords[0],
                },
            })

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

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(final_output, f, indent=4, ensure_ascii=False)

        print(f"Successfully parsed {sum(len(v) for v in grouped_highways.values())} cameras.")
        print(f"Data grouped by {len(final_output)} highways.")
        print(f"Output saved to '{output_file}'.")
    except json.JSONDecodeError:
        print("Error: Failed to decode the input JSON file.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    parse_js_cameras("data/webcams_fr_other.js", "data/cameras_fr_other.json")
