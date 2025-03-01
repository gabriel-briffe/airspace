from bs4 import BeautifulSoup
import re

# Load eaip_selected_tables.html
with open("eaip_selected_tables.html", "r", encoding="utf-8") as f:
    soup = BeautifulSoup(f, "html.parser")

# Add helper function at the top after imports

def format_coords(text):
    """Clean coordinate text by removing unwanted characters and formatting coordinate pairs as 'lat, lon'."""
    # Remove parenthesis group if preceded by 'Km' and ending with 'NM'
    text = re.sub(r'(?i)(km)\s*\([^)]*nm\)', r'\1', text)
    # Remove degree symbols and other unwanted characters
    cleaned = re.sub(r"[°º'\"’”]", "", text)

    # Replace occurrences where two coordinates are separated by '-' or ','
    # Pattern: a token (6 digits with optional spaces before letter) followed by '-' or ',' then a token (7 digits with optional spaces)
    cleaned = re.sub(
        r'(\d{6}\s*[NSEW])\s*[-,]\s*(\d{7}\s*[NSEW])',
        lambda m: f"{re.sub(r'\s+', '', m.group(1))}@{re.sub(r'\s+', '', m.group(2))}",
        cleaned
    )

    # Determine delimiter: if ' - ' exists, use that; otherwise, split on commas not inside parentheses
    if " - " in cleaned:
        tokens = cleaned.split(" - ")
    else:
        tokens = re.split(r'(?<=\d{6}[NSEW]@\d{7}[NSEW])\s*,\s*(?=\d{6}[NSEW]@\d{7}[NSEW])', cleaned)

    parts = [re.sub(r'(\d{6})\s+([NSEW])', r'\1\2', token.strip()) for token in tokens if token.strip()]
    return "[" + ", ".join(f'\"{p}\"' for p in parts) + "]"

# Add helper function to clean parsed text (remove control characters and normalize whitespace)

def remove_control_characters(text):
    """Remove control characters and normalize whitespace in the given text."""
    cleaned_text = re.sub(r'[\r\n\t\x00-\x1F\x7F]', '', text)
    normalized_text = re.sub(r'\s+', ' ', cleaned_text).strip()
    # Collapse multiple spaces into one (normalizes whitespace)
    # normalized_text = " ".join(normalized_text.split())
    # print(normalized_text)
    return normalized_text

# Add the common helper function after remove_control_characters

def compute_array_str(cell_text, prev_parsed_coords):
    """Compute the array string from cell text. If cell_text is empty, return prev_parsed_coords if available, otherwise return "[]"."""
    if cell_text and cell_text.strip():
        return format_coords(cell_text)
    else:
        return prev_parsed_coords if prev_parsed_coords is not None else "[]"

# Add helper function for creating a parsed row after compute_array_str

def create_parsed_row(array_str, other_texts):
    """Create a new parsed row with the first cell as array_str and subsequent cells with texts from other_texts."""
    new_tr = soup.new_tag("tr")
    new_tr["class"] = ["eaip-row", "parsed-row"]
    # First cell
    first_td = soup.new_tag("td")
    first_td.string = array_str
    new_tr.append(first_td)
    # Create tds for each text in list
    for text in other_texts:
        new_td = soup.new_tag("td")
        new_td.string = text
        new_tr.append(new_td)
    return new_tr

# Add helper functions for determining a name row and extracting its text

def is_name_row(tr):
    """Return True if the row (tr) is considered a name row based on presence of a <td> or <th> with class 'strong'."""
    return tr.find(lambda tag: tag.name in ['td', 'th'] and 'strong' in tag.get('class', [])) is not None


def get_name_text(tr):
    """Extract and return the concatenated stripped strings from the first <td> or <th> that contains 'strong' in its class."""
    name_td = tr.find(lambda tag: tag.name in ['td', 'th'] and 'strong' in tag.get('class', []))
    if name_td:
        # Return the joined stripped strings
        return remove_control_characters(" ".join(name_td.stripped_strings))
    return ""


