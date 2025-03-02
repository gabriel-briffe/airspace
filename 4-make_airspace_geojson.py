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
REGEX_COORD_PAIR = r'\d{6}[NSEW]\s*@\s*\d{7}[NSEW]'
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
def format_dms(value, is_latitude):
    """Convert a decimal degree value to a DMS string.
    For latitude, format is DDMMSS[NS] (e.g., 474600N).
    For longitude, format is DDDMMSS[EW] (e.g., 0073200E).
    """
    abs_val = abs(value)
    deg = int(abs_val)
    rem = (abs_val - deg) * 60
    minutes = int(rem)
    seconds = int(round((rem - minutes) * 60))
    # Handle case where rounding seconds results in 60
    if seconds == 60:
        seconds = 0
        minutes += 1
    if minutes == 60:
        minutes = 0
        deg += 1
    if is_latitude:
        # For latitude, degrees should be 2 digits
        hem = 'N' if value >= 0 else 'S'
        return f"{deg:02d}{minutes:02d}{seconds:02d}{hem}"
    else:
        # For longitude, degrees should be 3 digits
        hem = 'E' if value >= 0 else 'W'
        return f"{deg:03d}{minutes:02d}{seconds:02d}{hem}"
# New function to parse textual arc descriptions and return polygon coordinates


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
# Returns a tuple (points, complete) where points is a list of coordinates if successful, else an empty list
# and complete is a boolean indicating whether the process was successful

def process_arc_token(token, prev_token, next_token):
    lower_token = token.lower()
    # Default return is an empty list with failure flag
    if "arc horaire" in lower_token or "arc anti-horaire" in lower_token:
        if "arc" in prev_token.lower():
            print(f"Previous token is also an arc: {prev_token}")
        if "arc" in next_token.lower():
            print(f"Next token is also an arc: {next_token}")
        m_prev = re.search(REGEX_COORD_PAIR, prev_token, re.IGNORECASE)
        m_next = re.search(REGEX_COORD_PAIR, next_token, re.IGNORECASE)
        if m_prev and m_next:
            # Extract the first coordinate pair from each token
            prev_match = re.search(rf'({REGEX_COORD_SINGLE})\s*@\s*({REGEX_COORD_SINGLE})', prev_token, re.IGNORECASE)
            next_match = re.search(rf'({REGEX_COORD_SINGLE})\s*@\s*({REGEX_COORD_SINGLE})', next_token, re.IGNORECASE)
            if prev_match and next_match:
                try:
                    prev_pt = [convert_coord(prev_match.group(1)), convert_coord(prev_match.group(2))]
                    next_pt = [convert_coord(next_match.group(1)), convert_coord(next_match.group(2))]
                except Exception as e:
                    print(f"Error converting coordinates for arc token: {e}")
                    return ([], False)
                arc_points = construct_arc(prev_pt, token, next_pt)
                if arc_points is not None and len(arc_points) > 1:
                    return (arc_points, True)
        else:
            print(f"Arc token at chain end: {token}")
    return ([], False)


# New helper function to process a circle token
# Returns a tuple (points, complete) where points is a list of coordinates if successful, else an empty list
# and complete is a boolean indicating whether the process was successful

def process_circle_token(token):
    if "cercle de" in token.lower() and "centré sur" in token.lower():
        circle_points = parse_circle_text(token)
        if circle_points is not None:
            # Remove the duplicate closing coordinate and report success
            return (circle_points[:-1], True)
        else:
            print(f"Circle processing failed for token: {token}")
            return ([], False)
    return ([], False)


# New helper function to process a plain coordinate token
# Returns a list of coordinates (usually a single pair or multiple pairs) if successful, else an empty list
def get_coordinates(token):
    return re.findall(REGEX_COORD_PAIR, token, re.IGNORECASE)

def get_lonLat  (token):
    pairs = get_coordinates(token)
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
            return [lon, lat]
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

def substract_lonLat(text):
    m = re.compile(REGEX_COORD_PAIR).search(text)
    if m:
        extracted = m.group(0)
        remaining_text = text.replace(extracted, '').strip()
        return extracted,remaining_text
    else:
        return None,text

def is_pure_lonLat(token):
    lonLat, rest = substract_lonLat(token)
    return lonLat and not rest

def split_twin_tokens(token):
    # lower_token = token.lower()
    coordinates = []
    pairs = get_coordinates(token)
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

def make_triplet(token,prev_token,next_token):
    return {
        "token": token,
        "prev_token": prev_token,
        "next_token": next_token
    }

def france_only(triplet):
    if "frontière franco-" in triplet["token"].lower():
        return True
    else:
        return False

