import argparse
import json
import sys

# Here is the updated parks_map with empty fields replaced by ""
parks_map = {
    "010 . BAIE DE SOMME" : "",
    "014 . CHAUMES DU VERNILLER" : "",
    "015 . GROTTE ET PELOUSES D'ACQUIN-WESTBECOURT" : "",
    "020 . ESTUAIRE DE LA SEINE" : "",
    "021 . PARC NATIONAL DE FORETS" : "",
    "025 . COTEAUX DE WAVRANS-SUR-L'AA" : "",
    "030 . PLATIER D'OYE" : "",
    "035 . ETANGS DU ROMELAËRE" : "",
    "040 . MANNEVILLES" : "",
    "045 . FORET D'ORIENT" : "",
    "046 . ETANGS ET RIGOLES D'YVELINE" : "",
    "047 . TOURBIERE DE MARCHIENNES" : "",
    "048 . SAINT MESMIN" : "",
    "050 . MASSIF DU VENTRON" : "",
    "051 . MASSIF FORESTIER DE LA ROBERTSAU ET LA WANTZENAU" : "",
    "055 . MASSIF FORESTIER DE STRASBOURG-NEUHOF / ILLKIRCH" : "",
    "060 . PETITE CAMARGUE ALSACIENNE" : "",
    "070 . FORET D'OFFENDORF" : "",
    "080 . BAIE DE SAINT BRIEUC" : "",
    "090 . DOMAINE DE BEAUGUILLOT" : "",
    "100 . IROISE" : "",
    "110 . LA SANGSURIERE ET L'ADRIENNERIE" : "",
    "120 . MARAIS DU MULLEMBOURG" : "",
    "130 . MARAIS DE SENE" : "",
    "140 . GRAND LIEU" : "",
    "145 . VENEC" : "",
    "148 . SEPT ILES" : "",
    "150 . VALLEE D'OSSAU" : "",
    "160 . BAIE DE L'AIGUILLON" : "",
    "170 . BANC D'ARGUIN" : "",
    "180 . CONAT" : "",
    "190 . ETANG DE COUSSEAU" : "",
    "195 . ETANG DES LANDES - LUSSAT" : "",
    "200 . JUJOLS" : "",
    "210 . L'ETANG DE LA MAZIERE" : "",
    "220 . LILLEAU DES NIGES ( FIER D'ARS )" : "",
    "230 . MANTET" : "",
    "240 . MARAIS DE MOEZE" : "",
    "250 . MARAIS D'ORX" : "",
    "255 . DUNES ET MARAIS D'HOURTIN" : "",
    "260 . MARAIS D'YVES" : "",
    "270 . NEOUVIELLE" : "",
    "280 . NOHEDES" : "",
    "290 . PRATS DE MOLLO LA PRESTE" : "",
    "300 . PY" : "",
    "310 . PARC NATIONAL DES PYRENEES OCCIDENTALES" : "PARC/RESERVE  PYRENNEES 1000M/SOL",
    "320 . SAINT DENIS DU PAYRE" : "",
    "330 . CHERINE" : "",
    "340 . CHAUDEFOUR" : "",
    "345 . CASSE DE LA BELLE HENRIETTE" : "",
    "346 . SAGNES DE LA GODIVELLE" : "",
    "347 . ARJUZANX" : "",
    "350 . AIGUILLES ROUGES" : "PARC/RESERVE  AIGUILLES ROUGES 1000M/SOL",
    "351 . DELTA DE LA DRANSE" : "",
    "352 . HAUT-RHONE FRANCAIS" : "",
    "353 . HAUTS DE VILLAROGER" : "",
    "354 . MARAIS DU VIGUEIRAT" : "",
    "355 . PLAINE DES MAURES" : "",
    "356 . ROCHE GRANDE" : "",
    "360 . BAGNAS" : "",
    "365 . PLAN DE TUEDA" : "",
    "370 . CAMARGUE" : "",
    "375 . LA BAILLETAZ" : "PARC/RESERVE  BAILLETAZ",
    "380 . CARLAVEYRON" : "",
    "385 . ROCHER DE LA JAQUETTE" : "",
    "390 . PARC NATIONAL DES CEVENNES" : "PARC/RESERVE  CEVENNES 1000 M/SOL",
    "400 . CIRQUE DU GRAND LAC DES ESTARIS" : "",
    "410 . CONTAMINES MONTJOIE" : "PARC/RESERVE  CONTAMINES 300M/SOL",
    "420 . PARC NATIONAL DES ECRINS" : "PARC/RESERVE  ECRINS 1000M/SOL",
    "430 . ETANG DU GRAND LEMPS" : "",
    "440 . GRANDE SASSIERE" : "PARC/RESERVE  GDE SASSIERE 1000M/SOL",
    "450 . HAUTE VALLEE DE LA SEVERAISSE" : "",
    "460 . HAUTE VALLEE DE SAINT PIERRE" : "",
    "470 . HAUT-BERANGER" : "",
    "480 . HAUT-VENEON" : "",
    "490 . HAUTS PLATEAUX DU VERCORS" : "PARC/RESERVE  VERCORS 300M/SOL",
    "500 . ILE DE LA PLATIERE" : "",
    "510 . GORGES DE L'ARDECHE" : "",
    "520 . MARAIS DU BOUT DU LAC D'ANNECY" : "",
    "530 . MAS LARRIEU" : "",
    "540 . PARC NATIONAL DU MERCANTOUR" : "PARC/RESERVE  MERCANTOUR 1000M/SOL",
    "550 . PASSY" : "PARC/RESERVE  PASSY 300M/SOL",
    "560 . PARC NATIONAL DE PORT CROS" : "",
    "570 . RAMIERES DU VAL DE DROME" : "",
    "580 . SCANDOLA" : "",
    "590 . SIXT-FER-A-CHEVAL - PASSY" : "PARC/RESERVE  SIXT 300M/SOL",
    "600 . PARC NATIONAL DE LA VANOISE" : "PARC/RESERVE  VANOISE 1000M/SOL",
    "610 . VERSANT NORD DES PICS DU COMBEYNOT" : "",
    "620 . VALLON DE BERARD" : "",
    "630 . RISTOLAS MONT VISO" : "",
    "640 . CHASTREIX SANCY" : "",
    "650 . CALANQUES" : ""
}