def update_header(container, table_number):
    """Update the header (h3) in the container to display the table number."""
    h3 = container.find("h3")
    if h3:
        h3.string = f"Table number: {table_number}"

def process_name_row(tr):
    """Process a name row: update its strong element, mark as highlighted, and insert a parsed name row."""
    raw_text = get_name_text(tr)
    # Clear and set the text for the element that was flagged
    elt = tr.find(lambda tag: tag.name in ['td', 'th'] and 'strong' in tag.get('class', []))
    if elt:
        elt.clear()
        elt.string = raw_text
    tr["class"] = tr.get("class", []) + ["highlighted"]
    name_tr = create_parsed_name_row(raw_text)
    tr.insert_after(name_tr)

def create_parsed_name_row(raw_text):
    """Create and return a new parsed name row with the given raw text."""
    new_tr = soup.new_tag("tr")
    new_tr["class"] = ["eaip-row", "parsed-name"]
    new_td = soup.new_tag("td")
    new_td.string = raw_text
    new_tr.append(new_td)
    return new_tr




# Add helper function for generic content row processing with a transform function (default: join stripped strings)

def process_content_row_generic(tr, expected_tds, prev_parsed_coords, transform=lambda td, j: " ".join(td.stripped_strings)):
    """Process a content row if it has the expected number of <td> cells using a transform function. Returns the updated prev_parsed_coords."""
    tds = tr.find_all("td")
    if len(tds) == expected_tds:
        first_cell = tds[0]
        cell_text = first_cell.get_text(" ", strip=True)
        array_str = compute_array_str(cell_text, prev_parsed_coords)
        other_texts = [transform(td, j) for j, td in enumerate(tds[1:])]
        new_tr = create_parsed_row(array_str, other_texts)
        tr.insert_after(new_tr)
        return array_str
    return prev_parsed_coords


# Redefine process_content_row to call the generic version with default transform

def process_content_row(tr, expected_tds, prev_parsed_coords):
    return process_content_row_generic(tr, expected_tds, prev_parsed_coords)


def process_table_0(container):
    update_header(container, 0)

    # Track previous non-name row's parsed coordinates
    prev_parsed_coords = None

    # Process <tr> rows
    all_rows = container.select(".eaip-row")
    for i, tr in enumerate(all_rows):
        if is_name_row(tr):
            raw_text = get_name_text(tr)
            # Clear and set the text for the element that was flagged
            elt = tr.find(lambda tag: tag.name in ['td', 'th'] and 'strong' in tag.get('class', []))
            if elt:
                elt.clear()
                elt.string = raw_text
            tr["class"] = tr.get("class", []) + ["highlighted"]
            # Use new helper to create parsed name row
            name_tr = create_parsed_name_row(raw_text)
            tr.insert_after(name_tr)
        else:
            # Content row: must have 5 cells
            tds = tr.find_all("td")
            if len(tds) == 5:
                # First cell: Extract raw text from first cell and split by ' - '
                first_cell = tds[0]
                cell_text = first_cell.get_text(" ", strip=True)
                # Use the common compute_array_str helper
                array_str = compute_array_str(cell_text, prev_parsed_coords)
                # Use the new helper to create parsed row
                other_texts = [" ".join(td.stripped_strings) for td in tds[1:]]
                new_tr = create_parsed_row(array_str, other_texts)
                tr.insert_after(new_tr)
                # Update previous parsed coordinates
                prev_parsed_coords = array_str

    return container



def process_table_1(container):
    update_header(container, 1)
    prev_parsed_coords = None
    all_rows = container.select(".eaip-row")
    for i, tr in enumerate(all_rows):
        if is_name_row(tr):
            raw_text = get_name_text(tr)
            if raw_text == "LTA FRANCE partie 2":
                tr["class"] = tr.get("class", []) + ["rejected"]
                # Reject the next row if it exists (assumed content row)
                if i + 1 < len(all_rows):
                    next_tr = all_rows[i + 1]
                    next_tr["class"] = next_tr.get("class", []) + ["rejected"]
            else:
                process_name_row(tr)
                
            continue
        else:
            if len(tr.find_all("td")) == 5 and "rejected" not in tr.get("class", []):
                prev_parsed_coords = process_content_row(tr, 5, prev_parsed_coords)
    return container


