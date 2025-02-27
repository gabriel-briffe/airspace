import requests
from bs4 import BeautifulSoup
import json
import re


urls =[
    # ("FR-ENR-2.1", "https://www.sia.aviation-civile.gouv.fr/dvd/eAIP_20_FEB_2025/FRANCE/AIRAC-2025-02-20/html/eAIP/FR-ENR-2.1-fr-FR.html#ENR-2",[0,1,2]),
    # ("FR-ENR-2.2", "https://www.sia.aviation-civile.gouv.fr/dvd/eAIP_20_FEB_2025/FRANCE/AIRAC-2025-02-20/html/eAIP/FR-ENR-2.2-fr-FR.html",[0,10]),
    ("FR-ENR-5.1", "https://www.sia.aviation-civile.gouv.fr/dvd/eAIP_20_FEB_2025/FRANCE/AIRAC-2025-02-20/html/eAIP/FR-ENR-5.1-fr-FR.html#ENR-5.1-1",[4,8, 49])
]

airspaces = []
for url in urls:
    # Fetch the page
    response = requests.get(url[1])
    print(f"Status code: {response.status_code}")
    if response.status_code != 200:
        print("Failed to fetch page. Check URL.")
        exit()

    # Parse the HTML
    soup = BeautifulSoup(response.content, "html.parser")

    # Find all <tbody> elements
    tbody_elements = soup.find_all("tbody")
    if not tbody_elements:
        print("No <tbody> elements found on the page.")
        exit()
    print(f"Found {len(tbody_elements)} <tbody> elements")

    # Process <tbody> content into JSON
    if url[0] == "FR-ENR-2.1" or url[0] == "FR-ENR-2.2":
        for tbody in tbody_elements:

            #if not index of tbody in url[2]
            if tbody_elements.index(tbody) not in url[2]:
                continue

            rows = tbody.find_all("tr")
            # If no rows (since this is a mock), use the <td> directly for testing
            if not rows:
                cells = tbody.find_all("td")
                if not cells:
                    continue
                coords_td = cells[0]
            else:
                current_name = ""
                current_coordinates = ""
                # Compile a regex pattern for coordinates like 46°45'00" (optional double quote at the end)
                coord_pattern = re.compile(r"\d+°\d+'\d+\"?")
                # Iterate over each row individually
                for row in rows:
                    cells = row.find_all("td")
                    if not cells:
                        continue

                    # Get the text from the first cell
                    first_cell_text = " ".join(cells[0].stripped_strings)
                    
                    # If the first cell is not empty and does not contain a coordinate,
                    # treat this row as a name row.
                    if first_cell_text and not coord_pattern.search(first_cell_text):
                        current_name = first_cell_text
                        if tbody_elements.index(tbody) in url[2]:
                            print(current_name)
                        continue  # Skip further processing of this row
                    
                    # Otherwise, assume the row is a details row;
                    # it should have exactly 5 cells.
                    if len(cells) not in [4,5]:
                        print(f"Skipping a row: Expected 4 or5 cells, found {len(cells)}")
                        print(cells)
                        continue

                    if len(cells) == 5:
                        # Extract coordinates and other details from the cells
                        coordinates = " ".join(cells[0].stripped_strings)
                        airspace_class = " ".join(cells[1].stripped_strings)
                        limits = " ".join(cells[2].stripped_strings)
                        radio = " ".join(cells[3].stripped_strings)
                        remarks = " ".join(cells[4].stripped_strings)

                        if coordinates == "":
                            coordinates = current_coordinates
                        else:
                            current_coordinates = coordinates

                        if coordinates == "":
                            print("no coordinates")

                        airspaces.append({
                            "name": current_name,
                            "coordinates": coordinates,
                            "class": airspace_class,
                            "limits": limits,
                            "radio": radio,
                            "remarks": remarks
                        })
                    
                    if len(cells) == 4:
                        
                        coordinates = " ".join(cells[0].stripped_strings)
                        # airspace_class = " ".join(cells[1].stripped_strings)
                        limits = " ".join(cells[1].stripped_strings)
                        radio = " ".join(cells[2].stripped_strings)
                        remarks = " ".join(cells[3].stripped_strings)

                        if coordinates == "":
                            coordinates = current_coordinates
                        else:
                            current_coordinates = coordinates

                        if coordinates == "":
                            print("no coordinates")

                        airspaces.append({
                            "name": current_name,
                            # "coordinates": coordinates,
                            "class": airspace_class,
                            "limits": limits,
                            "radio": radio,
                            "remarks": remarks
                        })

    elif url[0] == "FR-ENR-5.1":
        for tbody in tbody_elements:

            #if not index of tbody in url[2]
            # if tbody_elements.index(tbody) not in url[2]:
            #     continue

            rows = tbody.find_all("tr")
            # If no rows (since this is a mock), use the <td> directly for testing
            if not rows:
                cells = tbody.find_all("td")
                if not cells:
                    continue
                coords_td = cells[0]
            else:
                current_name = ""
                current_coordinates = ""
                # Compile a regex pattern for coordinates like 46°45'00" (optional double quote at the end)
                coord_pattern = re.compile(r"\d+°\d+'\d+\"?")
                # Iterate over each row individually
                for row in rows:
                    cells = row.find_all("td")
                    if not cells:
                        continue

                    # Get the text from the first cell
                    first_cell_text = " ".join(cells[0].stripped_strings)
                    if tbody_elements.index(tbody) not in url[2]:
                        print("table number: ", tbody_elements.index(tbody))
                        print ( first_cell_text)
                    if tbody_elements.index(tbody) not in url[2]:
                        break

                    if first_cell_text and first_cell_text.startswith("("):
                        # add this row to skippedrows
                        continue
                    # If the first cell is not empty and does not contain a coordinate,
                    # treat this row as a name row.
                    if first_cell_text and not coord_pattern.search(first_cell_text):
                        current_name = first_cell_text
                        if tbody_elements.index(tbody) in url[2]:
                            print(current_name)
                        continue  # Skip further processing of this row
                    
                    # Otherwise, assume the row is a details row;
                    # it should have exactly 5 cells.
                    if len(cells) not in [5,3]:
                        print(f"Skipping a row: Expected 3 or 5 cells, found {len(cells)}")
                        print(cells)
                        continue

                    if len(cells) == 5:
                        # Extract coordinates and other details from the cells
                        coordinates = " ".join(cells[0].stripped_strings)
                        limits = " ".join(cells[1].stripped_strings)
                        hor = " ".join(cells[2].stripped_strings)
                        restriction = " ".join(cells[3].stripped_strings)
                        remarks = " ".join(cells[4].stripped_strings)

                        if coordinates == "":
                            coordinates = current_coordinates
                        else:
                            current_coordinates = coordinates

                        if coordinates == "":
                            print("no coordinates")

                        airspaces.append({
                            "name": current_name,
                            "coordinates": coordinates,
                            "limits": limits,
                            "hor": hor,
                            "restriction": restriction,
                            "remarks": remarks
                        })
                    
                    if len(cells) == 3:
                                            # Extract coordinates and other details from the cells
                        coordinates = " ".join(cells[0].stripped_strings)
                        limits = " ".join(cells[1].stripped_strings)
                        restriction = " ".join(cells[2].stripped_strings)

                        if coordinates == "":
                            coordinates = current_coordinates
                        else:
                            current_coordinates = coordinates

                        if coordinates == "":
                            print("no coordinates")

                        airspaces.append({
                            "name": current_name,
                            "limits": limits,
                            "restriction": restriction,
                        })



