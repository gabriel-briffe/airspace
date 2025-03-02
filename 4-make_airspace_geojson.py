import json
import re
from bs4 import BeautifulSoup
import math
from preprocess_border_file import read_border_geojson
# ===============================
# Regex Patterns
# ===============================

REGEX_ARC = r'arc\s+(anti-horaire|horaire)\s+de\s+([\d.]+)\s*(NM|m|km)\s+de\s+rayon\s+centré\s+sur\s+(\d{6}[NS])(?:\s*@\s*(\d{7}[EW]))?'
REGEX_CIRCLE = r'cercle\s+de\s+([\d.]+)\s*(NM|m|km)\s+de\s+rayon\s+centré\s+sur\s+(\d{6}[NS])(?:\s*@\s*(\d{7}[EW]))?'
REGEX_COORD_PAIR = r'\d{6,7}[NSEW]\s*@\s*\d{6,7}[NSEW]'
REGEX_COORD_SINGLE = r'\d{6,7}[NSEW]'

# ===============================
# Coordinate Conversion and Parsing Helper Functions
# ===============================

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
    # Use the centralized regex constant
    m = re.search(REGEX_ARC, text, re.IGNORECASE)
    if not m:
        return None
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
        return None
    lat_center = convert_coord(lat_str)
    lon_center = convert_coord(lon_str)
    # Convert radius in nautical miles to degrees (approximation)
    r_deg_lat = radius_nm / 60  # approx change in latitude
    r_deg_lon = r_deg_lat / math.cos(math.radians(lat_center))
    # Determine number of segments
    num_segments = max(12, int(radius_nm * 12))
    points = []
    for i in range(num_segments):
        angle_deg = 360 / num_segments * i
        angle_rad = math.radians(angle_deg)
        lon = lon_center + r_deg_lon * math.cos(angle_rad)
        lat = lat_center + r_deg_lat * math.sin(angle_rad)
        points.append([lon, lat])
    points.append(points[0])  # ensure polygon is closed
    if direction == 'anti-horaire':
        points = list(reversed(points))
    return points


def parse_circle_text(text):
    m = re.search(REGEX_CIRCLE, text, re.IGNORECASE)
    if not m:
        print(f"No match found for circle description: {text}")
        return None
    radius_value = float(m.group(1))
    unit = m.group(2).strip()
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
    r_deg_lat = radius_nm / 60
    r_deg_lon = r_deg_lat / math.cos(math.radians(lat_center))
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


def construct_arc(prev_pt, arc_text, next_pt):
    m = re.search(REGEX_ARC, arc_text, re.IGNORECASE)
    if not m:
        return None
    direction = m.group(1).lower()
    radius_value = float(m.group(2))
    unit = m.group(3).strip().lower()
    if unit == 'm':
        radius_nm = radius_value / 1852
    elif unit == 'km':
        radius_nm = radius_value / 1.852
    else:
        radius_nm = radius_value
    lat_str = m.group(4).strip()
    lon_str = m.group(5).strip()
    lat_center = convert_coord(lat_str)
    lon_center = convert_coord(lon_str)
    angular_radius = radius_nm * math.pi / 60 / 180
    lat_center_rad = math.radians(lat_center)
    lon_center_rad = math.radians(lon_center)

    def bearing_to_point(lat1, lon1, lat2, lon2):
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        dlon = lon2 - lon1
        y = math.sin(dlon) * math.cos(lat2)
        x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
        return math.atan2(y, x)

    start_bearing = bearing_to_point(lat_center, lon_center, prev_pt[0], prev_pt[1])
    end_bearing = bearing_to_point(lat_center, lon_center, next_pt[0], next_pt[1])
    if start_bearing < 0:
        start_bearing += 2 * math.pi
    if end_bearing < 0:
        end_bearing += 2 * math.pi
    delta_angle = end_bearing - start_bearing
    if delta_angle > 2 * math.pi:
        delta_angle -= 2 * math.pi
    elif delta_angle < -2 * math.pi:
        delta_angle += 2 * math.pi
    if direction == 'horaire':
        if delta_angle < 0:
            delta_angle += 2 * math.pi
    else:
        if delta_angle > 0:
            delta_angle -= 2 * math.pi
    num_segments = max(2, int(abs(delta_angle) / math.radians(5)))
    arc_points = []
    for i in range(num_segments + 1):
        t = i / num_segments
        if i == 0:
            continue
        elif i == num_segments:
            break
        else:
            bearing = start_bearing + t * delta_angle
            if bearing < 0:
                bearing += 2 * math.pi
            if bearing > 2 * math.pi:
                bearing -= 2 * math.pi
            lat_rad = math.asin(math.sin(lat_center_rad) * math.cos(angular_radius) +
                                math.cos(lat_center_rad) * math.sin(angular_radius) * math.cos(bearing))
            lon_rad = lon_center_rad + math.atan2(math.sin(bearing) * math.sin(angular_radius) * math.cos(lat_center_rad),
                                                  math.cos(angular_radius) - math.sin(lat_center_rad) * math.sin(lat_rad))
            lon_rad = (lon_rad + 3 * math.pi) % (2 * math.pi) - math.pi
            lat = math.degrees(lat_rad)
            lon = math.degrees(lon_rad)
            arc_points.append([lon, lat])
    return arc_points