def process_table_2(container):
    update_header(container, 2)

    # Pre-pass: Create name rows for 5-cell rows with text before coordinates
    all_rows = container.select(".eaip-row")
    for tr in all_rows:
        tds = tr.find_all("td")
        if len(tds) == 5:
            first_td = tds[0]
            full_text = " ".join(first_td.stripped_strings)
            coord_match = re.search(r"\d{2}°\d{2}(?:'|’)\d{2}(?:\"|”)[NSEW]", full_text)

            # Debugging prints
            # print(f"Raw text: '{full_text}'")
            if coord_match:
                coord_start = coord_match.start()
                # print(f"Found regex at: {coord_start}")
                if coord_start > 0:  # Text before coordinate exists
                    found_name = full_text[:coord_start].strip()
                    # print(f"Found name: '{found_name}'")
                    # Create parsed name row just before the current row
                    name_tr = soup.new_tag("tr")
                    name_tr["class"] = ["eaip-row", "parsed-name"]
                    name_td = soup.new_tag("td")
                    name_td.string = found_name
                    name_tr.append(name_td)
                    tr.insert_before(name_tr)

                    # Remove name from first cell, keep only coordinate text
                    coord_text = full_text[coord_start:]
                    first_td.clear()
                    first_td.string = coord_text
            else:
                # print("No coordinate pattern found")
                pass

    # Track previous non-name row's parsed coordinates
    prev_parsed_coords = None
    ta_info = "33"  # Default sentinel value

    # Main pass: Process <tr> rows
    all_rows = container.select(".eaip-row")  # Refresh after insertions
    for i, tr in enumerate(all_rows):
        tds = tr.find_all("td")

        # Handle 2-cell rows
        if len(tds) == 2:
            second_cell_text = " ".join(tds[1].stripped_strings)
            if "TA" in second_cell_text.upper():
                ta_info = second_cell_text
            else:
                ta_info = "33"
            tr["class"] = tr.get("class", []) + ["rejected"]
            continue

        # Process 5-cell rows (content)
        if len(tds) == 5 and "parsed-name" not in tr.get("class", []):
            first_cell = tds[0]
            cell_text = first_cell.get_text(" ", strip=True)
            array_str = compute_array_str(cell_text, prev_parsed_coords)
            other_texts = []
            for j, td in enumerate(tds[1:]):
                raw_text = " ".join(td.stripped_strings)
                if j == 3 and ta_info != "33":
                    other_texts.append(f"{ta_info} {raw_text}" if raw_text else ta_info)
                else:
                    other_texts.append(raw_text)
            new_tr = create_parsed_row(array_str, other_texts)
            tr.insert_after(new_tr)

            # Update previous parsed coordinates
            prev_parsed_coords = array_str

    return container


# Refactor process_table_3 to use helper functions

def process_table_3(container):
    update_header(container, 3)
    prev_parsed_coords = None
    all_rows = container.select(".eaip-row")
    for i, tr in enumerate(all_rows):
        if is_name_row(tr):
            process_name_row(tr)
        else:
            if len(tr.find_all("td")) == 5:
                prev_parsed_coords = process_content_row(tr, 5, prev_parsed_coords)
    return container


def process_table_4(container):
    update_header(container, 4)
    prev_parsed_coords = None
    all_rows = container.select(".eaip-row")
    for i, tr in enumerate(all_rows):
        if is_name_row(tr):
            process_name_row(tr)
            continue
        else:
            if len(tr.find_all("td")) == 4:
                prev_parsed_coords = process_content_row(tr, 4, prev_parsed_coords)
    return container


