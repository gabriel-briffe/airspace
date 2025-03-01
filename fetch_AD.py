import requests
from bs4 import BeautifulSoup
import os

# Base URL and starting page
base_url = "https://www.sia.aviation-civile.gouv.fr/dvd/eAIP_20_FEB_2025/FRANCE/AIRAC-2025-02-20/html/eAIP/"
start_url = base_url + "FR-menu-fr-FR.html"

# Headers to mimic a browser request
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

# Function to fetch and parse a webpage
def fetch_page(url):
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return BeautifulSoup(response.text, 'html.parser')
    else:
        print(f"Failed to fetch {url}: Status code {response.status_code}")
        return None

# Step 1: Get all AD-2.17 links from the menu page
soup = fetch_page(start_url)
if not soup:
    print("Could not fetch the menu page. Exiting.")
    exit()

ad_2_17_links = []
for link in soup.find_all('a', href=True):
    href = link['href']
    if href.endswith('AD-2.17'):
        full_url = base_url + href.split('#')[0] + "#" + href.split('#')[1] if '#' in href else base_url + href
        ad_2_17_links.append(full_url)

print(f"Found {len(ad_2_17_links)} AD-2.17 links.")

# Step 2: Fetch tables and process rows
combined_rows = []
single_row_tables = []
first_header = None

for url in ad_2_17_links:
    soup = fetch_page(url.split('#')[0])  # Fetch the page without the fragment
    if not soup:
        continue
    
    # Find the div with id ending in AD-2.17
    section_id = url.split('#')[-1]
    section_div = soup.find('div', id=section_id)
    if section_div:
        table = section_div.find('table')
        if table:
            # Extract the header (thead) if not already set
            thead = table.find('thead')
            if not first_header and thead:
                first_header = str(thead)
            
            # Extract the body (tbody) and its rows
            tbody = table.find('tbody')
            if tbody:
                rows = tbody.find_all('tr')
                aerodrome_code = section_id.split('-')[2]  # e.g., LFBA from LFBA-AD-2.17
                
                # Add aerodrome code as a new column to each row
                for row in rows:
                    row_soup = BeautifulSoup(str(row), 'html.parser')
                    # new_td = row_soup.new_tag('td')
                    # new_td.string = aerodrome_code
                    # row_soup.tr.insert(0, new_td)  # Insert at the beginning of the row
                    
                    if len(rows) > 1:
                        combined_rows.append(str(row_soup))
                    else:
                        # If table has only one row, store it separately with its aerodrome code
                        single_row_tables.append((aerodrome_code, str(row_soup)))
            else:
                print(f"No tbody found in {section_id} at {url}")
        else:
            print(f"No table found in {section_id} at {url}")
    else:
        print(f"Section {section_id} not found at {url}")

# Step 3: Build the combined HTML
combined_html = "<html><head><title>Combined CTR Tables</title></head><body>"
combined_html += "<h1>Combined CTR Tables (Multiple Rows)</h1>"

# Create the main table with all rows from tables with >1 row
if first_header and combined_rows:
    combined_html += "<table border='1'>"
    combined_html += first_header  # Add the common header
    combined_html += "<tbody>"
    combined_html += "".join(combined_rows)  # Add all collected rows
    combined_html += "</tbody></table>"

# Add separate tables for single-row cases
if single_row_tables:
    combined_html += "<h1>Single-Row CTR Tables</h1>"
    for aerodrome_code, row in single_row_tables:
        combined_html += f"<h2>{aerodrome_code} CTR</h2>"
        combined_html += "<table border='1'>"
        combined_html += first_header  # Reuse the same header
        combined_html += "<tbody>"
        combined_html += row
        combined_html += "</tbody></table>"

combined_html += "</body></html>"

# Step 4: Write to CTR.html
with open("CTR.html", "w", encoding="utf-8") as f:
    f.write(combined_html)

print("Combined CTR tables have been written to CTR.html")