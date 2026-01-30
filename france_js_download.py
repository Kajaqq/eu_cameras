import httpx
from utils import download, CONSTANTS
import re

BASE_URL = CONSTANTS.FRANCE.OTHER.BASE_URL
AUTH_URL = CONSTANTS.FRANCE.OTHER.AUTH_URL
HTTPS_PREFIX = CONSTANTS.COMMON.HTTPS_PREFIX
CAMERA_SUFFIX = CONSTANTS.FRANCE.OTHER.CAMERA_SUFFIX


def get_auth_key(url):
    key = None
    with httpx.stream("GET", url) as r:
        r.raise_for_status()
        for line in r.iter_lines():
            try:
                if line.startswith("WT3_AuthenticateWebSite"):
                    line = line.split("'")
                    key = line[3]
                    break
            except (IndexError, httpx.HTTPError) as e:
                print(f"Error: {e}")
    return key


def get_phase2(key, url=AUTH_URL):
    url = url.format(key=key)
    phase2 = download(url).split(";")
    phase2 = [x for x in phase2 if x.startswith("WT3_SawtLinkToPhase2.src =")]
    phase2_url = phase2[0].split("'")[1]
    phase2_url = HTTPS_PREFIX + phase2_url
    return phase2_url


def parse_phase2(phase2_url):
    p2 = download(phase2_url)
    return p2.split(";")


def resolve_js_variables(lines, target_domain="www.autoroutes.fr"):
    var_map = {}

    # regex to match: var NAME = 'VALUE' or "VALUE"
    var_pattern = re.compile(
        r"var\s+(\w+)\s*=\s*['\"]([^'\"]*)['\"](?:\.substring\((\d+),(\d+)\))?"
    )

    for line in lines:
        line = line.strip()

        # 1. Handle Domain Conditionals: if(document.domain == '...') { var X = 'Y' }
        # We look for the assignment that matches our domain OR the 'else' block
        if "document.domain" in line:
            is_match = f"'{target_domain}'" in line
            is_negation = "!=" in line

            # Logic: (== and match) OR (!= and no match) -> Take the 'if' value
            # Otherwise, we'd wait for the 'else' block (which usually follows in the list)
            should_take = (is_match and not is_negation) or (
                is_negation and not is_match
            )

            match = var_pattern.search(line)
            if match and should_take:
                name, val, start, end = match.groups()
                var_map[name] = val[int(start) : int(end)] if start else val
            continue

        # 2. Handle standard assignments (including those in 'else' blocks that didn't match above)
        match = var_pattern.search(line)
        if match:
            name, val, start, end = match.groups()
            # Only update if not already set by a specific domain condition
            if name not in var_map:
                var_map[name] = val[int(start) : int(end)] if start else val

    return var_map


def assemble_url(phase2_list, var_values):
    descriptor_line = next(
        (x for x in phase2_list if "var SAWT3_WebcamDescriptorsLocation =" in x), None
    )

    if descriptor_line:
        # Extract the sum components: var X = A + B + C
        parts_string = descriptor_line.split("=")[1].strip().rstrip(";")
        var_names = [v.strip() for v in parts_string.split("+")]

        # Join the resolved values
        final_path = "".join(var_values.get(name, "") for name in var_names)
        full_url = HTTPS_PREFIX + final_path + CAMERA_SUFFIX
    else:
        raise ValueError("Could not find descriptor line in phase 2 list.")
    return full_url


# noinspection PyShadowingNames
def main():
   # print("Downloading data")
    auth_key = get_auth_key(BASE_URL)
    phase_2_url = get_phase2(auth_key)
    phase_2_list = parse_phase2(phase_2_url)
    resolved_vars = resolve_js_variables(phase_2_list)
    full_url = assemble_url(phase_2_list, resolved_vars)
    camera_data = download(full_url)
   # print ("Successfully downloaded data.")
    return camera_data


if __name__ == "__main__":
    js_data = main()
    with open("data/webcams_fr_other.js", "w", encoding="utf-8") as f:
        f.write(js_data)
        print("Downloaded France js data to webcams_fr_other.js")
