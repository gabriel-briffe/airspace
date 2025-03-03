import json
import re


def process_geojson(data):
    for feature in data.get('features', []):
        props = feature.get('properties', {})
        # Set icaoClass to "Other" if not present or falsy
        if 'icaoClass' not in props or not props['icaoClass']:
            props['icaoClass'] = "Other"

        # Determine the 'type' property based on the 'name'
        name = props.get('name', '')
        name_upper = name.upper()
        name_lower = name.lower()
        new_type = None

        if ' aéromodélisme ' in name:
            new_type = "aéromodélisme"
        elif name.startswith("LF R"):
            new_type = "Restricted"
        elif name.startswith("TMA "):
            new_type = "TMA"
        elif name.startswith("SIV"):
            new_type = "SIV"
        elif ' treuillage ' in name:
            new_type = "treuil"
        elif (' para ' in name) or (' voltige ' in name):
            new_type = "Para/voltige"
        elif "activité particulière" in name:
            new_type = "activité_particulière"
        elif "AWY" in name_upper:
            new_type = "AWY"
        elif name.startswith("LF D"):
            new_type = "Dangerous"
        elif name.startswith("LF P"):
            new_type = "Prohibited"
        elif name.startswith("CTR "):
            new_type = "CTR"
        elif name.startswith("RMZ"):
            new_type = "RMZ"
        elif name.startswith("TMZ"):
            new_type = "TMZ"
        elif name.startswith("FIR"):
            new_type = "FIR"
        elif name.startswith("CTA"):
            new_type = "CTA"
        elif name.startswith("LF TRA "):
            new_type = "TRA"
        elif name.startswith("LTA "):
            new_type = "LTA"
        elif name.startswith("UIR "):
            new_type = "UIR"
        elif name.startswith("UTA "):
            new_type = "UTA"
        
        # Check restrictions field for gliding conditions
        restrictions = props.get('restrictions', '')
        restrictions_lower = restrictions.lower()
        if 'activité vélivole' in restrictions_lower: # or 'activité vélivole régie par protocole' in restrictions_lower:
            new_type = "gliding"
        if name.startswith("LTA") and props['icaoClass'] == "E":
            new_type = "gliding"
        if 'survol / overflight' in restrictions_lower :
            new_type = "Park"

        if props.get('code_zsm', ''):
            new_type = "ZSM"

        
        props['type'] = new_type if new_type else "Other"

        # Process upperAltitude
        upper_alt = props.get('upperAltitude', '')
        if isinstance(upper_alt, str) and upper_alt.strip() != "":
            parsed_upper = parse_altitude(upper_alt, "upperAltitude", props.get('name', 'Unknown'))
            if parsed_upper:
                props["upperUlArray"] = json.dumps(parsed_upper)
        
        # Process lowerAltitude
        lower_alt = props.get('lowerAltitude', '')
        if isinstance(lower_alt, str) and lower_alt.strip() != "":
            parsed_lower = parse_altitude(lower_alt, "lowerAltitude", props.get('name', 'Unknown'))
            if parsed_lower:
                props["lowerUlArray"] = json.dumps(parsed_lower)

    return data


