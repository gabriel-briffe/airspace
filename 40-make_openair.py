import json
import re
from bs4 import BeautifulSoup
import math
# from preprocess_border_file import read_border_geojson

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
def read_border_geojson(border_file):
    try:
        with open(border_file, 'r', encoding='utf-8') as bf:
            france_geo = json.load(bf)
            if 'features' in france_geo and len(france_geo['features']) > 0:
                feature = france_geo['features'][0]
                geom = feature.get('geometry', {})
                geo_type = geom.get('type', '').lower()
                if geo_type == 'polygon':
                    border_coords = geom.get('coordinates', [])
                    if border_coords and isinstance(border_coords, list):
                        border_coords = border_coords[0]
                    else:
                        border_coords = []
                elif geo_type == 'linestring':
                    border_coords = geom.get('coordinates', [])
                else:
                    border_coords = []
            else:
                border_coords = []
            # print(f"[INFO] Loaded border from '{border_file}' with {len(border_coords)} coordinates.")
            return border_coords
    except Exception as e:
        print(f"[ERROR] Error reading {border_file}: {e}")
        return []
def read_parks_json(parks_file):
    try:
        with open(parks_file, 'r', encoding='utf-8') as pf:
            return json.load(pf)
    except Exception as e:
        print(f"[ERROR] Error reading park file {parks_file}: {e}")
    return None

def parse_circle_text(text):
    """Parse circle description and return structured data for OpenAir output"""
    m = re.search(REGEX_CIRCLE, text, re.IGNORECASE)
    if not m:
        print(f"No match found for circle description: {text}")
        return None
    
    radius_value = float(m.group(1))
    unit = m.group(2).strip().lower()
    # Convert to NM
    if unit == 'm':
        radius_nm = radius_value / 1852
    elif unit == 'km':
        radius_nm = radius_value * 0.539957
    else:
        radius_nm = radius_value
        
    lat_str = m.group(3).strip()
    lon_str = m.group(4).strip() if m.group(4) else None
    if not lon_str:
        print(f"Missing longitude in circle description: {text}")
        return None
        
    center = f"{lat_str}@{lon_str}"
    
    return {
        'type': 'circle',
        'radius': radius_nm,
        'center': center
    }

def process_circle_token(token):
    """Process circle token and return structured data"""
    if "cercle de" in token.lower() and "centré sur" in token.lower():
        circle_data = parse_circle_text(token)
        if circle_data is not None:
            return (circle_data, True)
        else:
            print(f"Circle processing failed for token: {token}")
            return (None, False)
    return (None, False)

def process_arc_token(token, prev_token, next_token, name):
    """Process arc token and return structured data for OpenAir output"""
    lower_token = token.lower()
    if "arc horaire" in lower_token or "arc anti-horaire" in lower_token:
        m = re.search(REGEX_ARC, token, re.IGNORECASE)
        if not m:
            print(f"[ERROR] No match found for arc description: {token}")
            return (None, False)
            
        direction = m.group(1).lower()
        radius_value = float(m.group(2))
        unit = m.group(3).strip().lower()
        
        # Convert to NM
        if unit == 'm':
            radius_nm = radius_value / 1852
        elif unit == 'km':
            radius_nm = radius_value / 1.852
        else:
            radius_nm = radius_value
            
        center_lat = m.group(4).strip()
        center_lon = m.group(5).strip() if m.group(5) else None
        if not center_lon:
            print(f"Missing center longitude in arc description: {token}")
            return (None, False)
            
        # Get start and end points from prev and next tokens
        m_prev = re.search(REGEX_COORD_PAIR, prev_token, re.IGNORECASE)
        m_next = re.search(REGEX_COORD_PAIR, next_token, re.IGNORECASE)
        # print(f"[DEBUG] Neighbour prev_token: '{prev_token}' -> m_prev: {m_prev.group(0) if m_prev else None}")
        # print(f"[DEBUG] Neighbour next_token: '{next_token}' -> m_next: {m_next.group(0) if m_next else None}")
        if m_prev and m_next:
            return ({
                'type': 'arc',
                'direction': direction,
                'radius': radius_nm,
                'center': f"{center_lat}@{center_lon}",
                'start': m_prev.group(0),
                'end': m_next.group(0)
            }, True)
        else:
            print(f"Missing start/end points for arc: {token}")
            return (None, False)
            
    return (None, False)

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