def process_table_5(container):
    update_header(container, 5)

    # Track previous non-name row's parsed coordinates
    prev_parsed_coords = None

    # Process <tr> rows
    all_rows = container.select(".eaip-row")
    for i, tr in enumerate(all_rows):
        # Check if this is a name row based on having exactly 2 cells
        tds = tr.find_all("td")
        if len(tds) == 2:
            tr["class"] = tr.get("class", []) + ["highlighted"]

            # Combine raw text from both cells
            combined_text = " ".join(
                td.get_text(" ", strip=True) for td in tds)
            # Create a new parsed name row
            name_tr = soup.new_tag("tr")
            name_tr["class"] = ["eaip-row", "parsed-name"]
            name_td = soup.new_tag("td")
            name_td.string = combined_text
            name_tr.append(name_td)
            tr.insert_after(name_tr)
            continue

        else:
            # Content row: must have 5 cells
            tds = tr.find_all("td")
            if len(tds) == 5:
                # First cell: Extract raw text from first cell and split by ' - '
                first_cell = tds[0]
                cell_text = first_cell.get_text(" ", strip=True)
                array_str = compute_array_str(cell_text, prev_parsed_coords)
                other_texts = [" ".join(td.stripped_strings) for td in tds[1:]]
                new_tr = create_parsed_row(array_str, other_texts)
                tr.insert_after(new_tr)
                # Update previous parsed coordinates
                prev_parsed_coords = array_str



    return container


# Refactor process_table_6 to use helper functions

def process_table_6(container):
    update_header(container, 6)
    prev_parsed_coords = None
    all_rows = container.select(".eaip-row")
    for i, tr in enumerate(all_rows):
        if is_name_row(tr):
            raw_text = get_name_text(tr)
            tr["class"] = tr.get("class", []) + ["highlighted"]
            name_tr = create_parsed_name_row(raw_text)
            tr.insert_after(name_tr)
        else:
            if len(tr.find_all("td")) == 5:
                prev_parsed_coords = process_content_row(tr, 5, prev_parsed_coords)
    return container