def parse_altitude(alt_str, alt_type="Altitude", feature_name="Unknown"):
    formatted=alt_str
    # Process FL tokens: if FL (or fl/Fl) is found, replace patterns with numberFL STD, or warn if no number is found
    if re.search(r'\b[Ff][Ll]\s*\d', formatted):
        # Replace occurrences of FL followed by number (with optional space) with numberFL STD
        if re.search(r'\b[Ff][Ll]\s*(\d+)\b', formatted):
            formatted = re.sub(r'\b[Ff][Ll]\s*(\d+)\b', lambda m: f"{m.group(1)}FL STD", formatted)
            # print(f"{alt_str} transformed to {formatted}")
        else:
            print(f"[{alt_type}] Warning: FL found but no number after FL in: {formatted} in feature '{feature_name}'")

    # Replace any occurrence of standalone 'GND' with '0ft ASFC'
    formatted = re.sub(r"\bGND\b", "0ft GND", formatted)
    formatted = re.sub(r"\bSFC\b", "0ft GND", formatted)
    formatted = re.sub(r"\bASFC\b", "GND", formatted)
    formatted = re.sub(r"\bAMSL\b", "MSL", formatted)
    formatted = re.sub(r"\bUNL\b", "9999999ft MSL", formatted)

    tokens = formatted.split()
    # Merge tokens if a numeric token is immediately followed by an alphabetic token (e.g., '250' 'ft' -> '250ft')
    merged_tokens = []
    i = 0
    while i < len(tokens):
        if tokens[i].isdigit() and i+1 < len(tokens) and tokens[i+1].isalpha():
            merged_tokens.append(tokens[i] + tokens[i+1])
            i += 2
        else:
            merged_tokens.append(tokens[i])
            i += 1
    tokens = merged_tokens

    parsed = []
    if len(tokens) % 2 == 0:
        for i in range(0, len(tokens), 2):
            m = re.match(r"^(\d+)([a-zA-Z]+)$", tokens[i])
            # Check that the second token has no digits
            if m and not re.search(r"\d", tokens[i+1]):
                parsed.append({
                    "ulvalue": int(m.group(1)),
                    "ulunit": m.group(2),
                    "ulref": tokens[i+1]
                })
    else:
        print(f"Error: Not a valid altitude string in feature '{feature_name}', tokens: {tokens}, full: {alt_str}")
    return parsed


def main():
    # Open the input geojson file
    with open('airspace.geojson', 'r') as infile:
        data = json.load(infile)

    # Process the geojson data
    processed_data = process_geojson(data)

    # Count occurrences for icaoClass and type
    icao_counts = {}
    type_counts = {}
    for feature in processed_data.get('features', []):
        props = feature.get('properties', {})
        icao = props.get('icaoClass', 'None')
        ftype = props.get('type', 'None')
        icao_counts[icao] = icao_counts.get(icao, 0) + 1
        type_counts[ftype] = type_counts.get(ftype, 0) + 1

    # Nicely print the counts
    # print("\nProcessed GeoJSON Summary:")
    # print("-------------------------")
    # print("ICAO Class Counts:")
    # for k, v in sorted(icao_counts.items()):
    #     print(f"  {k}: {v}")
    
    # print("\nType Counts (Sorted by frequency):")
    # for k, v in sorted(type_counts.items(), key=lambda item: item[1], reverse=True):
    #     print(f"  {k}: {v}")
    
    # Print names of features that do not have a 'type'
    missing_names = []
    # for feature in processed_data.get('features', []):
    #     props = feature.get('properties', {})
    #     if 'type' not in props:
    #         missing_names.append(props.get('name', 'Unknown'))
    
    if missing_names:
        print("\nFeatures without a 'type':")
        for name in missing_names:
            print(f"  {name}")
    else:
        print("\nAll features have a 'type' property.")

    # Print the upperAltitude property for each feature
    # print("\nUpper Altitude for Each Feature:")
    # for feature in processed_data.get('features', []):
    #     props = feature.get('properties', {})
    #     print(f"  {props.get('upperAltitude', 'N/A')}")

    # Collect unique values from altitude arrays (ulvalue, ulunit, ulref)
    ulvalue_set = set()
    ulunit_set = set()
    ulref_set = set()

    for feature in processed_data.get('features', []):
        props = feature.get('properties', {})
        for key in ['upperUlArray']:
            if key in props:
                try:
                    alt_array = json.loads(props[key])
                    for item in alt_array:
                        ulvalue_set.add(item.get('ulvalue'))
                        ulunit_set.add(item.get('ulunit'))
                        ulref_set.add(item.get('ulref'))
                except Exception as e:
                    print(f"Error parsing {key}: {e}")

    # print("\nUnique ulvalue values:", sorted(list(ulvalue_set)))
    print("Unique ulunit values:", sorted(list(ulunit_set)))
    print("Unique ulref values:", sorted(list(ulref_set)))
    llvalue_set = set()
    llunit_set = set()
    llref_set = set()

    for feature in processed_data.get('features', []):
        props = feature.get('properties', {})
        for key in ['lowerUlArray']:
            if key in props:
                try:
                    alt_array = json.loads(props[key])
                    for item in alt_array:
                        llvalue_set.add(item.get('ulvalue'))
                        llunit_set.add(item.get('ulunit'))
                        llref_set.add(item.get('ulref'))
                        # if item.get('ulunit') == 'f':
                        #     print(f"Warning: {alt_array} {props.get('name', 'Unknown')}")
                except Exception as e:
                    print(f"Error parsing {key}: {e}")

    # print("\nUnique llvalue values:", sorted(list(llvalue_set)))
    print("Unique llunit values:", sorted(list(llunit_set)))
    print("Unique llref values:", sorted(list(llref_set)))

    # Write the processed data to a new file
    with open('airspace_processed.geojson', 'w') as outfile:
        json.dump(processed_data, outfile, indent=2)