def substract_alllonLat(text):
    matches = re.findall(REGEX_COORD_PAIR, text, re.IGNORECASE)
    remaining_text = re.sub(REGEX_COORD_PAIR, '', text, flags=re.IGNORECASE).strip()
    return matches, remaining_text
       
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
            if not any(x in token for x in ["Frontière"]):
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
    prev_token,rest = substract_lonLat(prev_token)
    next_token,rest = substract_lonLat(next_token)
    return {
        "token": token,
        "prev_token": prev_token,
        "next_token": next_token
    }

def get_shortest_path_for_triplet(triplet, border_file):
    """For a given triplet with 'prev_token' and 'next_token' in 'lat@lon' format,
    find the closest points in border_coords and return the shortest path between them
    as a list of coordinate pairs [lon, lat].
    border_coords is a list of [lon, lat] pairs.
    """
    try:
        border_coords = read_border_geojson(border_file)
    except Exception as e:
        print(f"[ERROR] Failed to read border file: {e}")
        return [], False
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

def process_france_token(token,prev_token,next_token,border_files):
    points=[]
    triplet = make_triplet(token,prev_token,next_token)
    if ("frontière franco-" in triplet["token"].lower() or 
        "limite des eaux territoriales atlantique françaises" in triplet["token"].lower()):
        if is_pure_lonLat(triplet["prev_token"]) and is_pure_lonLat(triplet["next_token"]):
            points,success = get_shortest_path_for_triplet(triplet,border_files["france"])
            if len(points) == 0: print(f"[WARN] No points found for triplet: {triplet}")
            return points,success
        else:
            print(f"[WARN] Not pure lonLat before and after: {prev_token} - {token} - {next_token}")
            return points,False
    elif "frontière" in triplet["token"].lower() and "germano-suisse" in triplet["token"].lower():
        if is_pure_lonLat(triplet["prev_token"]) and is_pure_lonLat(triplet["next_token"]):
            points,success = get_shortest_path_for_triplet(triplet,border_files["switzerland"])
            if len(points) == 0: print(f"[WARN] No points found for triplet: {triplet}")
            return points,success
        else:
            print(f"[WARN] Not pure lonLat before and after: {token}")
            return points,False
    elif "frontière hispano-andorrane" in triplet["token"].lower():
        if is_pure_lonLat(triplet["prev_token"]) and is_pure_lonLat(triplet["next_token"]):
            points,success = get_shortest_path_for_triplet(triplet,border_files["andorra"])
            if len(points) == 0: print(f"[WARN] No points found for triplet: {triplet}")
            return points,success
        else:
            print(f"[WARN] Not pure lonLat before and after: {triplet['prev_token']} - {triplet['token']} - {triplet['next_token']}")
            print(f"[----] We hade to substract: {prev_token} - {token} - {next_token}")
            return points,False
    elif ("la côte atlantique française" in triplet["token"].lower() or 
          "côte méditérrannéenne" in triplet["token"].lower()):
        if is_pure_lonLat(triplet["prev_token"]) and is_pure_lonLat(triplet["next_token"]):
            points,success = get_shortest_path_for_triplet(triplet,border_files["atlantique"])
            if len(points) == 0: print(f"[WARN] No points found for triplet: {triplet}")
            return points,success
        else:
            print(f"[WARN] Not pure lonLat before and after: {triplet['prev_token']} - {triplet['token']} - {triplet['next_token']}")
            print(f"[----] We hade to substract: {prev_token} - {token} - {next_token}")
    elif "côte corse" in triplet["token"].lower():
        if is_pure_lonLat(triplet["prev_token"]) and is_pure_lonLat(triplet["next_token"]):
            points,success = get_shortest_path_for_triplet(triplet,border_files["corse"])
            if len(points) == 0: print(f"[WARN] No points found for triplet: {triplet}")
            return points,success
        else:
            print(f"[WARN] Not pure lonLat before and after: {triplet['prev_token']} - {triplet['token']} - {triplet['next_token']}")
    else:
        print(f"[WARN] Not a France token: {token.lower()}")
    return [], False

