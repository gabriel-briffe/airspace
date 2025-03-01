from bs4 import BeautifulSoup

# List of table numbers to keep (example input)
tables_to_keep = [0, 1, 2, 3, 13, 18, 22, 63, 64, 66, 69, 72, 73]  # Replace with your desired list

# Load the original eaip_tables.html
with open("eaip_tables.html", "r", encoding="utf-8") as f:
    soup = BeautifulSoup(f, "html.parser")

# Find all table containers
containers = soup.select(".table-container")

# Filter to keep only specified table indices
selected_containers = [containers[i] for i in tables_to_keep if i < len(containers)]

# Update table numbers sequentially
for index, container in enumerate(selected_containers):
    h3 = container.find("h3")
    if h3:
        h3.string = f"Table number: {index}"

# Create new HTML with only selected tables
new_html_content = "<!DOCTYPE html>\n<html>\n<head>\n"
new_html_content += "<meta charset=\"UTF-8\">\n"
new_html_content += "<title>eAIP Selected Tables</title>\n"

# Add custom CSS (same as original)
new_html_content += "<style>\n"
new_html_content += "  td[class*=\"strong\"], th[class*=\"strong\"] { font-weight: bold; }\n"
new_html_content += "  .eaip-table { display: block; margin-bottom: 20px; width: 100%; transition: max-height 0.3s ease; }\n"
new_html_content += "  .eaip-row { display: flex; max-height: 50px; overflow: hidden; transition: max-height 0.3s ease; cursor: pointer; }\n"
new_html_content += "  .eaip-row.expanded { max-height: none; }\n"
new_html_content += "  .eaip-table.collapsed { max-height: 100px; overflow: hidden; }\n"
new_html_content += "  .eaip-row td, .eaip-row th { flex: 1; padding: 5px; border: 1px solid black; box-sizing: border-box; }\n"
new_html_content += "  .table-container { position: relative; margin-bottom: 40px; }\n"
new_html_content += "  .table-buttons { position: absolute; top: 0; right: 0; display: flex; gap: 5px; }\n"
new_html_content += "  .table-buttons button { padding: 5px 10px; cursor: pointer; }\n"
new_html_content += "  .table-container.highlighted { background-color: #90ee90; }\n"
new_html_content += "  h3 { cursor: pointer; }\n"
new_html_content += "  .controls { margin: 10px 0; display: flex; gap: 10px; align-items: center; }\n"
new_html_content += "  .controls input { padding: 5px; width: 300px; }\n"
new_html_content += "  .controls button { padding: 5px 10px; cursor: pointer; }\n"
new_html_content += "</style>\n"