# New helper function to process an arc token
# Expects the current token, previous token, and next token
# Returns a list of coordinates if successful, else an empty list

def process_arc_token(token, prev_token, next_token):
    lower_token = token.lower()
    if "arc horaire" in lower_token or "arc anti-horaire" in lower_token:
        if "arc" in prev_token.lower():
            print(f"Previous token is also an arc: {prev_token}")
        if "arc" in next_token.lower():
            print(f"Next token is also an arc: {next_token}")
        m_prev = re.search(REGEX_COORD_PAIR, prev_token, re.IGNORECASE)
        m_next = re.search(REGEX_COORD_PAIR, next_token, re.IGNORECASE)
        if m_prev and m_next:
            # Extract first coordinate pair from the match using raw f-string
            prev_match = re.search(rf'({REGEX_COORD_SINGLE})\s*@\s*({REGEX_COORD_SINGLE})', prev_token, re.IGNORECASE)
            next_match = re.search(rf'({REGEX_COORD_SINGLE})\s*@\s*({REGEX_COORD_SINGLE})', next_token, re.IGNORECASE)
            if prev_match and next_match:
                prev_pt = [convert_coord(prev_match.group(1)), convert_coord(prev_match.group(2))]
                next_pt = [convert_coord(next_match.group(1)), convert_coord(next_match.group(2))]
                arc_points = construct_arc(prev_pt, token, next_pt)
                if arc_points is not None and len(arc_points) > 1:
                    return arc_points
        else:
            print(f"Arc token at chain end: {token}")
    return []


# New helper function to process a circle token
# Returns a list of coordinates if successful, else an empty list

def process_circle_token(token):
    if "cercle de" in token.lower() and "centré sur" in token.lower():
        circle_points = parse_circle_text(token)
        if circle_points is not None:
            return circle_points[:-1]
        else:
            print(f"Circle processing failed for token: {token}")
    return []


# New helper function to process a plain coordinate token
# Returns a list of coordinates (usually a single pair or multiple pairs) if successful, else an empty list