def get_first_latLon(token):
    match_list = re.findall(REGEX_COORD_PAIR, token, re.IGNORECASE)
    if match_list:
        return match_list[0]
    else:
        return token

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

def process_parc_ecrins_token(token, prev_token, next_token):
    """
    Expects token to be a string representing the key in parks.json,
    along with its previous and next tokens (in 'lat@lon' format).
    Returns the shortest path between the points on the park border (from parks.json) and a success flag.
    """
    # Build a triplet from the provided tokens
    triplet = make_triplet(token, prev_token, next_token)

    import json
    try:
        with open('parks.json', 'r', encoding='utf-8') as pf:
            parks = json.load(pf)
    except Exception as e:
        print(f"[ERROR] Failed to read parks.json: {e}")
        return [], False

    key = "420 . PARC NATIONAL DES ECRINS"
    if key not in parks:
        print(f"[WARN] Park key '{key}' not found in parks.json")
        return [], False

    border_coords = parks[key].get('coordinates', [])
    if not border_coords:
        print(f"[WARN] No coordinates found for park key: {key}")
        return [], False

    # Helper function to find the closest index in border_coords for a given point
    def find_closest_index(pt, coords):
        best_idx = None
        best_dist = None
        for idx, coord in enumerate(coords):
            dist = (pt[0] - coord[0])**2 + (pt[1] - coord[1])**2
            if best_dist is None or dist < best_dist:
                best_dist = dist
                best_idx = idx
        return best_idx

    # Convert previous token to coordinate (expecting format 'lat@lon')
    try:
        b_lat_str, b_lon_str = triplet["prev_token"].split('@')
        b_lat = convert_coord(b_lat_str)
        b_lon = convert_coord(b_lon_str)
        triplet_begin = (b_lon, b_lat)  # border_coords are [lon, lat]
    except Exception as e:
        print(f"[ERROR] Failed to parse previous token: {e}")
        return [], False

    # Convert next token to coordinate
    try:
        e_lat_str, e_lon_str = triplet["next_token"].split('@')
        e_lat = convert_coord(e_lat_str)
        e_lon = convert_coord(e_lon_str)
        triplet_end = (e_lon, e_lat)  # border_coords are [lon, lat]
    except Exception as e:
        print(f"[ERROR] Failed to parse next token: {e}")
        return [], False

    i_begin = find_closest_index(triplet_begin, border_coords)
    i_end = find_closest_index(triplet_end, border_coords)
    if i_begin is None or i_end is None:
        print(f"[DEBUG] No closest index found for triplet {triplet}")
        return [], False

    def circular_path(i, j, coords):
        if i <= j:
            return coords[i:j+1]
        else:
            return coords[i:] + coords[:j+1]

    path1 = circular_path(i_begin, i_end, border_coords)
    path2 = circular_path(i_end, i_begin, border_coords)[::-1]  

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

def process_polygon_token(token):
    """Process a standard coordinate token and return structured data"""
    coordinates = []
    pairs = get_coordinates(token)
    if pairs:
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
            coordinates.append(f"{lat_str}@{lon_str}")
        
        if coordinates:
            return ({
                'type': 'polygon',
                'coordinates': coordinates
            }, True)
    
    return (None, False)

