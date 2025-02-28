import json
import re
from bs4 import BeautifulSoup
import math

# Input and output file paths
input_file = 'eaip_selected_tables_stage1_cleaned.html'
geojson_file = 'airspace.geojson'

# Helper function to convert coordinate string to decimal degrees
# Assumes coordinate string is in format: either 6 or 7 digits followed by a hemisphere letter
# For lat (N/S), if length of numeric part is 6 then degrees = first 2 digits, else if 7 then first 3 digits
# Similarly, for lon (E/W), numeric part should be 7 (typically) but we'll use the same logic


def convert_coord(coord_str):
    # Remove any spaces
    coord_str = coord_str.strip()
    num_part = coord_str[:-1]
    hemi = coord_str[-1]
    # Determine split based on length of numeric part
    if len(num_part) == 6:
        # For latitude typically
        deg = int(num_part[:2])
        minute = int(num_part[2:4])
        sec = int(num_part[4:6])
    elif len(num_part) == 7:
        # For longitude typically
        deg = int(num_part[:3])
        minute = int(num_part[3:5])
        sec = int(num_part[5:7])
    else:
        # Fallback, try first 2 digits
        deg = int(num_part[:2])
        minute = int(num_part[2:4])
        sec = int(num_part[4:6])
    decimal = deg + minute/60 + sec/3600
    if hemi in ('S', 'W'):
        decimal = -decimal
    return decimal

# New function to parse textual arc descriptions and return polygon coordinates


def parse_arc_text(text):
    # print(text)
    # Matches patterns like: arc anti-horaire de 3 NM de rayon centré sur 461334N, 0012345E or with meters
    m = re.search(
        r'arc\s+(anti-horaire|horaire)\s+de\s+([\d.]+)\s*(NM|m|km)\s+de\s+rayon\s+centré\s+sur\s+(\d{6,7}[NS])(?:\s*,\s*(\d{6,7}[EW]))?', text, re.IGNORECASE)
    if not m:
        return None
    # print(m.groups())
    direction = m.group(1).lower()
    radius_value = float(m.group(2))
    unit = m.group(3).strip()
    # Convert to nautical miles if unit is meters
    if unit.lower() == 'm':
        radius_nm = radius_value / 1852
    elif unit.lower() == 'km':
        radius_nm = radius_value * 0.539957
    else:
        radius_nm = radius_value
    lat_str = m.group(4).strip()
    lon_str = m.group(5).strip() if m.group(5) else None
    if not lon_str:
        # print(f"Missing longitude in arc description: {text}")
        return None
    lat_center = convert_coord(lat_str)
    lon_center = convert_coord(lon_str)
    # Convert radius in nautical miles to degrees (approximation)
    r_deg_lat = radius_nm / 60  # approx change in latitude
    r_deg_lon = r_deg_lat / math.cos(math.radians(lat_center))
    # Adjust num_segments based on radius: num_segments = max(12, int(radius_nm * 12))
    num_segments = max(12, int(radius_nm * 12))
    points = []
    for i in range(num_segments):
        angle_deg = 360 / num_segments * i
        angle_rad = math.radians(angle_deg)
        lon = lon_center + r_deg_lon * math.cos(angle_rad)
        lat = lat_center + r_deg_lat * math.sin(angle_rad)
        points.append([lon, lat])
    points.append(points[0])  # ensure polygon is closed
    if direction == 'horaire':
        points = list(reversed(points))
    return points


def parse_circle_text(text):
    # Matches patterns like: cercle de 500 m de rayon centré sur 433305N, 0061234E
    # or without a longitude
    # print(f"Parsing circle text: {text}")
    m = re.search(
        r'cercle\s+de\s+([\d.]+)\s*(NM|m|km)\s+de\s+rayon\s+centré\s+sur\s+(\d{6,7}[NS])(?:\s*,\s*(\d{6,7}[EW]))?', text, re.IGNORECASE)
    # print(f"Match: {m}")
    if not m:
        print(f"No match found for circle description: {text}")
        return None
    radius_value = float(m.group(1))
    unit = m.group(2).strip()
    # Convert to nautical miles if needed
    if unit.lower() == 'm':
        radius_nm = radius_value / 1852
    elif unit.lower() == 'km':
        radius_nm = radius_value * 0.539957
    else:
        radius_nm = radius_value
    lat_str = m.group(3).strip()
    lon_str = m.group(4).strip() if m.group(4) else None
    if not lon_str:
        print(f"Missing longitude in circle description: {text}")
        return None
    lat_center = convert_coord(lat_str)
    lon_center = convert_coord(lon_str)
    # Convert radius in nautical miles to degrees (approximation)
    r_deg_lat = radius_nm / 60
    r_deg_lon = r_deg_lat / math.cos(math.radians(lat_center))
    # Adjust number of segments based on radius
    num_segments = max(12, int(radius_nm * 12))
    points = []
    for i in range(num_segments):
        angle_deg = 360 / num_segments * i
        angle_rad = math.radians(angle_deg)
        lon = lon_center + r_deg_lon * math.cos(angle_rad)
        lat = lat_center + r_deg_lat * math.sin(angle_rad)
        points.append([lon, lat])
    points.append(points[0])  # ensure polygon is closed
    return points

