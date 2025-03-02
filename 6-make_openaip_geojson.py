import json

# Reverse mappings based on comments in 5-process_geojson.py
ICAO_CLASS_MAP_R = {
    "A": 0,
    "B": 1,
    "C": 2,
    "D": 3,
    "E": 4,
    "F": 5,
    "G": 6,
    "Other": 8
}

TYPE_MAP_R = {
    "AWY": 0,
    "Restricted": 1,
    "Dangerous": 2,
    "Prohibited": 3,
    "CTR": 4,
    "TMZ": 5,
    "RMZ": 6,
    "TMA": 7,
    "FIR": 10,
    "gliding": 21,
    "CTA": 26,
    "Para/voltige": 28,
    "ZSM": 29,
    "SIV": 33
}

UNIT_MAP_R = {
    "ft": 1,
    "FL": 6
}

REFERENCE_DATUM_MAP_R = {
    "GND": 0,
    "MSL": 1,
    "STD": 2,
    "1013": 2
}

# For types not in the mapping, assign sequential values starting from 34
unknown_type_map = {}
unknown_dynamic_counter = 34


def convert_altitude(ul_array_str):
    """Converts the JSON altitude array string into an openAIP altitude dictionary using the reverse mappings."""
    try:
        arr = json.loads(ul_array_str)
        if arr and isinstance(arr, list):
            entry = arr[0]  # use the first entry
            value = entry.get("ulvalue")
            unit_str = entry.get("ulunit")
            ref_str = entry.get("ulref")
            unit = UNIT_MAP_R.get(unit_str, None)
            # Normalize reference string to uppercase for matching
            ref_key = str(ref_str).upper() if isinstance(ref_str, str) else ref_str
            ref = REFERENCE_DATUM_MAP_R.get(ref_key, None)
            return {"value": value, "unit": unit, "referenceDatum": ref}
    except Exception as e:
        print("Error converting altitude:", e)
    return None


def main():
    # Read the processed geojson
    with open('airspace_processed.geojson', 'r') as f:
        data = json.load(f)

    global unknown_dynamic_counter
    features = data.get("features", [])
    for feature in features:
        props = feature.get("properties", {})
        
        # Reverse mapping for icaoClass
        icao_str = props.get("icaoClass", "Other")
        props["icaoClass"] = ICAO_CLASS_MAP_R.get(icao_str, 8)

        # Reverse mapping for type
        type_str = props.get("type", "Other")
        if type_str in TYPE_MAP_R:
            props["type"] = TYPE_MAP_R[type_str]
        else:
            if type_str not in unknown_type_map:
                unknown_type_map[type_str] = unknown_dynamic_counter
                unknown_dynamic_counter += 1
            props["type"] = unknown_type_map[type_str]

        # Convert upper altitude array to openAIP upperLimit
        if "upperUlArray" in props:
            converted = convert_altitude(props["upperUlArray"])
            if converted:
                props["upperLimit"] = converted
            del props["upperUlArray"]

        # Convert lower altitude array to openAIP lowerLimit
        if "lowerUlArray" in props:
            converted = convert_altitude(props["lowerUlArray"])
            if converted:
                props["lowerLimit"] = converted
            del props["lowerUlArray"]

    # Write the openAIP geojson
    with open('/Users/gabrielbriffe/code/mountainCircles-map-beta/test2/merged_asp.geojson', 'w') as outfile:
    # with open('airspace_openAIP.geojson', 'w') as outfile:
        json.dump(data, outfile, indent=2)


if __name__ == '__main__':
    main() 