def process_coordinates(name, all_coords, border_files):
    """
    Process raw coordinate tokens into OpenAir format commands.
    Returns (commands_list, had_missing) where commands_list is a list of OpenAir commands
    and had_missing indicates if any tokens couldn't be processed.
    """
    commands = []
    had_missing = False
    i = 0
    total = len(all_coords)

    # Handle special cases (para, voltige, etc.) by converting to circle commands
    if name and (any(x in name.lower() for x in [" para ", " voltige ", " treuillage ", "aéromodélisme", " activité particulière ", "lf d "])) \
        and isinstance(all_coords, list) and total == 1:
        # If it's already a circle definition, let it pass through
        if 'cercle de' in all_coords[0].lower() and 'de rayon centré sur' in all_coords[0].lower():
            pass
        else:
            # Clean the coordinate first
            all_coords[0] = get_first_latLon(all_coords[0])
            match_list = re.findall(REGEX_COORD_PAIR, all_coords[0], re.IGNORECASE)
            if len(match_list) == 1:
                center = match_list[0]
                if any(x in name.lower() for x in [" para "]):
                    radius = "3"
                    unit = "NM"
                elif any(x in name.lower() for x in [" treuillage ", "aéromodélisme"]):
                    radius = "600"
                    unit = "m"
                elif any(x in name.lower() for x in [" voltige "]):
                    radius = "1"
                    unit = "NM"
                elif any(x in name.lower() for x in [" activité particulière "]):
                    radius = "1"
                    unit = "km"
                elif name == "LF D 562 - LA VALETTE":
                    radius = "1.35"
                    unit = "NM"
                elif name == "LF D 595 LASER HAUTE PROVENCE":
                    radius = "1.5"
                    unit = "km"
                else:
                    print(f"[WARN] Remain to treat {all_coords} - {name} ")
                    return ([], True)
                
                all_coords = [f"cercle de {radius} {unit} de rayon centré sur {center}"]

    while i < total:
        token = all_coords[i]
        token_commands = []
        prev_index = i - 1 if i != 0 else total - 1
        next_index = i + 1 if i != total - 1 else 0
        prev_token = all_coords[prev_index]
        next_token = all_coords[next_index]

        if "arc horaire" in token.lower() or "arc anti-horaire" in token.lower():
            geometry, complete = process_arc_token(token, prev_token, next_token, name)
            if complete:
                # Write arc commands - note the reordered commands
                if geometry['direction'] == "anti-horaire":
                    token_commands.append("V D=-")
                token_commands.append(f"V X={formatDMS(geometry['center'])}")
                token_commands.append(f"DB {formatDMS(geometry['start'])},{formatDMS(geometry['end'])}")
            else:
                had_missing = True
                print(f"[WARN] Unprocessed arc: {name} - {token}")

        elif "cercle de" in token.lower() and "centré sur" in token.lower():
            geometry, complete = process_circle_token(token)
            if complete:
                # Write circle commands
                token_commands.append(f"V X={formatDMS(geometry['center'])}")
                token_commands.append(f"DC {geometry['radius']}")
            else:
                had_missing = True
                print(f"[WARN] Unprocessed circle: {name} - {token}")

        elif ("frontière" in token.lower() or 
              "la côte atlantique française" in token.lower() or 
              "côte corse" in token.lower() or
              "limite des eaux territoriales atlantique françaises" in token.lower() or
              "côte méditérrannéenne" in token.lower()):
            points, complete = process_france_token(token, prev_token, next_token, border_files)
            if complete:
                # Convert border points to DP commands
                for point in points:
                    lat = format_dms(point[1], True)
                    lon = format_dms(point[0], False)
                    coord_str = f"{lat}@{lon}"
                    token_commands.append(f"DP {formatDMS(coord_str)}")
            else:
                had_missing = True
                print(f"[WARN] Unprocessed border: {name} - {token}")

        elif "axe" in token.lower():
            print(f"[DEBUG] Unsupported token type: {token} : {name}")
            had_missing = True

        elif "parc national des écrins" in token.lower():
            points, complete = process_parc_ecrins_token(token, prev_token, next_token)
            if complete:
                # Convert park points to DP commands
                for point in points:
                    lat = format_dms(point[1], True)
                    lon = format_dms(point[0], False)
                    coord_str = f"{lat}@{lon}"
                    token_commands.append(f"DP {formatDMS(coord_str)}")
            else:
                had_missing = True
                print(f"[WARN] Unprocessed park: {name} - {token}")

        else:
            # Process standard coordinate pair
            # print(f"[DEBUG] Processing token: {token}")
            token = get_first_latLon(token)
            geometry, complete = process_polygon_token(token)
            if complete:
                for coord in geometry['coordinates']:
                    token_commands.append(f"DP {formatDMS(coord)}")
            else:
                had_missing = True
                print(f"[WARN] Unprocessed coordinates: {token} : {name}")

        commands.extend(token_commands)
        i += 1

    return (commands, had_missing)