def get_shortest_path_for_triplet(triplet, border_coords):
    """For a given triplet with 'prev_token' and 'next_token' in 'lat@lon' format,
    find the closest points in border_coords and return the shortest path between them
    as a list of coordinate pairs [lon, lat].
    border_coords is a list of [lon, lat] pairs.
    """
    # Convert triplet beginning and end to [lon, lat] using convert_coord
    try:
        b_lat_str, b_lon_str = triplet["prev_token"].split('@')
        b_lat = convert_coord(b_lat_str)
        b_lon = convert_coord(b_lon_str)
        triplet_begin = (b_lon, b_lat)  # border_coords order
    except Exception as e:
        return [], False
    try:
        e_lat_str, e_lon_str = triplet["next_token"].split('@')
        e_lat = convert_coord(e_lat_str)
        e_lon = convert_coord(e_lon_str)
        triplet_end = (e_lon, e_lat)  # border_coords order
    except Exception as e:
        return [], False
    
    def find_closest_index(pt, coords):
        best_idx = None
        best_dist = None
        for idx, coord in enumerate(coords):
            dist = (pt[0] - coord[0])**2 + (pt[1] - coord[1])**2
            if best_dist is None or dist < best_dist:
                best_dist = dist
                best_idx = idx
        return best_idx
    
    i_begin = find_closest_index(triplet_begin, border_coords)
    i_end = find_closest_index(triplet_end, border_coords)
    if i_begin is None or i_end is None:
        print(f"[DEBUG] No closest index found for triplet {triplet['token']}")
        return [], False
    
    # print(triplet["prev_token"],triplet["next_token"])
    # print(border_coords[i_begin],border_coords[i_end])
    # print(i_begin,i_end)
    
    def circular_path(i, j, coords):
        if i <= j:
            return coords[i:j+1]
        else:
            return coords[i:] + coords[:j+1]
    
    path1 = circular_path(i_begin, i_end, border_coords)
    path2 = circular_path(i_end, i_begin, border_coords)[::-1]  # reverse to go from begin to end
    
    def path_length(path):
        total = 0.0
        for k in range(len(path) - 1):
            dx = path[k+1][0] - path[k][0]
            dy = path[k+1][1] - path[k][1]
            total += (dx*dx + dy*dy)**0.5
        return total
    
    length1 = path_length(path1)
    length2 = path_length(path2)
    chosen_path = path1 if length1 <= length2 else path2
    
    if len(chosen_path) == 0:
        return [], False
    return chosen_path, True

def process_france_token(token,prev_token,next_token,border_coords):
    points=[]
    # print(f"[DEBUG] Processing France token: {token}")
    triplet = make_triplet(token,prev_token,next_token)
    if france_only(triplet):
        # print(f"[DEBUG] Processing France token: {token}")
        if is_pure_lonLat(prev_token) and is_pure_lonLat(next_token):
            points,success = get_shortest_path_for_triplet(triplet,border_coords)
            # print(len(points))
            if len(points) == 0: print(f"[WARN] No points found for triplet: {triplet}")
            return points,success
        else:
            return points,False
    return [], False

# Refactored process_coordinates using the new helper functions