# Function to validate and process coordinate array
# Expects coords to be a list of strings
# Returns a list of [lon, lat] pairs if valid, else None


def process_coordinates(all_coords):
    """
    Simplified process_coordinates: expects all_coords to be a list of strings in the format "lat , lon".
    For each string (token), if it contains 'arc' or 'cercle', the corresponding parser is called to generate coordinates.
    Otherwise, the string is treated as a plain coordinate pair.
    By 'token' we mean each individual string element from the input list, which should be a coordinate pair like "485337N , 0012345E".
    """
    final_points = []

    for token in all_coords:
        lower_token = token.lower()

        # if "arc" in lower_token or "cercle" in lower_token: print(token)
        # Check for arc or cercle keywords
        if "arc horaire" in lower_token or "arc anti-horaire" in lower_token:
            arc_points = parse_arc_text(token)
            if arc_points is not None:
                final_points.extend(arc_points)
            else:
                print(f"Arc processing failed for token: {token}")
        elif "cercle de" in lower_token and "centré sur" in lower_token:
            circle_points = parse_circle_text(token)
            if circle_points is not None:
                final_points.extend(circle_points[:-1])
            else:
                print(f"Circle processing failed for token: {token}")
        else:
            # Treat token as plain "lat , lon" pair
            parts = [p.strip() for p in token.split(",")]
            if len(parts) != 2:
                if not "Frontière" in token and not "atlantique" in token and not "Côte" in token and not "Parc" in token and not "Axe" in token: print(f"Invalid coordinate pair format: {all_coords}")
                continue
            lat_str, lon_str = parts[0], parts[1]

            # Check if the parts exactly match the expected coordinate pattern
            if not (re.fullmatch(r'\d{6,7}[NSEW]', lat_str) and re.fullmatch(r'\d{6,7}[NSEW]', lon_str)):
                # Attempt to extract valid coordinate substrings from the parts
                m_lat = re.search(r'(\d{6,7}[NSEW])', lat_str)
                m_lon = re.search(r'(\d{6,7}[NSEW])', lon_str)
                if m_lat and m_lon:
                    # print(f"Warning")
                    # print(f"Warning: coordinate value in token '{token}' contained extra text; extracting coordinates.")
                    lat_str = m_lat.group(1)
                    lon_str = m_lon.group(1)
                else:
                    print(f"Invalid coordinate values: {token}")
                    continue

            lat = convert_coord(lat_str)
            lon = convert_coord(lon_str)
            final_points.append([lon, lat])

    if not final_points or len(final_points) < 2:
        return None

    # Ensure the polygon is closed
    if final_points[0] != final_points[-1]:
        final_points.append(final_points[0])
    return final_points


# Parse the cleaned HTML file
with open(input_file, 'r', encoding='utf-8') as f:
    soup = BeautifulSoup(f, 'html.parser')

features = []

# For every table container, process rows in document order to associate parsed rows with the previous parsed name row
for container in soup.select('.table-container'):
    current_name = None
    # Loop over all rows in order within the container
    for tr in container.find_all('tr'):
        classes = tr.get('class', [])
        if 'parsed-name' in classes:
            # Update current name using the text from the first cell
            td = tr.find('td')
            if td:
                current_name = td.get_text(strip=True)
        elif 'parsed-row' in classes:
            # Get the first <td> which should contain the coordinates as a JSON array string
            td = tr.find('td')
            if not td:
                continue
            cell_text = td.get_text(strip=True)
            try:
                # Expecting cell_text like ["485337N , 0014747E", "485337N , 0014747E", ...] 
                coords = json.loads(cell_text)
                # if current_name == "6902 voltige MAZET de ROMANIN (13)" and coords == ["434548N , 0045617E Axe Nord-Sud de 1 NM de longueur centré sur sur 434548N", "0045617E"]:
                #     coords = ["434548N , 0045617E Axe Nord-Sud de 1 NM de longueur centré sur sur 434548N , 0045617E"]
                # # If coords is a list with a single string that contains commas, split it
                # if isinstance(coords, list) and len(coords) == 1 and ',' in coords[0]:
                #     coords = [c.strip() for c in coords[0].split(",")]
            except Exception as e:
                print(f"Error parsing coordinates: {e}")
                print(f"Cell text: {cell_text}")
                # Skip rows with non-JSON coordinate text
                continue
            # Process only if valid
            polygon_points = process_coordinates(coords)
            if polygon_points is None:
                continue
            # Create a GeoJSON feature with property "name" from current_name
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [polygon_points]
                },
                "properties": {
                    "name": current_name if current_name else ""
                }
            }
            features.append(feature)

