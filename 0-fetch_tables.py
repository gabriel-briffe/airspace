import requests
from bs4 import BeautifulSoup

# List of URLs for eAIP pages
urls = [
    "https://www.sia.aviation-civile.gouv.fr/dvd/eAIP_20_FEB_2025/FRANCE/AIRAC-2025-02-20/html/eAIP/FR-ENR-2.1-fr-FR.html#ENR-2",
    "https://www.sia.aviation-civile.gouv.fr/dvd/eAIP_20_FEB_2025/FRANCE/AIRAC-2025-02-20/html/eAIP/FR-ENR-2.2-fr-FR.html",
    "https://www.sia.aviation-civile.gouv.fr/dvd/eAIP_20_FEB_2025/FRANCE/AIRAC-2025-02-20/html/eAIP/FR-ENR-5.1-fr-FR.html#ENR-5.1-1",
    "https://www.sia.aviation-civile.gouv.fr/dvd/eAIP_20_FEB_2025/FRANCE/AIRAC-2025-02-20/html/eAIP/FR-ENR-5.2-fr-FR.html#ENR-5.2-1",
    "https://www.sia.aviation-civile.gouv.fr/dvd/eAIP_20_FEB_2025/FRANCE/AIRAC-2025-02-20/html/eAIP/FR-ENR-5.5-fr-FR.html#ENR-5.5",
    "https://www.sia.aviation-civile.gouv.fr/dvd/eAIP_20_FEB_2025/FRANCE/AIRAC-2025-02-20/html/eAIP/FR-ENR-5.7-fr-FR.html#ENR-5.7-1"
]

# Pre-selected tables
selected_tables= [0, 1, 2, 3, 13, 18, 22, 63, 64, 66, 69, 72]
# Function to fetch tables from a URL


def extract_tables_from_url(url):
    try:
        response = requests.get(url)
        print(f"Fetching {url}: Status code {response.status_code}")
        if response.status_code != 200:
            print(f"Failed to fetch {url}")
            return []

        soup = BeautifulSoup(response.content, "html.parser")
        tables = soup.find_all("table")
        # Remove <del> tags from each table
        for table in tables:
            for del_tag in table.find_all("del"):
                del_tag.decompose()  # Removes the <del> tag and its content
        return tables
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return []


# Collect all tables from all URLs
all_tables = []
for url in urls:
    tables = extract_tables_from_url(url)
    all_tables.extend(tables)

# Generate new HTML with custom styles and labeled tables
html_content = "<!DOCTYPE html>\n<html>\n<head>\n"
html_content += "<meta charset=\"UTF-8\">\n"
html_content += "<title>eAIP Tables</title>\n"

# Add custom CSS
html_content += "<style>\n"
html_content += "  td[class*=\"strong\"], th[class*=\"strong\"] { font-weight: bold; }\n"
html_content += "  .eaip-table { display: block; margin-bottom: 20px; width: 100%; transition: max-height 0.3s ease; }\n"
html_content += "  .eaip-row { display: flex; max-height: 50px; overflow: hidden; transition: max-height 0.3s ease; cursor: pointer; }\n"
html_content += "  .eaip-row.expanded { max-height: none; }\n"
html_content += "  .eaip-table.collapsed { max-height: 80px; overflow: hidden; }\n"
html_content += "  .eaip-row td, .eaip-row th { flex: 1; padding: 5px; border: 1px solid black; box-sizing: border-box; }\n"
html_content += "  .table-container { position: relative; margin-bottom: 40px; }\n"
html_content += "  .table-buttons { position: absolute; top: 0; right: 0; display: flex; gap: 5px; }\n"
html_content += "  .table-buttons button { padding: 5px 10px; cursor: pointer; }\n"
html_content += "  .table-container.highlighted { background-color: #90ee90; }\n"
html_content += "  h3 { cursor: pointer; }\n"
html_content += "  .controls { margin: 10px 0; display: flex; gap: 10px; align-items: center; }\n"
html_content += "  .controls input { padding: 5px; width: 300px; }\n"
html_content += "  .controls button { padding: 5px 10px; cursor: pointer; }\n"
html_content += "</style>\n"