def formatDMS(coord_str):
    """Convert a lat@lon string to OpenAir DMS format.
    Input format: "DDMMSS[NS]@DDDMMSS[EW]"
    Output format: "DD:MM:SS N DDD:MM:SS E"
    """
    # Split the coordinates
    lat_str, lon_str = coord_str.split('@')
    
    # Process latitude
    lat_num = lat_str[:-1]  # Remove N/S
    lat_hem = lat_str[-1]   # Get N/S
    lat_deg = lat_num[:2]
    lat_min = lat_num[2:4]
    lat_sec = lat_num[4:6]
    
    # Process longitude
    lon_num = lon_str[:-1]  # Remove E/W
    lon_hem = lon_str[-1]   # Get E/W
    lon_deg = lon_num[:3]   # Note: longitude has 3 digits for degrees
    lon_min = lon_num[3:5]
    lon_sec = lon_num[5:7]
    
    # Format in OpenAir DMS style with spaces before hemisphere letters
    return f"{lat_deg}:{lat_min}:{lat_sec} {lat_hem} {lon_deg}:{lon_min}:{lon_sec} {lon_hem}"

def parse_altitude(alt_str):
    """Parse altitude string and return OpenAir format"""
    if not alt_str:
        return None
        
    formatted = alt_str.upper()
    
    # Handle FL cases first
    if re.search(r'\b[Ff][Ll]\s*\d', formatted):
        m = re.search(r'\b[Ff][Ll]\s*(\d+)\b', formatted)
        if m:
            return f"FL{m.group(1)}"  # Direct return for FL cases
        else:
            print(f"Warning: FL found but no number after FL in: {formatted}")
            return None

    # Standard replacements
    formatted = re.sub(r"\bSFC\b", "GND", formatted)
    formatted = re.sub(r"\bASFC\b", "AGL", formatted)
    formatted = re.sub(r"\bAMSL\b", "MSL", formatted)
    formatted = re.sub(r"\bUNL\b", "UNL", formatted)

    # Rest of the processing for non-FL altitudes...

    # Split into tokens and merge numeric+unit tokens
    tokens = formatted.split()
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

    # Take only first altitude if multiple exist (first value-unit-ref triplet)
    if len(tokens) >= 2:
        m = re.match(r"^(\d+)([a-zA-Z]+)$", tokens[0])
        if m and not re.search(r"\d", tokens[1]):
            value = m.group(1)
            unit = m.group(2).lower()
            ref = tokens[1].upper()
            
            # Convert to OpenAir format - note the removal of space in FL case
            if ref == "STD":
                return f"FL{value}"  # No space
            elif ref == "GND":
                if value == "0":
                    return "GND"
                return f"{value}ft AGL"
            elif ref == "MSL":
                return f"{value}ft AMSL"
            else:
                return f"{value}{unit} {ref}"
    
    return alt_str  # Return unchanged if parsing fails