def process_plain_token(token):
    lower_token = token.lower()
    coordinates = []
    pairs = re.findall(REGEX_COORD_PAIR, token, re.IGNORECASE)
    if pairs and len(pairs) > 1:
        for pair in pairs:
            parts = [p.strip() for p in pair.split("@")]
            if len(parts) != 2:
                print(f"Invalid coordinate pair format in pair: {pair}")
                continue
            lat_str, lon_str = parts[0], parts[1]
            if not (re.fullmatch(REGEX_COORD_SINGLE, lat_str) and re.fullmatch(REGEX_COORD_SINGLE, lon_str)):
                m_lat = re.search(REGEX_COORD_SINGLE, lat_str)
                m_lon = re.search(REGEX_COORD_SINGLE, lon_str)
                if m_lat and m_lon:
                    lat_str = m_lat.group(0)
                    lon_str = m_lon.group(0)
                else:
                    print(f"Invalid coordinate values in pair: {pair}")
                    continue
            lat = convert_coord(lat_str)
            lon = convert_coord(lon_str)
            coordinates.append([lon, lat])
        return coordinates
    else:
        parts = [p.strip() for p in token.split("@")]
        if len(parts) != 2:
            if not any(x in token for x in ["Frontière", "atlantique", "Côte", "Parc", "Axe"]):
                print(f"Invalid coordinate pair format: {token}")
            return []
        lat_str, lon_str = parts[0], parts[1]
        if not (re.fullmatch(REGEX_COORD_SINGLE, lat_str) and re.fullmatch(REGEX_COORD_SINGLE, lon_str)):
            m_lat = re.search(REGEX_COORD_SINGLE, lat_str)
            m_lon = re.search(REGEX_COORD_SINGLE, lon_str)
            if m_lat and m_lon:
                lat_str = m_lat.group(0)
                lon_str = m_lon.group(0)
            else:
                print(f"Invalid coordinate values: {token}")
                return []
        lat = convert_coord(lat_str)
        lon = convert_coord(lon_str)
        return [[lon, lat]]


def process_france_token(token,border_coords):
    # TODO: process france token
    pass


# Refactored process_coordinates using the new helper functions

def process_coordinates(all_coords,border_coords):
    """
    Expects all_coords to be a list of coordinate tokens.
    Processes each token using arc, circle, or plain coordinate logic.
    Returns a list of points forming a closed polygon, or None if invalid.
    """
    final_points = []
    i = 0
    total = len(all_coords)
    while i < total:
        token = all_coords[i]
        lower_token = token.lower()
        points = []
        if "arc horaire" in lower_token or "arc anti-horaire" in lower_token:
            prev_index = i - 1 if i != 0 else total - 1
            next_index = i + 1 if i != total - 1 else 0
            prev_token = all_coords[prev_index]
            next_token = all_coords[next_index]
            points = process_arc_token(token, prev_token, next_token)
        elif "cercle de" in lower_token and "centré sur" in lower_token:
            points = process_circle_token(token)
        elif "frontière" in lower_token or "atlantique" in lower_token or "côte" in lower_token:
            points = process_france_token(token,border_coords)
        elif "parc" in lower_token or "axe" in lower_token:
            # print(f"need to process park and axe")
            pass
        else:
            points = process_plain_token(token)
        if points:
            final_points.extend(points)
        i += 1

    if not final_points or len(final_points) < 2:
        return None
    if final_points[0] != final_points[-1]:
        final_points.append(final_points[0])
    return final_points




def create_geojson_feature(name, polygon_points, icao_class, upperAltitude, lowerAltitude, radio, schedule, restrictions, remarks):
    return {
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [polygon_points]
        },
        "properties": {
            "name": name,
            "icaoClass": icao_class,
            "upperAltitude": upperAltitude,
            "lowerAltitude": lowerAltitude,
            "radio": radio,
            "schedule": schedule,
            "restrictions": restrictions,
            "remarks": remarks
        }
    }