# Create FeatureCollection
geojson = {
    "type": "FeatureCollection",
    "features": features
}

# Write to geojson file
with open(geojson_file, 'w', encoding='utf-8') as f:
    json.dump(geojson, f, indent=2)

print(f"Saved {len(features)} features to '{geojson_file}'")


# Invalid coordinate pair format: ['502500N , 0022400E Verticale N41 au Sud-Est de la commune axe 080/260 de 1km de part et dautre du point 502500N,0022400E']
# Invalid coordinate pair format: ['500450N , 0031154E Verticale N44, axe 010/190 situé RDL 214/4.2 NM AD CAMBRAI NIERGNIES Distance 1 km entre les points 500450N,0031154E et 500522N,0031204E']
# Invalid coordinate pair format: ['484325N , 0061223E 1000 mètres de part et dautre de lARP, orienté 082/262']
# Invalid coordinate pair format: ['480840N , 0072130E Axé sur voie ferrée de Colmar à Sélestat entre 480925N, 0072135E et 48 0755 N, 00721 30E.']
# Invalid coordinate pair format: ['491043N , 0021913E Axe orienté 050/230 de 1200m centré sur 491043N', '0021913E (extrémité nord piste désaffectée 05/23)']
# Invalid coordinate pair format: ['482252N , 0020426E Rectangle de 2000x1000 m orienté sur RWY 06/24 revêtue et centré sur lARP (482252N, 0020426E)']
# Invalid coordinate pair format: ['493800N , 0004300E Rectangle de 1700x1000m orienté 086/266 et centré sur 493800N,0004300E']
# Invalid coordinate pair format: ['480340N , 0044220W', '480440N , 0043100W', '480340N , 0044220W Route départementale 7, entre les points 480340N, 0044220W et 480440N et 0043100W Longueur de laxe: 14000m.']
# Invalid coordinate pair format: ['481548N , 0042000W', '481610N , 0041535W', '481548N , 0042000W Route départementale 791, entre les points 481548N, 0042000W et 481610N, 0041535W; Longueur de laxe: 5000m.']
# Invalid coordinate pair format: ['483934N , 0034737W 3 km le long de la route D46 entre les points 484020N, 0034715W et 483848N, 0034758W']
# Invalid coordinate pair format: ['484009N , 0034515W 3.3 km le long de la route D78 entre les points 484041N, 0034621W et 483937N, 0034408W']
# Invalid coordinate pair format: ['463657N , 0010320E Rectangle de 1500x1000m orienté 172/352 et centré sur 463657N, 0010320E']
# Invalid coordinate pair format: ['442950N , 0005212E Axe de 2000m orienté 110/290 centré sur 442950N', '0005212E']
# Invalid coordinate pair format: ['432206N , 0002544W Axe centré sur 432206N', '0002544W orienté 125/305']
# Invalid coordinate pair format: ['443049N , 0003758E Axe de 2000m orienté 120/300 centré sur 443049N', '0003758E']
# Invalid coordinate pair format: ['442708N , 0004157E Axe de 2000m orienté 150/330 centré sur 442708N', '0004157E']
# Invalid coordinate pair format: ['442957N , 0001201E Axe centré sur 442957N', '0001201E orienté 110/290']
# Invalid coordinate pair format: ['451151N , 0004855E Axe centré sur 451151N', '0004855E orienté 110/290']
# Invalid coordinate pair format: ['434548N , 0045617E Axe Nord-Sud de 1 NM de longueur centré sur sur 434548N', '0045617E']
# Invalid coordinate pair format: ['445400N , 0001930W 445400N,0001930W limitée à lEst par la voie ferrée BORDEAUX-PARIS.']
# Invalid coordinate pair format: ['452047N , 0050019E RDL 265/13,9 NM de lARP de Grenoble Alpes Isère LFLS']
# Invalid coordinate pair format: ['485515N , 0031730E ALT 190 m, 067/12 NM VOR CLM']
# Invalid coordinate pair format: ['481600N , 0023500E ALT 115 m, 062/14.4 NM VOR PTV']