def write_openair_header(f, name, icao_class, airspace_type, upper_alt, lower_alt, frequency=None, station=None):
    """Write the header section of an OpenAir airspace definition"""
    # Convert ICAO class (already in correct format A-G or "Other" -> "UNCLASSIFIED")
    openair_class = "UNCLASSIFIED" if icao_class == "Other" else icao_class
    
    # Write mandatory fields
    f.write(f"AC {openair_class}\n")
    f.write(f"AN {name}\n")
    
    # Write type if present (ensure uppercase)
    if airspace_type:
        f.write(f"AY {airspace_type.upper()}\n")
    
    # Parse and write altitude limits
    upper = parse_altitude(upper_alt)
    lower = parse_altitude(lower_alt)
    
    if upper:
        f.write(f"AH {upper}\n")
    if lower:
        f.write(f"AL {lower}\n")
    
    # Write optional fields if present
    if frequency:
        f.write(f"AF {frequency}\n")
    if station:
        f.write(f"AG {station}\n")

def write_openair_geometry(f, geometry):
    """Write the geometric definition of an airspace using structured data"""
    if not geometry or 'type' not in geometry:
        return
    
    geo_type = geometry['type']
    
    if geo_type == "circle":
        if 'center' in geometry and 'radius' in geometry:
            f.write(f"V X={formatDMS(geometry['center'])}\n")
            f.write(f"DC {geometry['radius']}\n")
    
    elif geo_type == "polygon":
        if 'coordinates' in geometry:
            for coord in geometry['coordinates']:
                f.write(f"DP {formatDMS(coord)}\n")
    
    elif geo_type == "arc":
        if 'center' in geometry:
            f.write(f"V X={formatDMS(geometry['center'])}\n")
            if geometry.get('direction') == "anti-horaire":
                f.write("V D=-\n")
            
            if 'start' in geometry and 'end' in geometry:
                # Using DB command with start/end points
                f.write(f"DB {formatDMS(geometry['start'])},{formatDMS(geometry['end'])}\n")
            elif all(k in geometry for k in ['radius', 'start_angle', 'end_angle']):
                # Using DA command with angles
                f.write(f"DA {geometry['radius']},{geometry['start_angle']},{geometry['end_angle']}\n")

def write_openair_feature(f, name, icao_class, commands, upper_alt, lower_alt, frequency=None, station=None):
    """Write a complete airspace feature in OpenAir format"""
    # Check for missing altitude limits
    if not upper_alt or not lower_alt:
        print(f"[WARN] Missing altitude limits for {name}")
        if not upper_alt:
            print(f"       Upper limit missing")
        if not lower_alt:
            print(f"       Lower limit missing")
    
    # Write header
    write_openair_header(f, name, icao_class, "", upper_alt, lower_alt, frequency, station)
    
    # Write geometry commands
    for cmd in commands:
        f.write(f"{cmd}\n")
    
    # Add blank line between features
    f.write("\n")

def format_airspace_name(name):
    """Format airspace name to match standard format.
    Example: 'LF R 108 A F3 ISTRES' -> 'LF-R108AF3 ISTRES'"""
    parts = name.split()
    
    # Handle empty name
    if not parts:
        return name
        
    # Initialize result and buffer
    result = []
    buffer = []
    
    # Handle LF prefix only if it's not already in the format we want
    if parts[0] == "LF" and len(parts) > 1 and parts[1] != "-":
        buffer.append("LF-")
        parts = parts[1:]  # Remove LF from parts
    elif parts[0] == "LF-":
        buffer.append("LF-")
        parts = parts[1:]  # Remove LF- from parts
    
    # Process remaining parts
    found_main_word = False
    
    for part in parts:
        if not found_main_word:
            # Check if it's a main word (3+ letters and not a number)
            is_main_word = len(part) >= 3 and not any(c.isdigit() for c in part)
            
            if is_main_word:
                # Add buffer contents and this part with a space
                prefix = buffer[0] + ''.join(buffer[1:]) if buffer else ''
                result.append(f"{prefix} {part}")
                buffer = []
                found_main_word = True
            else:
                buffer.append(part)
        else:
            # After main word, keep original spacing
            result.append(part)
    
    # If we never found a main word, join everything
    if not found_main_word and buffer:
        result.append(''.join(buffer))
    
    # Join with spaces and remove any double spaces
    return ' '.join(result).strip()