if __name__ == '__main__':
    main()

# features from airspace.geojson
# feature = {
#     "type": "Feature",
#     "geometry": {
#         "type": "Polygon",
#         "coordinates": [polygon_points]
#     },
#     "properties": {
#         "name": current_name ,
#         "icaoClass": icao_class ,
#         "upperAltitude": upperAltitude,
#         "lowerAltitude": lowerAltitude,
#         "radio": radio,
#         "schedule": schedule,
#         "restrictions": restrictions,
#         "remarks": remarks
#     }
# }

#desired output properties
# export const ICAO_CLASS_MAPPING = {
#     0: "A",
#     1: "B",
#     2: "C",
#     3: "D",
#     4: "E",
#     5: "F",
#     6: "G",
#     8: "Other"
# }; 

# export const TYPE_MAPPING = {
#     0: "AWY",
#     1: "Restricted",
#     2: "Dangerous",
#     3: "Prohibited",
#     4: "CTR",
#     5: "TMZ",
#     6: "RMZ",
#     7: "TMA",
#     10: "FIR",
#     21: "gliding",
#     26: "CTA",
#     28: "Para/voltige",
#     29: "ZSM",
#     33: "SIV"
# };

# export const UNIT_MAPPING = { 
#     1: "ft", 
#     6: "FL" 
# };

# export const REFERENCE_DATUM_MAPPING = { 
#     0: "GND", 
#     1: "MSL", 
#     2: "1013" 
# };

# export const COLOR_MAPPING = {
#     "A": "rgb(255, 0, 0)",
#     "B": "rgb(255, 0, 0)",
#     "C": "rgb(0, 0, 255)",
#     "D": "rgb(0, 0, 255)",
#     "E": "rgb(0, 83, 0)",
#     "F": "rgb(0, 83, 0)",
#     "G": "rgb(0, 83, 0)",
#     "Prohibited": "rgb(255, 0, 0)",
#     "Restricted": "rgb(255, 0, 0)",
#     "Dangerous": "rgb(255, 0, 0)",
#     "ZSM": "rgb(255, 165, 0)",
#     "RMZ": "rgb(255, 165, 0)",
#     "TMZ": "rgb(128, 0, 128)",
#     "Para/voltige": "rgb(128, 0, 128)",
#     "SIV": "rgb(0, 160, 0)",
#     "FIR": "rgb(0, 0, 255)",
#     "gliding": "rgb(255, 255, 0)",
#     "other": "rgb(0, 0, 0)"
# }

# openAIP structure
# {
#   "_id": "str",
#   "createdBy": "str",
#   "createdAt": "str",
#   "updatedBy": "str",
#   "updatedAt": "str",
#   "name": "str",
#   "dataIngestion": "bool",
#   "type": "int",
#   "icaoClass": "int",
#   "activity": "int",
#   "onDemand": "bool",
#   "onRequest": "bool",
#   "byNotam": "bool",
#   "specialAgreement": "bool",
#   "requestCompliance": "bool",
#   "country": "str",
#   "upperLimit": {
#     "value": "int",
#     "unit": "int",
#     "referenceDatum": "int"
#   },
#   "lowerLimit": {
#     "value": "int",
#     "unit": "int",
#     "referenceDatum": "int"
#   },
#   "hoursOfOperation": {
#     "operatingHours": [
#       {
#         "dayOfWeek": "int",
#         "startTime": "str",
#         "endTime": "str",
#         "byNotam": "bool",
#         "sunrise": "bool",
#         "sunset": "bool",
#         "publicHolidaysExcluded": "bool"
#       }
#     ]
#   }
# }