def process_table_7(container):
    update_header(container, 7)

    # Pre-pass: Create name rows for 3-cell rows with text before coordinates
    all_rows = container.select(".eaip-row")
    for tr in all_rows:
        tds = tr.find_all("td")
        if len(tds) == 3:
            first_td = tds[0]

            full_text = " ".join(first_td.stripped_strings)

            if not full_text.strip():
                tr["class"] = tr.get("class", []) + ["rejected"]

            coord_match = re.search(r"Cercle|Secteur|(\d{2}°\d{2}(?:'|’)\d{2}(?:\"|”)[NSEW])|(\d{6}[NSEW])|(\d{6} [NSEW])", full_text)

            # Debugging prints
            # print(f"Raw text: '{full_text}'")
            if coord_match:
                coord_start = coord_match.start()
                # print(f"Found regex at: {coord_start}")
                if coord_start > 0:  # Text before coordinate exists
                    found_name = full_text[:coord_start].strip()
                    found_name = remove_control_characters(found_name)
                    #if  "LF-R " or "LF - R " in name   , replace with "LF R "
                    if "LF-R " in found_name or "LF - R " in found_name:
                        found_name = found_name.replace("LF-R ", "LF R ").replace("LF - R ", "LF R ")
                    if "LF-P " in found_name :
                        found_name = found_name.replace("LF-P ", "LF P ")
                    if "LF-D " in found_name :
                        found_name = found_name.replace("LF-D ", "LF D ")
                    # print(f"Found name: '{found_name}'")
                    # Create parsed name row just before the current row
                    name_tr = soup.new_tag("tr")
                    name_tr["class"] = ["eaip-row", "parsed-name"]
                    name_td = soup.new_tag("td")
                    name_td.string = found_name
                    name_tr.append(name_td)
                    tr.insert_before(name_tr)

                    # Remove name from first cell, keep only coordinate text
                    coord_text = full_text[coord_start:]
                    first_td.clear()
                    first_td.string = coord_text
            else:
                # print("No coordinate pattern found")
                pass

    # Track previous non-name row's parsed coordinates
    prev_parsed_coords = None
    ta_info = "33"  # Default sentinel value
    lf_r_prefix = None  # To store the prefix from rows starting with "LF-R 213 NORD-EST"

    # Main pass: Process <tr> rows
    all_rows = container.select(".eaip-row")  # Refresh after insertions
    prev_name_text = ""
    for i, tr in enumerate(all_rows):
        tds = tr.find_all("td")

        # if rejected row, skip
        if "rejected" in tr.get("class", []):
            continue

        # if parsed name row, set previous name text to the name text
        if "parsed-name" in tr.get("class", []):
            prev_name_text = tds[0].get_text(" ", strip=True)
            # print(f"prev_name_text set to: {prev_name_text}")

        # process 3-cell row (name row): if cell 2 and 3 are empty, treat as name row
        if len(tds) == 3 and not list(tds[1].stripped_strings) and not list(tds[2].stripped_strings):
            # print("Name row detected")
            name_tr = soup.new_tag("tr")
            name_tr["class"] = ["eaip-row", "parsed-name"]
            name_td = soup.new_tag("td")
            found_name = tds[0].get_text(" ", strip=True)
            found_name = remove_control_characters(found_name)
            if "LF-R " in found_name or "LF - R " in found_name:
                found_name = found_name.replace("LF-R ", "LF R ").replace("LF - R ", "LF R ")
            if "LF-P " in found_name :
                found_name = found_name.replace("LF-P ", "LF P ")
            if "LF-D " in found_name :
                found_name = found_name.replace("LF-D ", "LF D ")
            # print(f"Found name: '{found_name}'")
            name_td.string = found_name
            prev_name_text = name_td.string
            # print(f"prev_name_text set to: {prev_name_text}")
            name_tr.append(name_td)
            tr.insert_after(name_tr)
            continue
        

        # Process 3-cell rows (content)
        if len(tds) == 3 and "parsed-name" not in tr.get("class", []):
            first_cell = tds[0]
            cell_text = first_cell.get_text(" ", strip=True)

            # Check if first cell starts with the specific string
            if cell_text.startswith("LF-R 213 NORD-EST"):
                # Obtain prefix from the third cell of this row
                current_prefix = tds[2].get_text(" ", strip=True)
                if not lf_r_prefix:
                    lf_r_prefix = current_prefix
                # set this row's class to deleted
                tr["class"] = tr.get("class", []) + ["rejected"]
                continue

            if not cell_text:
                # Use previous non-name row's parsed coordinates if available and previous row is not a name row
                if prev_parsed_coords and i > 0:
                    prev_tr = all_rows[i - 1]
                    if len(prev_tr.find_all("td")) == 3 and "parsed-name" not in prev_tr.get("class", []):
                        array_str = prev_parsed_coords
                    else:
                        array_str = "[]"
                else:
                    array_str = "[]"
            else:
                array_str = format_coords(cell_text)

            # Create new parsed row with eaip-row class
            other_texts = []
            for j, td in enumerate(tds[1:]):
                raw_text = " ".join(td.stripped_strings).strip()
                if j == 0:
                    print(raw_text)
                    # For cell index 1, insert ' ------------ ' just after the first <p> tag
                    original_html = td.decode_contents()
                    inner_soup = BeautifulSoup(original_html, "html.parser")
                    first_p = inner_soup.find("p")
                    first_span = inner_soup.find("span")
                    if first_span:
                        first_span.insert_after(" ------------ ")
                    else:
                        first_p.insert_after(" ------------ ")
                    # convert inner_soup to raw text and clean it using the helper function
                    raw_text = inner_soup.get_text(" ", strip=True).strip()
                    raw_text = remove_control_characters(raw_text)
                    print(raw_text)
                    other_texts.append(raw_text)
                elif j == 1 and prev_name_text.startswith("LF-R 213 NORD-EST") and lf_r_prefix:
                    raw_text = " ".join(td.stripped_strings).strip()
                    other_texts.append(lf_r_prefix + " " + raw_text if raw_text else lf_r_prefix)
                else:
                    other_texts.append(raw_text)

            new_tr = create_parsed_row(array_str, other_texts)
            tr.insert_after(new_tr)

            # Update previous parsed coordinates
            prev_parsed_coords = array_str

    return container