# Add JavaScript for row toggling, per-table controls, heading highlight, and top controls
html_content += "<script>\n"
html_content += "  document.addEventListener('DOMContentLoaded', function() {\n"
html_content += "    var rows = document.querySelectorAll('.eaip-row');\n"
html_content += "    var containers = document.querySelectorAll('.table-container');\n"
html_content += "    var tables = document.querySelectorAll('.eaip-table');\n"
html_content += "    var selectedField = document.getElementById('selected-tables');\n"
html_content += "    function updateSelectedField() {\n"
html_content += "      var selected = Array.from(containers)\n"
html_content += "        .filter(container => container.classList.contains('highlighted'))\n"
html_content += "        .map(container => parseInt(container.querySelector('h3').textContent.replace('Table number: ', '')));\n"
html_content += "      selectedField.value =  selected.join(', ');\n"
html_content += "    }\n"
html_content += "    // Initialize collapsed state and pre-selected tables\n"
html_content += "    tables.forEach(function(table) {\n"
html_content += "      table.classList.add('collapsed');\n"
html_content += "    });\n"
html_content += f"    var initialSelected = {selected_tables};\n"
html_content += "    containers.forEach(function(container, index) {\n"
html_content += "      if (initialSelected.includes(index)) {\n"
html_content += "        container.classList.add('highlighted');\n"
html_content += "      }\n"
html_content += "    });\n"
html_content += "    updateSelectedField();\n"
html_content += "    // Row-level toggling\n"
html_content += "    rows.forEach(function(row) {\n"
html_content += "      row.addEventListener('click', function() {\n"
html_content += "        this.classList.toggle('expanded');\n"
html_content += "      });\n"
html_content += "    });\n"
html_content += "    // Heading click to toggle highlight\n"
html_content += "    var headings = document.querySelectorAll('h3');\n"
html_content += "    headings.forEach(function(heading) {\n"
html_content += "      heading.addEventListener('click', function() {\n"
html_content += "        var container = this.closest('.table-container');\n"
html_content += "        container.classList.toggle('highlighted');\n"
html_content += "        updateSelectedField();\n"
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
html_content += "    // Expand all tables\n"
html_content += "    document.getElementById('expand-all-tables').addEventListener('click', function() {\n"
html_content += "      tables.forEach(function(table) {\n"
html_content += "        table.classList.remove('collapsed');\n"
html_content += "      });\n"
html_content += "    });\n"
html_content += "    // Collapse all tables\n"
html_content += "    document.getElementById('collapse-all-tables').addEventListener('click', function() {\n"
html_content += "      tables.forEach(function(table) {\n"
html_content += "        table.classList.add('collapsed');\n"
html_content += "      });\n"
html_content += "    });\n"
html_content += "    // Input field to select tables\n"
html_content += "    selectedField.addEventListener('change', function() {\n"
html_content += "      var input = this.value.replace('selected_tables: ', '').split(',').map(num => parseInt(num.trim())).filter(num => !isNaN(num));\n"
html_content += "      containers.forEach(function(container, index) {\n"
html_content += "        if (input.includes(index)) {\n"
html_content += "          container.classList.add('highlighted');\n"
html_content += "        } else {\n"
html_content += "          container.classList.remove('highlighted');\n"
html_content += "        }\n"
html_content += "      });\n"
html_content += "      updateSelectedField();\n"
html_content += "    });\n"
html_content += "  });\n"
html_content += "</script>\n"

html_content += "</head>\n<body>\n"

# Add top controls
html_content += "<div class=\"controls\">\n"
html_content += "  <input type=\"text\" id=\"selected-tables\" value=\"selected_tables: \" />\n"
html_content += "  <button id=\"expand-all-tables\">Expand All Tables</button>\n"
html_content += "  <button id=\"collapse-all-tables\">Collapse All Tables</button>\n"
html_content += "</div>\n"

# Add tables with per-table buttons
for index, table in enumerate(all_tables):
    # Add custom class to each <tr> for styling and toggling
    for tr in table.find_all("tr"):
        tr["class"] = tr.get("class", []) + ["eaip-row"]
    # Ensure table has eaip-table class
    table["class"] = table.get("class", []) + ["eaip-table"]
    html_content += "<div class=\"table-container\">\n"
    html_content += f"<h3>Table number: {index}</h3>\n"
    html_content += "<div class=\"table-buttons\">\n"
    html_content += "  <button class=\"expand-rows-btn\">Expand All Rows</button>\n"
    html_content += "  <button class=\"collapse-rows-btn\">Collapse All Rows</button>\n"
    html_content += "  <button class=\"collapse-table-btn\">Collapse Table</button>\n"
    html_content += "  <button class=\"expand-table-btn\">Expand Table</button>\n"
    html_content += "</div>\n"
    html_content += str(table) + "\n"
    html_content += "</div>\n"

html_content += "</body>\n</html>"

# Save to file
output_file = "eaip_tables.html"
with open(output_file, "w", encoding="utf-8") as f:
    f.write(html_content)
print(f"Saved {len(all_tables)} tables to '{output_file}'")
