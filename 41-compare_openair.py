import difflib
import re
from difflib import SequenceMatcher

def read_openair_file(filename):
    """Read an OpenAir file and return a dictionary of airspaces.
    Each airspace is represented by a dictionary containing its properties."""
    airspaces = {}
    current_airspace = None
    
    with open(filename, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('*'):
                continue
                
            if line.startswith('AN '):
                if current_airspace:
                    airspaces[current_airspace['name']] = current_airspace
                current_airspace = {
                    'name': line[3:].strip(),
                    'geometry': [],
                    'class': None,
                    'floor': None,
                    'ceiling': None
                }
            elif current_airspace:
                if line.startswith('AC '):
                    current_airspace['class'] = line[3:].strip()
                elif line.startswith('AL '):
                    current_airspace['floor'] = line[3:].strip()
                elif line.startswith('AH '):
                    current_airspace['ceiling'] = line[3:].strip()
                elif line.startswith(('DP ', 'V ', 'DC ', 'DB ')):
                    current_airspace['geometry'].append(line.strip())
    
    # Add the last airspace
    if current_airspace:
        airspaces[current_airspace['name']] = current_airspace
    
    return airspaces

def normalize_altitude(alt):
    """Normalize altitude strings to handle equivalent terms."""
    if not alt:
        return alt
    
    # Convert to uppercase for consistent comparison
    alt = alt.upper()
    
    # Handle equivalent ground references
    alt = alt.replace('SFC', 'GND')
    
    # Handle equivalent mean sea level references
    alt = alt.replace('AMSL', 'MSL')
    
    # Special conversion: if altitude is 'FL999', return 'UNL'
    if alt.strip() == 'FL999':
        return 'UNL'
    
    # Normalize flight level formats e.g., 'FL 075' -> 'FL75'
    m = re.match(r'^FL\s*(0*)(\d+)$', alt)
    if m:
        return f"FL{int(m.group(2))}"
    
    # Remove space between number and FT, e.g., '3400 FT' -> '3400FT'
    alt = re.sub(r'(\d+)\s+FT', r'\1FT', alt)
    
    # If altitude matches a pattern like '3400FT GND', replace 'GND' with 'AGL'
    alt = re.sub(r'^(\d+FT)\s*GND$', r'\1 AGL', alt)
    
    return alt

def normalize_name(name):
    """Remove all spaces, dashes, and specific patterns from name for comparison"""
    # Convert to uppercase for consistent comparison
    name = name.upper()
    # Remove specific patterns first
    name = name.replace("(NOTAM)", "").replace("(MON-FRI)", "")\
        .replace("PARTIE", "").replace("(VOL LIBRE)", "")
    # Remove any remaining parentheses and their contents
    name = re.sub(r'\([^)]*\)', '', name)
    # Remove all non-alphanumeric characters
    name = re.sub(r'[^A-Z0-9]', '', name)
    # Remove LF prefix if it exists
    if name.startswith('LF'):
        name = name[2:]
    return name.strip()

def normalize_geometry(geom_list):
    """Normalize a list of geometry strings:
    - Replace multiple spaces with a single space
    - Remove any line that matches a pattern like an optional sign followed by 'V D=+'
    - Remove spaces on both sides of a comma
    """
    normalized = []
    for line in geom_list:
        # Replace multiple spaces with a single space and strip
        line_norm = re.sub(r'\s+', ' ', line).strip()
        # Remove spaces on both sides of a comma
        line_norm = re.sub(r'\s*,\s*', ',', line_norm)
        # If the line starts with an optional '+' or '-' then 'V D=+', skip it
        if re.match(r'^[+-]?V D=\+', line_norm):
            continue
        normalized.append(line_norm)
    return normalized

def compare_airspaces(airspaces1, airspaces2, file1_name, file2_name):
    """Compare two OpenAir files and report similarities."""
    max_len = max(len(file1_name), len(file2_name))
    aligned_file1 = file1_name.ljust(max_len)
    aligned_file2 = file2_name.ljust(max_len)
    
    # Filter out ZSM airspaces first
    airspaces1 = {name: space for name, space in airspaces1.items() 
                  if not name.upper().startswith('ZSM')}
    airspaces2 = {name: space for name, space in airspaces2.items() 
                  if not name.upper().startswith('ZSM')}
    
    print(f"{aligned_file1} contains {len(airspaces1)} airspaces (excluding ZSM)")
    print(f"{aligned_file2} contains {len(airspaces2)} airspaces (excluding ZSM)")
    
    # First find exact matches (name, geometry, and altitudes)
    normalized_map1 = {normalize_name(name): name for name in airspaces1.keys()}
    normalized_map2 = {normalize_name(name): name for name in airspaces2.keys()}
    
    common_normalized = set(normalized_map1.keys()) & set(normalized_map2.keys())
    
    # Get exact matches (same normalized name, geometry AND altitudes)
    exact_matches = []
    for norm in common_normalized:
        name1 = normalized_map1[norm]
        name2 = normalized_map2[norm]
        space1 = airspaces1[name1]
        space2 = airspaces2[name2]
        if (space1['geometry'] == space2['geometry'] and
            normalize_altitude(space1['floor']) == normalize_altitude(space2['floor']) and
            normalize_altitude(space1['ceiling']) == normalize_altitude(space2['ceiling'])):
            exact_matches.append((name1, name2))
    
    print(f"\nFound {len(exact_matches)} airspaces with identical names, geometry and altitudes")
    
    # Remove exact matches from consideration
    matched_norms = {normalize_name(name1) for name1, _ in exact_matches}
    remaining1 = {name: airspaces1[name] for name in airspaces1.keys() 
                 if normalize_name(name) not in matched_norms}
    remaining2 = {name: airspaces2[name] for name in airspaces2.keys() 
                 if normalize_name(name) not in matched_norms}
    
    print(f"Remaining airspaces to analyze: {len(remaining1)} in {file1_name}, {len(remaining2)} in {file2_name}")
    
    # Among remaining, find those with same name but different geometry/altitudes
    same_name_diff_geom = []  # Different geometry
    same_name_diff_alt = []   # Different altitudes
    
    for norm in set(normalize_name(name) for name in remaining1.keys()) & \
               set(normalize_name(name) for name in remaining2.keys()):
        name1 = normalized_map1[norm]
        name2 = normalized_map2[norm]
        space1 = airspaces1[name1]
        space2 = airspaces2[name2]
        norm_geom1 = normalize_geometry(space1['geometry'])
        norm_geom2 = normalize_geometry(space2['geometry'])
        same_geom = norm_geom1 == norm_geom2
        same_alt = (normalize_altitude(space1['floor']) == normalize_altitude(space2['floor']) and
                   normalize_altitude(space1['ceiling']) == normalize_altitude(space2['ceiling']))
        
        if not same_geom and same_alt:
            same_name_diff_geom.append((name1, name2))
        elif same_geom and not same_alt:
            same_name_diff_alt.append((name1, name2))
    
    print(f"Among remaining, {len(same_name_diff_geom)} have identical names and altitudes but different geometry")
    print(f"Among remaining, {len(same_name_diff_alt)} have identical names and geometry but different altitudes")
    
    # Show all normalized names and altitudes
    print(f"\nFound {len(same_name_diff_geom)} pairs with same name and altitudes but different geometry:")
    
    for i, (name1, name2) in enumerate(sorted(same_name_diff_geom)[:10], 1):
        space1 = airspaces1[name1]
        space2 = airspaces2[name2]
        print(f"\nPair {i}:")
        print(f"  {aligned_file1}: {name1}")
        print(f"  {aligned_file2}: {name2}")
        print(f"  Normalized as:")
        print(f"    {normalize_name(name1)}")
        print(f"    {normalize_name(name2)}")
        print(f"  Altitudes:")
        print(f"    Floor:   {normalize_altitude(space1['floor'])} = {normalize_altitude(space2['floor'])}")
        print(f"    Ceiling: {normalize_altitude(space1['ceiling'])} = {normalize_altitude(space2['ceiling'])}")
        # Print out the differences in geometry
        geom1 = normalize_geometry(space1['geometry'])
        geom2 = normalize_geometry(space2['geometry'])
        diff = list(difflib.unified_diff(geom1, geom2, fromfile='Geometry in ' + aligned_file1, tofile='Geometry in ' + aligned_file2, lineterm=''))
        if diff:
            print("  Geometry differences:")
            for line in diff:
                print(f"    {line}")
        else:
            print("  No geometry differences detected.")
    
    # Show examples of same name and geometry but different altitudes
    print(f"\nShowing 20 examples of pairs with same name and geometry but different altitudes:")
    for i, (name1, name2) in enumerate(sorted(same_name_diff_alt)[:10], 1):
        space1 = airspaces1[name1]
        space2 = airspaces2[name2]
        print(f"\nPair {i}:")
        print(f"  {aligned_file1}: {name1}")
        print(f"  {aligned_file2}: {name2}")
        print(f"  Altitudes:")
        print(f"    {aligned_file1} Floor:   {normalize_altitude(space1['floor'])}")
        print(f"    {aligned_file2} Floor:   {normalize_altitude(space2['floor'])}")
        print(f"    {aligned_file1} Ceiling: {normalize_altitude(space1['ceiling'])}")
        print(f"    {aligned_file2} Ceiling: {normalize_altitude(space2['ceiling'])}")
    
    # Among remaining, find those with same geometry and altitudes but different names
    same_geom_diff_name = []
    geom_alt_map1 = {(tuple(normalize_geometry(space['geometry'])), 
                      normalize_altitude(space['floor']),
                      normalize_altitude(space['ceiling'])): name 
                     for name, space in remaining1.items()}
    geom_alt_map2 = {(tuple(normalize_geometry(space['geometry'])), 
                      normalize_altitude(space['floor']),
                      normalize_altitude(space['ceiling'])): name 
                     for name, space in remaining2.items()}
    
    common_geoms = set(geom_alt_map1.keys()) & set(geom_alt_map2.keys())
    for geom_alt in common_geoms:
        name1 = geom_alt_map1[geom_alt]
        name2 = geom_alt_map2[geom_alt]
        if normalize_name(name1) != normalize_name(name2):  # Different names
            same_geom_diff_name.append((name1, name2))
    
    print(f"\nFound {len(same_geom_diff_name)} pairs with identical geometry and altitudes but different names:")
    
    for i, (name1, name2) in enumerate(sorted(same_geom_diff_name)[:10], 1):
        space1 = airspaces1[name1]
        space2 = airspaces2[name2]
        print(f"\nPair {i}:")
        print(f"  {aligned_file1}: {name1}")
        print(f"  {aligned_file2}: {name2}")
        print(f"  Normalized as:")
        print(f"    {normalize_name(name1)}")
        print(f"    {normalize_name(name2)}")
        print(f"  Altitudes:")
        print(f"    Floor:   {normalize_altitude(space1['floor'])} = {normalize_altitude(space2['floor'])}")
        print(f"    Ceiling: {normalize_altitude(space1['ceiling'])} = {normalize_altitude(space2['ceiling'])}")
    
    print(f"\nSummary:")
    print(f"Exact matches: {len(exact_matches)}")
    print(f"Same name and altitudes but different geometry: {len(same_name_diff_geom)}")
    print(f"Same name and geometry but different altitudes: {len(same_name_diff_alt)}")
    print(f"Same geometry and altitudes but different names: {len(same_geom_diff_name)}")

    # Among the remaining airspaces (those not exactly matched), compute similarity scores for every pair of names from remaining1 and remaining2
    remaining_pairs = []
    for name1 in remaining1:
        for name2 in remaining2:
            # Use normalized names for comparison
            n1 = normalize_name(name1)
            n2 = normalize_name(name2)
            ratio = SequenceMatcher(None, n1, n2).ratio()
            remaining_pairs.append((ratio, name1, name2))
    remaining_pairs.sort(key=lambda x: x[0], reverse=True)

    print("\nMost similar remaining name pairs (top 20):")
    for ratio, name1, name2 in remaining_pairs[:20]:
        print(f"  {name1} - {name2}: similarity {ratio:.2f}")

    print("\nLeast similar remaining name pairs (bottom 20):")
    for ratio, name1, name2 in remaining_pairs[-20:]:
        print(f"  {name1} - {name2}: similarity {ratio:.2f}")

if __name__ == '__main__':
    compare_airspaces(read_openair_file('airspace.openair'), read_openair_file('france.txt'), 'airspace.openair', 'france.txt')
