import json
import xml.etree.ElementTree as ET

def parse_coordinates(coord_string):
    """Convert KML coordinate string to GeoJSON coordinates"""
    coords = []
    for point in coord_string.strip().split():
        lon, lat = map(float, point.split(',')[:2])  # Ignore z if present
        coords.append([lon, lat])
    return coords

def kml_to_geojson(kml_file, geojson_file):
    # Parse KML
    tree = ET.parse(kml_file)
    root = tree.getroot()
    
    # Namespace handling (KML often uses namespaces)
    namespace = {'kml': 'http://www.opengis.net/kml/2.2'}
    
    # Count input features
    input_features = len(root.findall('.//kml:Placemark', namespace))
    print(f"Number of features in KML: {input_features}")
    
    # Initialize GeoJSON structure
    geojson = {
        "type": "FeatureCollection",
        "features": []
    }
    
    # Process each Placemark
    for placemark in root.findall('.//kml:Placemark', namespace):
        feature = {
            "type": "Feature",
            "properties": {},
            "geometry": None
        }
        
        # Extract properties from ExtendedData
        extended_data = placemark.find('.//kml:ExtendedData/kml:SchemaData', namespace)
        if extended_data is not None:
            for simple_data in extended_data.findall('kml:SimpleData', namespace):
                name = simple_data.get('name')
                value = simple_data.text
                # Convert numeric values
                try:
                    if value.isdigit():
                        value = int(value)
                    elif value.replace('.','',1).isdigit():
                        value = float(value)
                except (ValueError, AttributeError):
                    pass
                feature["properties"][name] = value
        
        # Extract geometry (assuming Polygon in MultiGeometry)
        polygon = placemark.find('.//kml:MultiGeometry/kml:Polygon', namespace)
        if polygon is not None:
            coordinates = polygon.find('.//kml:LinearRing/kml:coordinates', namespace)
            if coordinates is not None and coordinates.text:
                feature["geometry"] = {
                    "type": "Polygon",
                    "coordinates": [parse_coordinates(coordinates.text)]
                }
        
        # Add feature to collection if it has geometry
        if feature["geometry"]:
            geojson["features"].append(feature)
    
    # Count output features
    output_features = len(geojson["features"])
    print(f"Number of features in GeoJSON: {output_features}")
    
    # Write GeoJSON file
    with open(geojson_file, 'w', encoding='utf-8') as f:
        json.dump(geojson, f, indent=2, ensure_ascii=False)
    
    # Warn if feature counts don't match
    if input_features != output_features:
        print(f"Warning: {input_features - output_features} features were not converted (possibly missing geometry)")

# Example usage
if __name__ == "__main__":
    input_kml = "france.kml"
    output_geojson = "zsm.geojson"
    kml_to_geojson(input_kml, output_geojson)