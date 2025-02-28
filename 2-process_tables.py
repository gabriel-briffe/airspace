from bs4 import BeautifulSoup

# Load eaip_selected_tables.html
with open("eaip_selected_tables.html", "r", encoding="utf-8") as f:
    soup = BeautifulSoup(f, "html.parser")


def process_table_0(container):
    # Update table number
    h3 = container.find("h3")
    if h3:
        h3.string = "Table number: 0"

    # Track previous non-name row's parsed coordinates
    prev_parsed_coords = None

    # Process <tr> rows
    all_rows = container.select(".eaip-row")
    for i, tr in enumerate(all_rows):
        # Check if this is a name row (has "strong" in any <td> or <th>)
        name_td = tr.find(lambda tag: tag.name in [
                          "td", "th"] and "strong" in tag.get("class", []))
        if name_td:
            # Extract raw text for name row, ignoring <span> structure
            raw_text = " ".join(name_td.stripped_strings)
            name_td.clear()
            name_td.string = raw_text
            tr["class"] = tr.get("class", []) + ["highlighted"]
        else:
            # Content row: must have 5 cells
            tds = tr.find_all("td")
            if len(tds) == 5:
                # First cell: Extract raw text from first cell and split by ' - '
                first_cell = tds[0]
                cell_text = first_cell.get_text(" ", strip=True)
                if not cell_text:
                    # Use previous non-name row's parsed coordinates if available and previous row is not a name row
                    if prev_parsed_coords and i > 0:
                        prev_tr = all_rows[i - 1]
                        if not prev_tr.find(lambda tag: tag.name in ["td", "th"] and "strong" in tag.get("class", [])):
                            array_str = prev_parsed_coords
                        else:
                            array_str = "[]"
                    else:
                        array_str = "[]"
                else:
                    parts = cell_text.split(" - ")
                    parts = [part for part in parts if part.strip()]
                    array_str = "[" + \
                        ", ".join(f'\"{p}\"' for p in parts) + "]"

                # Create new parsed row with eaip-row class for consistent styling
                new_tr = soup.new_tag("tr")
                new_tr["class"] = ["eaip-row", "parsed-row"]

                # First cell: Array with (lat, lon) pairs and "Frontière" entries or copied coords
                new_td = soup.new_tag("td")
                new_td.string = array_str
                new_tr.append(new_td)

                # Remaining cells: Raw text from original <td>
                for td in tds[1:]:
                    raw_text = " ".join(td.stripped_strings)
                    new_td = soup.new_tag("td")
                    new_td.string = raw_text
                    new_tr.append(new_td)

                # Insert new row after the content row
                tr.insert_after(new_tr)

                # Update previous parsed coordinates
                prev_parsed_coords = array_str

    return container


def process_table_1(container):
    # Update table number
    h3 = container.find("h3")
    if h3:
        h3.string = "Table number: 1"

    # Track previous non-name row's parsed coordinates
    prev_parsed_coords = None

    # Process <tr> rows
    all_rows = container.select(".eaip-row")
    for i, tr in enumerate(all_rows):
        # Check if this is a name row (has "strong" in any <td> or <th>)
        name_td = tr.find(lambda tag: tag.name in [
                          "td", "th"] and "strong" in tag.get("class", []))
        if name_td:
            # Extract raw text for name row
            raw_text = " ".join(name_td.stripped_strings)
            name_td.clear()
            name_td.string = raw_text

            # Check if this is the row to reject
            if raw_text == "LTA FRANCE partie 2":
                tr["class"] = tr.get("class", []) + ["rejected"]
                # Reject the next row if it exists (assumed content row)
                if i + 1 < len(all_rows):
                    next_tr = all_rows[i + 1]
                    next_tr["class"] = next_tr.get("class", []) + ["rejected"]
            else:
                tr["class"] = tr.get("class", []) + ["highlighted"]
        else:
            # Content row: must have 5 cells and not rejected
            tds = tr.find_all("td")
            if len(tds) == 5 and "rejected" not in tr.get("class", []):
                # First cell: Extract raw text from first cell and split by ' - '
                first_cell = tds[0]
                cell_text = first_cell.get_text(" ", strip=True)
                if not cell_text:
                    # Use previous non-name row's parsed coordinates if available and previous row is not a name row
                    if prev_parsed_coords and i > 0:
                        prev_tr = all_rows[i - 1]
                        if not prev_tr.find(lambda tag: tag.name in ["td", "th"] and "strong" in tag.get("class", [])):
                            array_str = prev_parsed_coords
                        else:
                            array_str = "[]"
                    else:
                        array_str = "[]"
                else:
                    parts = cell_text.split(" - ")
                    parts = [part for part in parts if part.strip()]
                    array_str = "[" + \
                        ", ".join(f'\"{p}\"' for p in parts) + "]"

                # Create new parsed row with eaip-row class
                new_tr = soup.new_tag("tr")
                new_tr["class"] = ["eaip-row", "parsed-row"]

                # First cell: Array with (lat, lon) pairs and "Frontière" entries or copied coords
                new_td = soup.new_tag("td")
                new_td.string = array_str
                new_tr.append(new_td)

                # Remaining cells: Raw text from original <td>
                for td in tds[1:]:
                    raw_text = " ".join(td.stripped_strings)
                    new_td = soup.new_tag("td")
                    new_td.string = raw_text
                    new_tr.append(new_td)

                # Insert new row after the content row
                tr.insert_after(new_tr)

                # Update previous parsed coordinates
                prev_parsed_coords = array_str

    return container


