#!/usr/bin/env python
import sys
import json
from shapely.geometry import shape, mapping


def simplify_geojson(geojson_obj, tolerance):
    # Check if it's a FeatureCollection
    if 'features' in geojson_obj:
        new_features = []
        for feature in geojson_obj['features']:
            # Simplify the feature's geometry
            geom = shape(feature['geometry'])
            simplified_geom = geom.simplify(tolerance, preserve_topology=True)
            new_feature = feature.copy()
            new_feature['geometry'] = mapping(simplified_geom)
            new_features.append(new_feature)
        geojson_obj['features'] = new_features
        return geojson_obj
    else:
        # Assume the GeoJSON object is a geometry
        geom = shape(geojson_obj)
        simplified_geom = geom.simplify(tolerance, preserve_topology=True)
        return mapping(simplified_geom)


def main():
    if len(sys.argv) != 2:
        print('Usage: python simplify_line.py file.geojson')
        sys.exit(1)

    input_file = sys.argv[1]
    # Derive output file name by inserting '_simplified' before the .geojson extension
    if input_file.endswith('.geojson'):
        output_file = input_file[:-8] + 'simplified.geojson'
    else:
        output_file = input_file + '_simplified.geojson'

    try:
        with open(input_file, 'r') as f:
            geojson_data = json.load(f)
    except Exception as e:
        print(f'Error reading {input_file}: {e}')
        sys.exit(1)

    # Set a default tolerance value for simplification
    tolerance = 0.001  # Adjust tolerance as needed

    simplified_geojson = simplify_geojson(geojson_data, tolerance)

    try:
        with open(output_file, 'w') as f:
            json.dump(simplified_geojson, f)
        print(f'Simplified geojson written to {output_file}')
    except Exception as e:
        print(f'Error writing {output_file}: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()
