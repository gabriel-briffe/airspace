# Temporary function for debugging 'Frontière' tokens

import json
import re
from bs4 import BeautifulSoup

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

# Additional filtration: if candidate['begining'] or candidate['end'] contains a lat@lon coordinate, discard extra text
coord_pair_pattern = re.compile(r'(\d{6}[NSEW]@\d{7}[NSEW])')

def filter_coordinate(text):
    m = coord_pair_pattern.search(text)
    if m:
        extracted = m.group(1)
        remaining_text = text.replace(extracted, '').strip()
    return text,remaining_text

def print_unique_tokens(candidates):
    # Print the set of unique 'Frontière' token values from candidate['token']
    unique_tokens = set()
    for candidate in candidates:
        if 'token' in candidate:
            unique_tokens.add(candidate['token'])
    print("[INFO] Unique 'Frontière' token values:")
    for token in unique_tokens:
        print(f"  - {token}")

def france_only(candidates):
    filtered = []
    for candidate in candidates:
        if "frontière franco-" in candidate["token"].lower():
            filtered.append(candidate)
        # else:
            # print(f"[WARN] Discarding candidate not matching 'frontière franco-': {candidate['token']}")
    return filtered

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
            print(f"[INFO] Loaded border from '{border_file}' with {len(border_coords)} coordinates.")
            return border_coords
    except Exception as e:
        print(f"[ERROR] Error reading {border_file}: {e}")
        return []

def read_airspace_html(html_file):
    try:
        with open(html_file, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f, 'html.parser')
        print(f"[INFO] Loaded HTML file: '{html_file}'")
        return soup
    except Exception as e:
        print(f"[ERROR] Error reading {html_file}: {e}")
        return None

def getCleanTriplets(candidates):
    for candidate in candidates:
        if candidate.get("begining"):
            new_begining, discarded_beg = filter_coordinate(candidate["begining"])
            if not new_begining: print(f"[DEBUG] No begining for {candidate['token']}")
            candidate["begining"] = new_begining
            if discarded_beg:
                print(f"[DEBUG] Discarded {discarded_beg} from begining: {new_begining}")
        else:
            print(f"[DEBUG] No begining for {candidate['token']}")

        if candidate.get("end"):
            new_end, discarded_end = filter_coordinate(candidate["end"])
            if not new_end: print(f"[DEBUG] No end for {candidate['token']}")
            candidate["end"] = new_end
            if discarded_end:
                print(f"[DEBUG] Discarded {discarded_end} from end: {new_end}")
        else:
            print(f"[DEBUG] No end for {candidate['token']}")
    return candidates

def createTriplets(soup):
    candidates = []
    # Iterate over each table container and row to find tokens and capture the surrounding tokens
    for container in soup.select('.table-container'):
        for tr in container.find_all('tr'):
            classes = tr.get('class', [])
            # We check only parsed rows
            if 'parsed-row' in classes:
                tds = tr.find_all('td')
                if not tds:
                    continue
                cell_text = tds[0].get_text(strip=True)
                try:
                    coords = json.loads(cell_text)
                except Exception as e:
                    continue
                if isinstance(coords, list):
                    for i, token in enumerate(coords):
                        if isinstance(token, str) and 'frontière' in token.lower():
                            begining = coords[i-1] if i > 0 else coords[-1]
                            end = coords[i+1] if i < len(coords)-1 else coords[0]
                            candidate = {
                                "begining": begining,
                                "token": token,
                                "end": end
                            }
                            candidates.append(candidate)
    return candidates

def get_valid_candidates(candidates):
    """Return the list of valid candidates, ready count and not ready count.
    A candidate is considered ready if both its 'begining' and 'end' match the coord_pair_pattern exactly.
    """
    valid_candidates = []
    ready_tokens = 0
    not_ready_tokens = 0
    for candidate in candidates:
        if coord_pair_pattern.search(candidate["begining"]) and coord_pair_pattern.search(candidate["end"]):
            ready_tokens += 1
            valid_candidates.append(candidate)
        else:
            not_ready_tokens += 1
    return valid_candidates, ready_tokens, not_ready_tokens