def process_table_2(container):
    # Update table number
    h3 = container.find("h3")
    if h3:
        h3.string = "Table number: 2"

    import re
    # Pre-pass: Create name rows for 5-cell rows with text before coordinates
    all_rows = container.select(".eaip-row")
    for tr in all_rows:
        tds = tr.find_all("td")
        if len(tds) == 5:
            first_td = tds[0]
            full_text = " ".join(first_td.stripped_strings)
            coord_match = re.search(r"\d{2}°\d{2}'\d{2}\"[NSEW]", full_text)

            # Debugging prints
            print(f"Raw text: '{full_text}'")
            if coord_match:
                coord_start = coord_match.start()
                print(f"Found regex at: {coord_start}")
                if coord_start > 0:  # Text before coordinate exists
                    found_name = full_text[:coord_start].strip()
                    print(f"Found name: '{found_name}'")
                    # Create parsed name row just before the current row
                    name_tr = soup.new_tag("tr")
                    name_tr["class"] = ["eaip-row", "parsed-name"]
                    name_td = soup.new_tag("td")
                    name_td.string = found_name
                    name_tr.append(name_td)
                    for _ in range(4):
                        empty_td = soup.new_tag("td")
                        name_tr.append(empty_td)
                    tr.insert_before(name_tr)

                    # Remove name from first cell, keep only coordinate text
                    coord_text = full_text[coord_start:]
                    first_td.clear()
                    first_td.string = coord_text
            else:
                print("No coordinate pattern found")

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
            if not cell_text:
                # Use previous non-name row's parsed coordinates if available and previous row is not a name row
                if prev_parsed_coords and i > 0:
                    prev_tr = all_rows[i - 1]
                    if len(prev_tr.find_all("td")) == 5 and "parsed-name" not in prev_tr.get("class", []):
                        array_str = prev_parsed_coords
                    else:
                        array_str = "[]"
                else:
                    array_str = "[]"
            else:
                parts = cell_text.split(" - ")
                parts = [part for part in parts if part.strip()]
                array_str = "[" + ", ".join(f'\"{p}\"' for p in parts) + "]"
            
            # Create new parsed row with eaip-row class
            new_tr = soup.new_tag("tr")
            new_tr["class"] = ["eaip-row", "parsed-row"]
            
            # First cell: Array with (lat, lon) pairs and "Frontière" entries or copied coords
            new_td = soup.new_tag("td")
            new_td.string = array_str
            new_tr.append(new_td)
            
            # Remaining cells: Raw text from original <td>, prepend TA info to 5th cell if not sentinel
            for j, td in enumerate(tds[1:]):
                raw_text = " ".join(td.stripped_strings)
                new_td = soup.new_tag("td")
                if j == 3 and ta_info != "33":
                    new_td.string = f"{ta_info} {raw_text}" if raw_text else ta_info
                else:
                    new_td.string = raw_text
                new_tr.append(new_td)
            
            # Insert new row after the content row
            tr.insert_after(new_tr)
            
            # Update previous parsed coordinates
            prev_parsed_coords = array_str
    
    return container