# Refactor process_table_8 to use helper functions

def process_table_8(container):
    update_header(container, 8)
    prev_parsed_coords = None
    all_rows = container.select(".eaip-row")
    for i, tr in enumerate(all_rows):
        tds = tr.find_all("td")
        if len(tds) == 2:
            tr["class"] = tr.get("class", []) + ["highlighted"]
            combined_text = " ".join(td.get_text(" ", strip=True) for td in tds)
            name_tr = soup.new_tag("tr")
            name_tr["class"] = ["eaip-row", "parsed-name"]
            name_td = soup.new_tag("td")
            name_td.string = combined_text
            name_tr.append(name_td)
            tr.insert_after(name_tr)
            continue
        else:
            if len(tds) == 5:
                prev_parsed_coords = process_content_row(tr, 5, prev_parsed_coords)
    return container


# Refactor process_table_9 to use helper functions

def process_table_9(container):
    update_header(container, 9)
    prev_parsed_coords = None
    all_rows = container.select(".eaip-row")
    for i, tr in enumerate(all_rows):
        if is_name_row(tr):
            process_name_row(tr)
        else:
            if len(tr.find_all("td")) == 5:
                prev_parsed_coords = process_content_row(tr, 5, prev_parsed_coords)
    return container


def process_table_10(container):
    update_header(container, 10)


    # Get all rows
    all_rows = [row for row in container.select(".eaip-row") if row.find("th") is None]
    # Process rows in pairs: even row holds info, odd row holds content
    i = 0
    while i < len(all_rows) - 1:
        info_row = all_rows[i]
        content_row = all_rows[i+1]

        # Extract tds from info row
        info_tds = info_row.find_all("td")
        if len(info_tds) < 3:
            i += 2
            continue

        # Even row: second cell is name (ignored), third cell holds upper altitude
        # name is content of cell 0 and cell 1
        name_text = " ".join(info_tds[0].stripped_strings) + " " + " ".join(info_tds[1].stripped_strings)
        # Transform 'parachutage' into 'para' (case insensitive) and remove 'Aérodrom' and any text after that
        name_text = re.sub(r'(?i)parachutage', 'para', name_text)
        name_text = re.sub(r'Aérodrome.*', '', name_text)
        name_text = name_text.strip()
        # Extract raw text for name row, ignoring <span> structure
        all_rows[i]["class"] = all_rows[i].get("class", []) + ["highlighted"]
        # Create a new parsed name row
        name_tr = soup.new_tag("tr")
        name_tr["class"] = ["eaip-row", "parsed-name"]
        name_td = soup.new_tag("td")
        name_td.string = name_text
        name_tr.append(name_td)
        info_row.insert_after(name_tr)
        
        upper_alt = info_tds[2].get_text(" ", strip=True)
        hor_val = info_tds[3].get_text(" ", strip=True)

        # Process content row
        content_tds = content_row.find_all("td")
        if len(content_tds) < 3:
            i += 2
            continue

        # First cell: coordinates parsing as in other tables
        coord_text = content_tds[0].get_text(" ", strip=True)
        if coord_text:
            array_str = format_coords(coord_text)
        else:
            array_str = "[]"

        # Second cell: lower altitude, prepend upper_alt
        lower_alt = content_tds[1].get_text(" ", strip=True)
        new_lower = (upper_alt + " ------------ " + lower_alt).strip() if lower_alt else upper_alt

        # Third cell: parse as usual but prepend hor_val
        third_text = content_tds[2].get_text(" ", strip=True)
        new_third = (hor_val + " " + third_text).strip() if third_text else hor_val

        # Create new parsed row
        other_texts = [new_lower, new_third]
        new_tr = create_parsed_row(array_str, other_texts)

        # Insert the new parsed row after the content row
        content_row.insert_after(new_tr)

        i += 2

    return container