# Add JavaScript (same as original, with updated initial selection)
new_html_content += "<script>\n"
new_html_content += "  document.addEventListener('DOMContentLoaded', function() {\n"
new_html_content += "    var rows = document.querySelectorAll('.eaip-row');\n"
new_html_content += "    var containers = document.querySelectorAll('.table-container');\n"
new_html_content += "    var tables = document.querySelectorAll('.eaip-table');\n"
new_html_content += "    var selectedField = document.getElementById('selected-tables');\n"
new_html_content += "    function updateSelectedField() {\n"
new_html_content += "      var selected = Array.from(containers)\n"
new_html_content += "        .filter(container => container.classList.contains('highlighted'))\n"
new_html_content += "        .map(container => parseInt(container.querySelector('h3').textContent.replace('Table number: ', '')));\n"
new_html_content += "      selectedField.value = 'selected_tables: ' + selected.join(', ');\n"
new_html_content += "    }\n"
new_html_content += "    // Initialize collapsed state and pre-selected tables\n"
new_html_content += "    tables.forEach(function(table) {\n"
new_html_content += "      table.classList.add('collapsed');\n"
new_html_content += "    });\n"
new_html_content += f"    var initialSelected = {list(range(len(tables_to_keep)))};\n"  # New indices: 0 to len-1
new_html_content += "    containers.forEach(function(container, index) {\n"
new_html_content += "      if (initialSelected.includes(index)) {\n"
new_html_content += "        container.classList.add('highlighted');\n"
new_html_content += "      }\n"
new_html_content += "    });\n"
new_html_content += "    updateSelectedField();\n"
new_html_content += "    // Row-level toggling\n"
new_html_content += "    rows.forEach(function(row) {\n"
new_html_content += "      row.addEventListener('click', function() {\n"
new_html_content += "        this.classList.toggle('expanded');\n"
new_html_content += "      });\n"
new_html_content += "    });\n"
new_html_content += "    // Heading click to toggle highlight\n"
new_html_content += "    var headings = document.querySelectorAll('h3');\n"
new_html_content += "    headings.forEach(function(heading) {\n"
new_html_content += "      heading.addEventListener('click', function() {\n"
new_html_content += "        var container = this.closest('.table-container');\n"
new_html_content += "        container.classList.toggle('highlighted');\n"
new_html_content += "        updateSelectedField();\n"
new_html_content += "      });\n"
new_html_content += "    });\n"
new_html_content += "    // Per-table expand all rows\n"
new_html_content += "    document.querySelectorAll('.expand-rows-btn').forEach(function(button) {\n"
new_html_content += "      button.addEventListener('click', function() {\n"
new_html_content += "        var table = this.closest('.table-container').querySelector('.eaip-table');\n"
new_html_content += "        table.querySelectorAll('.eaip-row').forEach(function(row) {\n"
new_html_content += "          row.classList.add('expanded');\n"
new_html_content += "        });\n"
new_html_content += "      });\n"
new_html_content += "    });\n"
new_html_content += "    // Per-table collapse all rows\n"
new_html_content += "    document.querySelectorAll('.collapse-rows-btn').forEach(function(button) {\n"
new_html_content += "      button.addEventListener('click', function() {\n"
new_html_content += "        var table = this.closest('.table-container').querySelector('.eaip-table');\n"
new_html_content += "        table.querySelectorAll('.eaip-row').forEach(function(row) {\n"
new_html_content += "          row.classList.remove('expanded');\n"
new_html_content += "        });\n"
new_html_content += "      });\n"
new_html_content += "    });\n"
new_html_content += "    // Per-table collapse table\n"
new_html_content += "    document.querySelectorAll('.collapse-table-btn').forEach(function(button) {\n"
new_html_content += "      button.addEventListener('click', function() {\n"
new_html_content += "        var table = this.closest('.table-container').querySelector('.eaip-table');\n"
new_html_content += "        table.classList.add('collapsed');\n"
new_html_content += "      });\n"
new_html_content += "    });\n"
new_html_content += "    // Per-table expand table\n"
new_html_content += "    document.querySelectorAll('.expand-table-btn').forEach(function(button) {\n"
new_html_content += "      button.addEventListener('click', function() {\n"
new_html_content += "        var table = this.closest('.table-container').querySelector('.eaip-table');\n"
new_html_content += "        table.classList.remove('collapsed');\n"
new_html_content += "      });\n"
new_html_content += "    });\n"
new_html_content += "    // Expand all tables\n"
new_html_content += "    document.getElementById('expand-all-tables').addEventListener('click', function() {\n"
new_html_content += "      tables.forEach(function(table) {\n"
new_html_content += "        table.classList.remove('collapsed');\n"
new_html_content += "      });\n"
new_html_content += "    });\n"
new_html_content += "    // Collapse all tables\n"
new_html_content += "    document.getElementById('collapse-all-tables').addEventListener('click', function() {\n"
new_html_content += "      tables.forEach(function(table) {\n"
new_html_content += "        table.classList.add('collapsed');\n"
new_html_content += "      });\n"
new_html_content += "    });\n"
new_html_content += "    // Input field to select tables\n"
new_html_content += "    selectedField.addEventListener('change', function() {\n"
new_html_content += "      var input = this.value.replace('selected_tables: ', '').split(',').map(num => parseInt(num.trim())).filter(num => !isNaN(num));\n"
new_html_content += "      containers.forEach(function(container, index) {\n"
new_html_content += "        if (input.includes(index)) {\n"
new_html_content += "          container.classList.add('highlighted');\n"
new_html_content += "        } else {\n"
new_html_content += "          container.classList.remove('highlighted');\n"
new_html_content += "        }\n"
new_html_content += "      });\n"
new_html_content += "      updateSelectedField();\n"
new_html_content += "    });\n"
new_html_content += "  });\n"
new_html_content += "</script>\n"

new_html_content += "</head>\n<body>\n"

# Add top controls with updated selected tables
new_html_content += "<div class=\"controls\">\n"
new_html_content += "  <input type=\"text\" id=\"selected-tables\" value=\"selected_tables: \" />\n"  # Updated dynamically by JS
new_html_content += "  <button id=\"expand-all-tables\">Expand All Tables</button>\n"
new_html_content += "  <button id=\"collapse-all-tables\">Collapse All Tables</button>\n"
new_html_content += "</div>\n"

# Add only selected tables
for container in selected_containers:
    new_html_content += str(container) + "\n"

new_html_content += "</body>\n</html>"

# Save to new file
output_file = "eaip_selected_tables.html"
with open(output_file, "w", encoding="utf-8") as f:
    f.write(new_html_content)
print(f"Saved {len(selected_containers)} selected tables to '{output_file}'")