def process_table_3(container):
    # Update table number
    h3 = container.find("h3")
    if h3:
        h3.string = "Table number: 3"
    
    # Track previous non-name row's parsed coordinates
    prev_parsed_coords = None
    
    # Process <tr> rows
    all_rows = container.select(".eaip-row")
    for i, tr in enumerate(all_rows):
        # Check if this is a name row (has "strong" in any <td> or <th>)
        name_td = tr.find(lambda tag: tag.name in ["td", "th"] and "strong" in tag.get("class", []))
        if name_td:
            # Extract raw text for name row, ignoring <span> structure
            raw_text = " ".join(name_td.stripped_strings)
            name_td.clear()
            name_td.string = raw_text
            tr["class"] = tr.get("class", []) + ["highlighted"]
        else:
            # Content row: must have 5 cells
            tds = tr.find_all("td")
            if len(tds) == 5:
                # First cell: Extract raw text from first cell and split by ' - '
                first_cell = tds[0]
                cell_text = first_cell.get_text(" ", strip=True)
                if not cell_text:
                    # Use previous non-name row's parsed coordinates if available and previous row is not a name row
                    if prev_parsed_coords and i > 0:
                        prev_tr = all_rows[i - 1]
                        if not prev_tr.find(lambda tag: tag.name in ["td", "th"] and "strong" in tag.get("class", [])):
                            array_str = prev_parsed_coords
                        else:
                            array_str = "[]"
                    else:
                        array_str = "[]"
                else:
                    parts = cell_text.split(" - ")
                    parts = [part for part in parts if part.strip()]
                    array_str = "[" + ", ".join(f'\"{p}\"' for p in parts) + "]"
                
                # Create new parsed row with eaip-row class for consistent styling
                new_tr = soup.new_tag("tr")
                new_tr["class"] = ["eaip-row", "parsed-row"]
                
                # First cell: Array with (lat, lon) pairs and "Frontière" entries or copied coords
                new_td = soup.new_tag("td")
                new_td.string = array_str
                new_tr.append(new_td)
                
                # Remaining cells: Raw text from original <td>
                for td in tds[1:]:
                    raw_text = " ".join(td.stripped_strings)
                    new_td = soup.new_tag("td")
                    new_td.string = raw_text
                    new_tr.append(new_td)
                
                # Insert new row after the content row
                tr.insert_after(new_tr)
                
                # Update previous parsed coordinates
                prev_parsed_coords = array_str
    
    return container






def process_table_4(container): return container
def process_table_5(container): return container
# Add more as needed based on your selected tables count

# Map table numbers to processing functions
table_processors = {
    0: process_table_0,
    1: process_table_1,
    2: process_table_2,
    3: process_table_3,
    # 4: process_table_4,
    # 5: process_table_5,
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
            print(f"WARNING: Table number {table_number} not found in table_processors - Table will be missing")
    else:
        processed_containers.append(container)  # Append container even without h3

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
html_content += "  .eaip-table.collapsed { max-height: 80px; overflow: hidden; }\n"
html_content += "  .eaip-row td, .eaip-row th { flex: 1; padding: 5px; border: 1px solid black; box-sizing: border-box; }\n"
html_content += "  .table-container { position: relative; margin: 20px; }\n"
html_content += "  .table-buttons { position: absolute; top: 0; right: 0; display: flex; gap: 5px; }\n"
html_content += "  .table-buttons button { padding: 5px 10px; cursor: pointer; }\n"
html_content += "  .eaip-row.highlighted { background-color: #90ee90; }\n"  # Light green for highlighted rows
html_content += "  .parsed-row { font-size: 12px; font-family: arial; }\n"  
html_content += "  .highlight-span { background-color: yellow; }\n"
html_content += "  .rejected { background-color: #ff0000; }\n"  # Red for rejected rows
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
print(f"Saved Table 0 to '{output_file}'")