def process_table_11(container):
    update_header(container, 11)


    # Get all rows
    all_rows = container.select(".eaip-row")
    # Process rows in pairs: even row holds info, odd row holds content
    i = 1
    while i < len(all_rows) - 1:
        name_row = all_rows[i]
        content_row = all_rows[i+1]

        name_tds = name_row.find_all("td")
        # print(len(name_tds))
        if len(name_tds) == 0:
            # print("No name row")
            i += 2
            continue
        # name is content of cell 0 and cell 1
        name_text = " ".join(name_tds[0].stripped_strings)
        # print(name_text)
        all_rows[i]["class"] = all_rows[i].get("class", []) + ["highlighted"]
        # Create a new parsed name row
        name_tr = soup.new_tag("tr")
        name_tr["class"] = ["eaip-row", "parsed-name"]
        name_td = soup.new_tag("td")
        name_td.string = name_text
        name_tr.append(name_td)
        name_row.insert_after(name_tr)
        

        # Process content row
        content_tds = content_row.find_all("td")
        # if len(content_tds) < 4:
        #     i += 2
        #     continue

        # First cell: coordinates parsing as in other tables
        coord_text = content_tds[0].get_text(" ", strip=True)
        if coord_text:
            array_str = format_coords(coord_text)
        else:
            array_str = "[]"

        # Create new parsed row
        other_texts = [" ".join(td.stripped_strings) for td in content_tds[1:]]
        new_tr = create_parsed_row(array_str, other_texts)

        # Insert the new parsed row after the content row
        content_row.insert_after(new_tr)

        i += 2

    return container


# Refactor process_table_12 to use helper functions

def process_table_12(container):
    update_header(container, 12)
    prev_parsed_coords = None
    all_rows = container.select(".eaip-row")
    for i, tr in enumerate(all_rows):
        if is_name_row(tr):
            process_name_row(tr)
        else:
            if len(tr.find_all("td")) == 5:
                prev_parsed_coords = process_content_row(tr, 5, prev_parsed_coords)
    return container


# Add more as needed based on your selected tables count
# Map table numbers to processing functions
table_processors = {
    0: process_table_0,
    1: process_table_1,
    2: process_table_2,
    3: process_table_3,
    4: process_table_4,
    5: process_table_5,
    6: process_table_6,
    7: process_table_7,
    8: process_table_8,
    9: process_table_9,
    10: process_table_10,
    11: process_table_11,
    12: process_table_12,

    # Extend this as needed
}

# Extract all table containers
containers = soup.select(".table-container")

# Process all containers (each table has one container) and process using the appropriate table processor
processed_containers = []
for container in containers:
    h3 = container.find("h3")
    if h3:
        # Assume h3.text format is 'Table number: X'
        try:
            table_number = int(h3.text.split(":")[1].strip())
        except Exception:
            table_number = None
        if table_number is not None and table_number in table_processors:
            processor = table_processors[table_number]
            processed_container = processor(container)
            processed_containers.append(processed_container)
        else:
            print(
                f"WARNING: Table number {table_number} not found in table_processors - Table will be missing")
    else:
        # Append container even without h3
        processed_containers.append(container)

# Create new HTML with only Table 0, keeping collapsible functionality
html_content = "<!DOCTYPE html>\n<html>\n<head>\n"
html_content += "<meta charset=\"UTF-8\">\n"
html_content += "<title>eAIP Selected Tables Stage 1</title>\n"