# Save <tbody> content as JSON
with open("FR-ENR-2.1.json", "w", encoding="utf-8") as f:
    json.dump(airspaces, f, ensure_ascii=False, indent=2)
print("Saved <tbody> content to 'tbody_content.json'")

# Create leftovers: Visible text with basic layout
leftovers = BeautifulSoup(response.content, "html.parser")
for tbody in leftovers.find_all("tbody"):
    tbody.decompose()

def extract_text_with_layout(soup):
    lines = []
    for element in soup.descendants:
        if isinstance(element, str):
            text = element.strip()
            if text:
                lines.append(text)
        elif element.name == "br":
            lines.append("\n")
        elif element.name in ["div", "p", "h1", "h2", "h3", "h4", "h5", "h6"]:
            if lines and lines[-1] != "\n":
                lines.append("\n")
        elif element.name == "span":
            if lines and lines[-1] != "\n" and lines[-1] != " ":
                lines.append(" ")
    result = ""
    for i, line in enumerate(lines):
        if line == "\n":
            result += line
        elif line == " " and i > 0 and lines[i-1] != "\n":
            result += line
        elif i > 0 and lines[i-1] != "\n" and lines[i-1] != " ":
            result += " " + line
        else:
            result += line
    return result.strip()

visible_text = extract_text_with_layout(leftovers)

# Save leftovers as plain text with layout
with open("leftovers.txt", "w", encoding="utf-8") as f:
    f.write(visible_text)
print("Saved visible text leftovers to 'leftovers.txt'")