from bs4 import BeautifulSoup

# Input and output file paths
input_file = "eaip_selected_tables_stage1.html"
output_file = "eaip_selected_tables_stage1_cleaned.html"

# Load the input HTML file
with open(input_file, "r", encoding="utf-8") as f:
    soup = BeautifulSoup(f, "html.parser")

# Iterate over each table container
for container in soup.select('.table-container'):
    # Find all table row elements within the container
    for tr in container.find_all('tr'):
        classes = tr.get('class', [])
        # Keep only rows that are parsed name rows or parsed rows
        if not ("parsed-name" in classes or "parsed-row" in classes):
            tr.decompose()

# Write the cleaned HTML to output file
with open(output_file, "w", encoding="utf-8") as f:
    f.write(str(soup))

print(f"Saved cleaned tables to '{output_file}'")