def process_coordinates(name,all_coords,border_coords):
    """
    Expects all_coords to be a list of coordinate tokens.
    Processes each token using arc, circle, or plain coordinate logic.
    Returns a list of points forming a closed polygon, or None if invalid.
    """
    final_points = []
    had_missing = False
    i = 0
    total = len(all_coords)

    if name and (any(x in name.lower() for x in [" para ", " voltige ", " treuillage ", " aéromodélisme "])) \
        and isinstance(all_coords, list) and total == 1:
        if 'cercle de' in all_coords[0].lower() and 'de rayon centré sur' in all_coords[0].lower():
            pass
        elif any(x in name.lower() for x in [" para"]):
            match_list = re.findall(REGEX_COORD_PAIR, all_coords[0], re.IGNORECASE)
            if len(match_list) == 1:
                all_coords = [f"cercle de 3 NM de rayon centré sur {match_list[0]}"]
        elif any(x in name.lower() for x in [" treuillage"]):
            match_list = re.findall(REGEX_COORD_PAIR, all_coords[0], re.IGNORECASE)
            if len(match_list) == 1:
                all_coords = [f"cercle de 600m de rayon centré sur {match_list[0]}"]
        elif any(x in name.lower() for x in [" aéromodélisme"]):
            match_list = re.findall(REGEX_COORD_PAIR, all_coords[0], re.IGNORECASE)
            if len(match_list) == 1:
                all_coords = [f"cercle de 600m de rayon centré sur {match_list[0]}"]
        else:
            # case not para treuillage aéromodélisme -> voltige and not cercle and only one token
            return ([], False)



    while i < total:
        token = all_coords[i]
        token_points = []
        prev_index = i - 1 if i != 0 else total - 1
        next_index = i + 1 if i != total - 1 else 0
        prev_token = all_coords[prev_index]
        next_token = all_coords[next_index]
        if "arc horaire" in token.lower() or "arc anti-horaire" in token.lower():
            token_points, complete = process_arc_token(token, prev_token, next_token)
            if not complete: 
                had_missing = True
                # print(f"[WARN] Unprocessed item: {name} - {token}")
        elif "cercle de" in token.lower() and "centré sur" in token.lower():
            token_points, complete = process_circle_token(token)
            if not complete: 
                had_missing = True
                # print(f"[WARN] Unprocessed item: {name} - {token}")
        elif "frontière" in token.lower():
            token_points, complete = process_france_token(token, prev_token, next_token, border_coords)
            if not complete:
                had_missing = True
                # print(f"[WARN] Unprocessed item: {name} - {token}")
        elif "parc" in token.lower() or "axe" in token.lower() or "côte" in token.lower() or "atlantique" in token.lower():
            had_missing = True
        else:
            token_points = split_twin_tokens(token)
            if len(token_points) == 0:
                had_missing = True
                # print(f"[WARN] token with no latLon: {token}")
        if token_points:
            final_points.extend(token_points)
        i += 1
    if final_points[0] != final_points[-1]:
        final_points.append(final_points[0])
    return (final_points, had_missing)




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
def valid_ring(ring):
    """Check if ring is a valid linear ring as defined by GeoJSON:
    It has at least four coordinate pairs
    The first and last coordinate are equal
    Each coordinate is a list/tuple of two numbers
    """
    if not isinstance(ring, (list, tuple)) or len(ring) < 4:
        print(f"ring not valid: format")
        return False
    if ring[0] != ring[-1]:
        print(f"ring not closed")
        # Automatically close the ring if needed; alternatively, return False
        return False
    for pt in ring:
        if not (isinstance(pt, (list, tuple)) and len(pt) == 2 and all(isinstance(v, (int, float)) for v in pt)):
            print(pt,ring)
            print(f"ring not valid: coords format")
            return False
    return True

def main(input_file, geojson_file,border_file):
    # Parse the cleaned HTML file
    with open(input_file, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')

    features = []
    airspaces = 0
    border_coords = read_border_geojson(border_file)
    empty_airspaces = 0
    incomplete_airspaces = 0
    skipped_airspaces = 0
    empty_coords = 0
    points=0
    segments=0
    not_valid_rings = 0
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
                airspaces += 1
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

                if len(coords) == 0:
                    empty_airspaces += 1
                    continue
                polygon_points, had_missing = process_coordinates(current_name, coords, border_coords)
                if had_missing:
                    incomplete_airspaces += 1
                    continue
                if not had_missing and len(polygon_points) < 4:
                    if len(polygon_points) == 0:
                        empty_coords += 1
                        # print(f"[WARN] Empty coords: {current_name} - {polygon_points}")
                    elif len(polygon_points) == 1:
                        points += 1
                        # print(f"[WARN] Point: {current_name} - {polygon_points}")
                    elif len(polygon_points) == 2:
                        segments += 1
                        # print(f"[WARN] Segment: {current_name} - {polygon_points}")
                    elif len(polygon_points) == 3:
                        segments += 1  # triangle case, but not valid as linear ring
                        # print(f"[WARN] Triangle (invalid linear ring): {current_name} - {polygon_points}")
                    skipped_airspaces += 1
                    continue

                # Create the GeoJSON feature using the new function
                if not valid_ring(polygon_points):
                    not_valid_rings += 1
                    continue
                feature = create_geojson_feature(current_name, polygon_points, icao_class, upperAltitude, lowerAltitude, radio, schedule, restrictions, remarks)
                if any(token and "frontière" in token.lower() for token in coords if isinstance(token, str)):
                    features.append(feature)

    print(f"[INFO] {airspaces} airspaces encountered")
    print(f"[INFO] Exported {len(features)} features")
    total_missing =  incomplete_airspaces+skipped_airspaces
    print(f"[INFO] Skipped airspaces (no valid polygon): {skipped_airspaces} of which {empty_coords} empty coords, {points} points, {segments} segments")
    print(f"[INFO] Empty airspaces: {empty_airspaces}")
    print(f"[INFO] Not valid rings: {not_valid_rings}")
    print(f"[INFO] Airspaces with incomplete processing and not exported: {incomplete_airspaces}")
    print(f"[WARNING] Total missing airspaces: {total_missing} ({airspaces - len(features)} expected)")

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