def main(input_file, geojson_file,border_file):
    # Parse the cleaned HTML file
    with open(input_file, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')

    features = []
    border_coords = read_border_geojson(border_file)

    # For every table container, process rows in document order to associate parsed rows with the previous parsed name row
    for container_index, container in enumerate(soup.select('.table-container')):
        current_name = None
        for tr in container.find_all('tr'):
            classes = tr.get('class', [])
            if 'parsed-name' in classes:
                td = tr.find('td')
                if td:
                    current_name = td.get_text(strip=True)
            elif 'parsed-row' in classes:
                icao_class = ""
                upperAltitude = ""
                lowerAltitude = ""
                radio = ""
                schedule = ""
                restrictions = ""
                remarks = ""

                tds = tr.find_all('td')
                if not tds:
                    continue
                cell_text = tds[0].get_text(strip=True)

                if container_index in [0, 1, 2, 3, 12]:
                    icao_class = tds[1].get_text(strip=True)
                    altitude_text = tds[2].get_text(strip=True)
                    alt_parts = altitude_text.split("------------")
                    upperAltitude = alt_parts[0].strip()
                    lowerAltitude = alt_parts[1].strip()
                    radio = tds[3].get_text(strip=True)
                    remarks = tds[4].get_text(strip=True)
                elif container_index == 4:
                    altitude_text = tds[1].get_text(strip=True)
                    alt_parts = altitude_text.split("------------")
                    upperAltitude = alt_parts[0].strip()
                    lowerAltitude = alt_parts[1].strip()
                    radio = tds[2].get_text(strip=True)
                    remarks = tds[3].get_text(strip=True)
                elif container_index in [5, 6]:
                    altitude_text = tds[1].get_text(strip=True)
                    alt_parts = altitude_text.split("------------")
                    upperAltitude = alt_parts[0].strip()
                    lowerAltitude = alt_parts[1].strip()
                    schedule = tds[2].get_text(strip=True)
                    restrictions = tds[3].get_text(strip=True)
                    remarks = tds[4].get_text(strip=True)
                elif container_index == 7:
                    altitude_text = tds[1].get_text(strip=True)
                    alt_parts = altitude_text.split("------------")
                    upperAltitude = alt_parts[0].strip()
                    lowerAltitude = alt_parts[1].strip()
                    restrictions = tds[2].get_text(strip=True)
                elif container_index in [8, 9]:
                    altitude_text = tds[1].get_text(strip=True)
                    alt_parts = altitude_text.split("------------")
                    upperAltitude = alt_parts[0].strip()
                    lowerAltitude = alt_parts[1].strip()
                    schedule = tds[2].get_text(strip=True)
                    restrictions = tds[3].get_text(strip=True)
                    remarks = tds[4].get_text(strip=True)
                elif container_index == 10:
                    altitude_text = tds[1].get_text(strip=True)
                    alt_parts = altitude_text.split("------------")
                    upperAltitude = alt_parts[0].strip()
                    lowerAltitude = alt_parts[1].strip()
                    remarks = tds[2].get_text(strip=True)
                elif container_index == 11:
                    upperAltitude = tds[1].get_text(strip=True)
                    lowerAltitude = "GND"
                    restrictions = tds[2].get_text(strip=True)
                    remarks = tds[3].get_text(strip=True)

                try:
                    clean_text = re.sub(r'[\x00-\x1F]+', ' ', cell_text)
                    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
                    coords = json.loads(clean_text)
                except Exception as e:
                    print(f"Error parsing coordinates: {e}")
                    print(f"Cell text: {cell_text}")
                    continue

                if current_name and (any(x in current_name.lower() for x in [" para ", " voltige ", " treuillage ", " aéromodélisme "])) \
                    and isinstance(coords, list) and len(coords) == 1:
                    if 'cercle de' in coords[0].lower() and 'de rayon centré sur' in coords[0].lower():
                        pass
                    elif any(x in current_name.lower() for x in [" para"]):
                        match_list = re.findall(REGEX_COORD_PAIR, coords[0], re.IGNORECASE)
                        if len(match_list) == 1:
                            coords = [f"cercle de 3 NM de rayon centré sur {match_list[0]}"]
                    elif any(x in current_name.lower() for x in [" treuillage"]):
                        match_list = re.findall(REGEX_COORD_PAIR, coords[0], re.IGNORECASE)
                        if len(match_list) == 1:
                            coords = [f"cercle de 600m de rayon centré sur {match_list[0]}"]
                    elif any(x in current_name.lower() for x in [" aéromodélisme"]):
                        match_list = re.findall(REGEX_COORD_PAIR, coords[0], re.IGNORECASE)
                        if len(match_list) == 1:
                            coords = [f"cercle de 600m de rayon centré sur {match_list[0]}"]
                    else:
                        continue

                polygon_points = process_coordinates(coords,border_coords)
                if polygon_points is None:
                    continue

                # Create the GeoJSON feature using the new function
                feature = create_geojson_feature(current_name, polygon_points, icao_class, upperAltitude, lowerAltitude, radio, schedule, restrictions, remarks)
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
    



if __name__ == '__main__':
    # Input and output file paths
    input_file = 'eaip_selected_tables_stage1_cleaned.html'
    geojson_file = 'airspace.geojson'
    border_file = 'France.geojson'

    main(input_file, geojson_file,border_file)


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