def main(input_file, output_file, border_files, parks_file):
    # Parse the cleaned HTML file
    with open(input_file, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')

    # Load the parks data from JSON file
    parks_data = read_parks_json(parks_file)

    # Open output file in UTF-8 encoding
    with open(output_file, 'w', encoding='utf-8') as outfile:
        # Write file header
        outfile.write("* Generated by airspace converter\n")
        outfile.write("* Source: eAIP France\n\n")

        airspaces = 0
        processed = 0
        empty_airspaces = 0
        incomplete_airspaces = 0
        skipped_airspaces = 0

        # Process each table container
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
                    tds = tr.find_all('td')
                    if not tds:
                        print(f"[SKIP] No table cells found for airspace {current_name}")
                        continue

                    # Extract cell data based on container index
                    cell_text = tds[0].get_text(strip=True)
                    icao_class = ""
                    upper_alt = ""
                    lower_alt = ""
                    frequency = ""

                    # Different container types have different cell structures
                    if container_index in [0, 1, 2, 3, 12]:  # Class A-E airspaces
                        icao_class = tds[1].get_text(strip=True)
                        altitude_text = tds[2].get_text(strip=True)
                        alt_parts = altitude_text.split("------------")
                        upper_alt = alt_parts[0].strip()
                        lower_alt = alt_parts[1].strip()
                        frequency = tds[3].get_text(strip=True)
                    elif container_index == 4:  # Class G airspaces
                        altitude_text = tds[1].get_text(strip=True)
                        alt_parts = altitude_text.split("------------")
                        upper_alt = alt_parts[0].strip()
                        lower_alt = alt_parts[1].strip()
                        frequency = tds[2].get_text(strip=True)
                    elif container_index in [5, 6]:  # Restricted areas
                        altitude_text = tds[1].get_text(strip=True)
                        alt_parts = altitude_text.split("------------")
                        upper_alt = alt_parts[0].strip()
                        lower_alt = alt_parts[1].strip()
                    elif container_index == 7:  # Prohibited areas
                        altitude_text = tds[1].get_text(strip=True)
                        alt_parts = altitude_text.split("------------")
                        upper_alt = alt_parts[0].strip()
                        lower_alt = alt_parts[1].strip()
                    elif container_index in [8, 9]:  # Danger areas
                        altitude_text = tds[1].get_text(strip=True)
                        alt_parts = altitude_text.split("------------")
                        upper_alt = alt_parts[0].strip()
                        lower_alt = alt_parts[1].strip()
                    elif container_index == 10:  # Training areas
                        altitude_text = tds[1].get_text(strip=True)
                        alt_parts = altitude_text.split("------------")
                        upper_alt = alt_parts[0].strip()
                        lower_alt = alt_parts[1].strip()
                    elif container_index == 11:  # Low-level areas
                        upper_alt = tds[1].get_text(strip=True)
                        lower_alt = "GND"

                    # Print warning if altitude limits are missing
                    if not upper_alt or not lower_alt:
                        print(f"[WARN] Missing altitude limits for {current_name} (container {container_index})")
                        if not upper_alt:
                            print(f"       Upper limit missing")
                        if not lower_alt:
                            print(f"       Lower limit missing")

                    try:
                        # Clean and parse coordinates
                        clean_text = re.sub(r'[\x00-\x1F]+', ' ', cell_text)
                        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
                        coords = json.loads(clean_text)
                    except Exception as e:
                        print(f"[SKIP-PARSE] Error parsing coordinates for {current_name}: {e}")
                        print(f"[SKIP-PARSE] Cell text: {cell_text}")
                        skipped_airspaces += 1
                        continue

                    if len(coords) == 0:
                        print(f"[SKIP-EMPTY] Empty coordinates for {current_name}")
                        empty_airspaces += 1
                        continue

                    # Handle parks data
                    if parks_data and current_name in parks_data:
                        park_coords = parks_data[current_name]["coordinates"]
                        if park_coords:
                            current_name = "PARC/RESERVE " + current_name
                            # Convert park coordinates to OpenAir commands
                            commands = []
                            for point in park_coords:
                                lat = format_dms(point[1], True)
                                lon = format_dms(point[0], False)
                                coord_str = f"{lat}@{lon}"
                                commands.append(f"DP {formatDMS(coord_str)}")
                            
                            # Write the airspace
                            write_openair_feature(outfile, current_name, icao_class, 
                                               commands, upper_alt, lower_alt, frequency)
                            processed += 1
                            continue

                    # Process coordinates into OpenAir commands
                    commands, had_missing = process_coordinates(current_name, coords, border_files)
                    if had_missing:
                        print(f"[SKIP-INCOMPLETE] Incomplete processing for {current_name}")
                        print(f"[SKIP-INCOMPLETE] Coordinates: {coords}")
                        incomplete_airspaces += 1
                        continue

                    # Validate commands based on type
                    is_valid = False
                    if any(cmd.startswith('DC ') for cmd in commands):
                        # Circle definitions need V X= and DC commands (2 commands)
                        is_valid = len(commands) >= 2
                    elif len(commands) == 1 and commands[0].startswith('DP '):
                        # Single point definitions are valid
                        is_valid = False
                    else:
                        # Other geometries (polygons, arcs) need at least 3 commands
                        is_valid = len(commands) >= 3

                    if not is_valid:
                        print(f"[SKIP-INVALID] Invalid command count for {current_name}")
                        print(f"[SKIP-INVALID] Commands generated: {commands}")
                        print(f"[SKIP-INVALID] From coordinates: {coords}")
                        skipped_airspaces += 1
                        continue

                    # Write the airspace
                    write_openair_feature(outfile, current_name, icao_class, commands, 
                                       upper_alt, lower_alt, frequency)
                    processed += 1

        # Process ZSM data
        try:
            with open('zsm.geojson', 'r', encoding='utf-8') as zsm_file:
                zsm_data = json.load(zsm_file)
            for feature in zsm_data.get('features', []):
                props = feature.get('properties', {})
                name = props.get("code_zsm", "")
                airspaces += 1
                
                # Convert altitude
                try:
                    upper_alt = f"{int(float(props.get('_max', 0)))}ft MSL"
                except:
                    upper_alt = "0ft MSL"
                
                # Convert geometry to OpenAir commands
                geom = feature.get('geometry', {})
                if geom.get('type') == 'Polygon':
                    commands = []
                    for coord in geom.get('coordinates', [[]])[0]:
                        lat = format_dms(coord[1], True)
                        lon = format_dms(coord[0], False)
                        coord_str = f"{lat}@{lon}"
                        commands.append(f"DP {formatDMS(coord_str)}")
                    
                    # Write the ZSM airspace
                    write_openair_feature(outfile, name, "UNCLASSIFIED", commands, 
                                       upper_alt, "GND")
                    processed += 1

        except Exception as e:
            print(f"[ERROR] Failed to process zsm.geojson: {e}")

        # Print statistics
        print(f"[INFO] {airspaces} airspaces encountered")
        print(f"[INFO] {processed} airspaces written")
        print(f"[INFO] {empty_airspaces} empty airspaces skipped")
        print(f"[INFO] {incomplete_airspaces} incomplete airspaces")
        print(f"[INFO] {skipped_airspaces} invalid airspaces skipped")

if __name__ == '__main__':
    input_file = 'eaip_selected_tables_stage1_cleaned.html'
    output_file = 'airspace.openair'  # Changed extension to .openair
    border_files = {
        "france": "France.geojson",
        "andorra": "Andorre.geojson",
        "switzerland": "Suisse.geojson",
        "atlantique": "France_coastline.geojson",
        "corse": "Corsica.geojson"
    }
    parks_file = "parks.json"

    main(input_file, output_file, border_files, parks_file)

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