def get_border_match_count(valid_candidates, border_coords):
    """Return the number of candidates whose 'begining' and 'end' coordinates are exactly present in border_coords.
    valid_candidates: list of candidates that have valid 'lat@lon' strings
    border_coords: list of [lon, lat] pairs from the geojson border
    """
    border_match_count = 0
    for candidate in valid_candidates:
        try:
            lat_str, lon_str = candidate["begining"].split('@')
            lat_candidate = convert_coord(lat_str)
            lon_candidate = convert_coord(lon_str)
        except Exception as e:
            continue
        is_begin_in_border = any(lon_candidate == coord[0] and lat_candidate == coord[1] for coord in border_coords)
        
        try:
            lat_str_e, lon_str_e = candidate["end"].split('@')
            lat_candidate_e = convert_coord(lat_str_e)
            lon_candidate_e = convert_coord(lon_str_e)
        except Exception as e:
            continue
        is_end_in_border = any(lon_candidate_e == coord[0] and lat_candidate_e == coord[1] for coord in border_coords)
        
        if is_begin_in_border and is_end_in_border:
            border_match_count += 1
    return border_match_count

# Add helper function to format a decimal degree value into DMS string (e.g. 474600N or 0073200E)

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

# Update the get_shortest_path_for_candidate function to use format_dms when converting border points

def get_shortest_path_for_candidate(candidate, border_coords):
    """For a given candidate with 'begining' and 'end' in 'lat@lon' format,
    find the closest points in border_coords and return the shortest path between them
    as a list of points in 'lat@lon' format (formatted as DMS, e.g., 474600N@0073200E).
    border_coords is a list of [lon, lat] pairs.
    """
    # Convert candidate beginning and end to [lon, lat] using convert_coord
    try:
        b_lat_str, b_lon_str = candidate["begining"].split('@')
        b_lat = convert_coord(b_lat_str)
        b_lon = convert_coord(b_lon_str)
        candidate_begin = (b_lon, b_lat)  # border_coords order
    except Exception as e:
        return []
    try:
        e_lat_str, e_lon_str = candidate["end"].split('@')
        e_lat = convert_coord(e_lat_str)
        e_lon = convert_coord(e_lon_str)
        candidate_end = (e_lon, e_lat)  # border_coords order
    except Exception as e:
        return []

    def find_closest_index(pt, coords):
        best_idx = None
        best_dist = None
        for idx, coord in enumerate(coords):
            dist = (pt[0] - coord[0])**2 + (pt[1] - coord[1])**2
            if best_dist is None or dist < best_dist:
                best_dist = dist
                best_idx = idx
        return best_idx

    i_begin = find_closest_index(candidate_begin, border_coords)
    i_end = find_closest_index(candidate_end, border_coords)
    if i_begin is None or i_end is None:
        print(f"[DEBUG] No closest index found for candidate {candidate['token']}")
        return []

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

    # Convert chosen_path (list of [lon, lat]) to list of 'lat@lon' strings using DMS format
    result = [f"{format_dms(pt[1], True)}@{format_dms(pt[0], False)}" for pt in chosen_path]
    return result

def preprocess_frontiere_tokens(input_html_file, border_file):
    print("[INFO] Starting preprocessing of 'Frontière' tokens...")
    border_coords = read_border_geojson(border_file)

    soup = read_airspace_html(input_html_file)
    if soup is None:
        return

    frontiere_candidates = createTriplets(soup)
    toTreat = len(frontiere_candidates)
    print_unique_tokens(frontiere_candidates)

    print(f"[INFO] Found {toTreat} candidates with 'Frontière' tokens in the HTML.")

    frontiere_candidates = france_only(frontiere_candidates)
    print(f"\nremaining {len(frontiere_candidates)}/{toTreat} candidates after france_only\n")

    frontiere_candidates = getCleanTriplets(frontiere_candidates)
    print(f"\nremaining {len(frontiere_candidates)}/{toTreat} candidates after getCleanTriplets\n")

    total_tokens = len(frontiere_candidates)
    valid_candidates, ready_tokens, not_ready_tokens = get_valid_candidates(frontiere_candidates)
    print(f"\nremaining {len(valid_candidates)}/{toTreat} candidates after get_valid_candidates\n")

    border_match_count = get_border_match_count(valid_candidates, border_coords)

    print(f"\n[SUMMARY] 'Frontière' candidates: total = {total_tokens}")
    print(f"[SUMMARY] Ready candidates (with exactly 2 lat@lon): {ready_tokens}")
    print(f"[SUMMARY] Not ready candidates (missing 1 or 2 lat@lon): {not_ready_tokens}")
    print(f"[SUMMARY] Number of begining/end lat@lon already in '{border_file}': {border_match_count}\n")

    # For each valid candidate, compute and print the shortest path along the border
    for candidate in valid_candidates:
        route = get_shortest_path_for_candidate(candidate, border_coords)
        print(f"Candidate token '{candidate['token']}': shortest path -> {len(route)}")

# Call the preprocessing function before main processing
preprocess_frontiere_tokens('eaip_selected_tables_stage1_cleaned.html', 'France.geojson')