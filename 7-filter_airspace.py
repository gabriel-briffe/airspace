import json

INPUT_FILE = 'airspace_openAIP_unfiltered.geojson'
# OUTPUT_FILE = 'airspace_maxFl195.geosjon'
OUTPUT_FILE = '/Users/gabrielbriffe/code/mountainCircles-map-beta/test2/merged_asp.geojson'

# Threshold in meters
THRESHOLD = 5944


def process_feature(feature):
    props = feature.get('properties', {})
    # print(props)
    # Read and parse lowerUlArray and upperUlArray
    lower_ul_str = props.get('lowerUlArray')
    upper_ul_str = props.get('upperUlArray')
    try:
        lower_ul_array = json.loads(lower_ul_str) if lower_ul_str else []
    except Exception as e:
        lower_ul_array = []

    try:
        upper_ul_array = json.loads(upper_ul_str) if upper_ul_str else []
    except Exception as e:
        upper_ul_array = []

    # if props.get('type') == 21:
    #     print(props)
    # Condition 1: if any lower entry with ulunit 'FL' and ulvalue >= 195, skip this feature
    for lower in lower_ul_array:
        if lower.get('ulunit') == 'FL' and lower.get('ulvalue') >= 195 and not props.get('type') == 21:
            return None
        

    # Condition 2: if any upper entry with ulunit 'FL' and ulvalue > 195 and (no lower entry with 'FL' or any lower 'FL' entry has ulvalue < 195) then update upper ulvalue to 195
    for upper in upper_ul_array:
        if upper.get('ulunit') == 'FL' and upper.get('ulvalue') > 195:
            # Determine if condition is met based on lower entries
            lower_fl = [l for l in lower_ul_array if l.get('ulunit') == 'FL']
            if any(l.get('ulvalue') < 195 for l in lower_fl) and not props.get('type') == 21:
                upper['ulvalue'] = 195

    # Re-serialize the arrays back to JSON strings
    props['upperUlArray'] = json.dumps(upper_ul_array)
    props['lowerUlArray'] = json.dumps(lower_ul_array)
    return feature


def main():
    # Load input GeoJSON
    try:
        with open(INPUT_FILE, 'r') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading {INPUT_FILE}: {e}")
        return

    features = data.get('features', [])
    new_features = []

    for feature in features:
        processed = process_feature(feature)
        if processed is not None:
            new_features.append(processed)

    # Update features with filtered list
    data['features'] = new_features

    # Write the processed GeoJSON to output file
    try:
        with open(OUTPUT_FILE, 'w') as outfile:
            json.dump(data, outfile, indent=2)
        print(f"Filtered GeoJSON saved to {OUTPUT_FILE}")
    except Exception as e:
        print(f"Error writing to {OUTPUT_FILE}: {e}")


if __name__ == '__main__':
    main()