# CSS with collapsible functionality and highlighting
html_content += "<style>\n"
html_content += "  body { font-family: Arial, sans-serif; }\n"
html_content += "  .eaip-table { display: block; margin-bottom: 20px; width: 100%; transition: max-height 0.3s ease; }\n"
html_content += "  .eaip-row { display: flex; max-height: 80px; overflow: hidden; transition: max-height 0.3s ease; cursor: pointer; }\n"
html_content += "  .eaip-row.expanded { max-height: none; }\n"
html_content += "  .eaip-table.collapsed { max-height: 150px; overflow: hidden; }\n"
html_content += "  .eaip-row td, .eaip-row th { flex: 1; padding: 5px; border: 1px solid black; box-sizing: border-box; }\n"
html_content += "  .table-container { position: relative; margin: 20px; }\n"
html_content += "  .table-buttons { position: absolute; top: 0; right: 0; display: flex; gap: 5px; }\n"
html_content += "  .table-buttons button { padding: 5px 10px; cursor: pointer; }\n"
# Light green for highlighted rows
html_content += "  .eaip-row.highlighted { background-color: #90ee90; }\n"
html_content += "  .parsed-row { font-size: 12px; font-family: arial; }\n"
html_content += "  .parsed-name { font-size: 12px; font-family: arial; }\n"
html_content += "  .highlight-span { background-color: yellow; }\n"
# Red for rejected rows
html_content += "  .rejected { background-color: #ff0000; }\n"
html_content += "  h3 { font-size: 1.2em; margin-bottom: 10px; }\n"
html_content += "</style>\n"

# JavaScript for collapsing/expanding rows and tables
html_content += "<script>\n"
html_content += "  document.addEventListener('DOMContentLoaded', function() {\n"
html_content += "    var rows = document.querySelectorAll('.eaip-row');\n"
html_content += "    var tables = document.querySelectorAll('.eaip-table');\n"
html_content += "    // Row-level toggling\n"
html_content += "    rows.forEach(function(row) {\n"
html_content += "      row.addEventListener('click', function() {\n"
html_content += "        this.classList.toggle('expanded');\n"
html_content += "      });\n"
html_content += "    });\n"
html_content += "    // Per-table expand all rows\n"
html_content += "    document.querySelectorAll('.expand-rows-btn').forEach(function(button) {\n"
html_content += "      button.addEventListener('click', function() {\n"
html_content += "        var table = this.closest('.table-container').querySelector('.eaip-table');\n"
html_content += "        table.querySelectorAll('.eaip-row').forEach(function(row) {\n"
html_content += "          row.classList.add('expanded');\n"
html_content += "        });\n"
html_content += "      });\n"
html_content += "    });\n"
html_content += "    // Per-table collapse all rows\n"
html_content += "    document.querySelectorAll('.collapse-rows-btn').forEach(function(button) {\n"
html_content += "      button.addEventListener('click', function() {\n"
html_content += "        var table = this.closest('.table-container').querySelector('.eaip-table');\n"
html_content += "        table.querySelectorAll('.eaip-row').forEach(function(row) {\n"
html_content += "          row.classList.remove('expanded');\n"
html_content += "        });\n"
html_content += "      });\n"
html_content += "    });\n"
html_content += "    // Per-table collapse table\n"
html_content += "    document.querySelectorAll('.collapse-table-btn').forEach(function(button) {\n"
html_content += "      button.addEventListener('click', function() {\n"
html_content += "        var table = this.closest('.table-container').querySelector('.eaip-table');\n"
html_content += "        table.classList.add('collapsed');\n"
html_content += "      });\n"
html_content += "    });\n"
html_content += "    // Per-table expand table\n"
html_content += "    document.querySelectorAll('.expand-table-btn').forEach(function(button) {\n"
html_content += "      button.addEventListener('click', function() {\n"
html_content += "        var table = this.closest('.table-container').querySelector('.eaip-table');\n"
html_content += "        table.classList.remove('collapsed');\n"
html_content += "      });\n"
html_content += "    });\n"
html_content += "  });\n"
html_content += "</script>\n"

html_content += "</head>\n<body>\n"

# Add only Table 0
for container in processed_containers:
    html_content += str(container) + "\n"

html_content += "</body>\n</html>"

# Save to new file
output_file = "eaip_selected_tables_stage1.html"
with open(output_file, "w", encoding="utf-8") as f:
    f.write(html_content)
print(f"Saved {len(processed_containers)} tables to '{output_file}'")
