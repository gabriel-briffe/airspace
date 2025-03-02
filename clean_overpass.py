import sys
import json


def process_geojson(geojson):
    new_features = []
    for feature in geojson.get('features', []):
        geom = feature.get('geometry')
        if not geom:
            continue
        geom_type = geom.get('type')
        # Remove point features
        if geom_type == 'Point':
            continue
        # Transform MultiPolygon into MultiLineString
        elif geom_type == 'MultiPolygon':
            multi_polygon_coords = geom.get('coordinates', [])
            # Initialize list for multiline strings (exterior rings only)
            multiline_coords = []
            for polygon in multi_polygon_coords:
                # Each polygon is a list of rings; we take the first (exterior ring)
                if polygon and len(polygon) > 0:
                    multiline_coords.append(polygon[0])
            if len(multiline_coords) > 1:
                # Calculate ring details for each polygon: list of lengths (number of points) per ring
                rings_info = [[len(ring) for ring in polygon] for polygon in multi_polygon_coords if polygon]
                print(f"Warning: feature {feature.get('id', '')} has multiple polygons with rings details: {rings_info}", file=sys.stderr)
            # Replace geometry with MultiLineString
            feature['geometry'] = {
                'type': 'MultiLineString',
                'coordinates': multiline_coords
            }
            new_features.append(feature)
        # Transform Polygon into MultiLineString
        elif geom_type == 'Polygon':
            polygon_coords = geom.get('coordinates', [])
            if not polygon_coords or len(polygon_coords) == 0:
                continue
            # Extract the exterior ring (first ring)
            multiline_coords = [polygon_coords[0]]
            if len(polygon_coords) > 1:
                ring_lengths = [len(ring) for ring in polygon_coords]
                print(f"Warning: feature {feature.get('id', '')} has {len(polygon_coords)} rings with lengths {ring_lengths} in Polygon", file=sys.stderr)
            # Replace geometry with MultiLineString
            feature['geometry'] = {
                'type': 'MultiLineString',
                'coordinates': multiline_coords
            }
            new_features.append(feature)
        else:
            new_features.append(feature)
    geojson['features'] = new_features
    return geojson


def main():
    if len(sys.argv) != 2:
        print(f"Usage: python {sys.argv[0]} input.geojson")
        sys.exit(1)

    input_file = sys.argv[1]
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            geojson = json.load(f)
    except Exception as e:
        print(f"Error reading file {input_file}: {e}", file=sys.stderr)
        sys.exit(1)

    processed_geojson = process_geojson(geojson)
    # Determine the output filename by appending '_cleaned' before the .geojson extension
    if input_file.lower().endswith('.geojson'):
        output_file = input_file[:-8] + '_cleaned.geojson'
    else:
        output_file = input_file + '_cleaned.geojson'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(processed_geojson, f, ensure_ascii=False, indent=2)
    print(f"Cleaned GeoJSON written to {output_file}")


if __name__ == '__main__':
    main()