def output_park_names(geojson_path):
    """
    Reads a GeoJSON file and prints all 'name' properties of features
    that begin with 'PARC/RESERVE'.
    """
    try:
        with open(geojson_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        sys.exit(f"Error reading file: {e}")

    features = data.get("features", [])
    if not features:
        sys.exit("No features found in geojson file.")

    for feature in features:
        properties = feature.get("properties", {})
        name = properties.get("name", "")
        if name.startswith("PARC/RESERVE"):
            print(name)

def write_parks_json(geojson_path):
    """
    Reads the provided GeoJSON file and writes out parks.json.
    For each key in parks_map, if the value (expected feature name) is non-empty, then this function searches for a feature in the GeoJSON with a "name"
    equal to that value. If a matching feature is found, then the feature's geometry "coordinates" are saved under the park key in the output JSON.
    Otherwise, an empty list is stored.
    """
    try:
        with open(geojson_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        sys.exit(f"Error reading file: {e}")

    parks_output = {}
    features = data.get("features", [])
    if not features:
        sys.exit("No features found in geojson file.")

    for park_key, expected_name in parks_map.items():
        coords = []
        if expected_name.strip() != "":
            # search for a feature with property "name" exactly matching expected_name
            found = False
            for feature in features:
                feat_name = feature.get("properties", {}).get("name", "").strip()
                if feat_name == expected_name.strip():
                    coords = feature.get("geometry", {}).get("coordinates", [])
                    while coords and isinstance(coords, list) and len(coords) > 0 and isinstance(coords[0], list) and len(coords[0]) > 0 and isinstance(coords[0][0], list):
                        coords = coords[0]
                    print(f"Found feature for '{park_key}' matching '{expected_name}' with {len(coords)} coordinates.")
                    found = True
                    break
            if not found:
                print(f"No matching feature found for '{park_key}' with expected name '{expected_name}'.")
        else:
            print(f"No expected feature name provided for '{park_key}', leaving coordinates empty.")
        parks_output[park_key] = {"coordinates": coords}

    try:
        with open("parks.json", "w", encoding="utf-8") as outfile:
            json.dump(parks_output, outfile, ensure_ascii=False, indent=4)
        print("parks.json has been written.")
    except Exception as e:
        sys.exit(f"Error writing parks.json: {e}")

def main():
    parser = argparse.ArgumentParser(
        description="Process a GeoJSON file or output parks mapping as JSON."
    )
    parser.add_argument("geojson_file", nargs="?", help="Path to the GeoJSON file")
    parser.add_argument("--park_names", action="store_true",
                        help="Output park names that start with PARC/RESERVE")
    parser.add_argument("--out", action="store_true",
                        help="Write parks.json mapping file using coordinates from geojson features")
    args = parser.parse_args()

    if args.park_names:
        if not args.geojson_file:
            sys.exit("A GeoJSON file must be provided when using --park_names.")
        output_park_names(args.geojson_file)
    elif args.out:
        if not args.geojson_file:
            sys.exit("A GeoJSON file must be provided when using --out.")
        write_parks_json(args.geojson_file)
    else:
        print("No valid flag provided. Use --park_names to output park names or --out to write parks.json.")

if __name__ == "__main__":
    main()




