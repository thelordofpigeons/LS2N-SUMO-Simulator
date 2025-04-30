import pandas as pd
import sumolib

# Load SUMO network
net_path = r"C:\Users\ASUS\Documents\Stage LS2N\Nantes_simulation\cases\Nantes\MyNetwork.net.xml"
net = sumolib.net.readNet(net_path)

# Load your streets
raw_file_path = r"C:\Users\ASUS\Documents\Stage LS2N\nantes_traffic_archiver\dist\archive\nantes_traffic_snapshot_20250403_161310.csv"
raw_df = pd.read_csv(raw_file_path)

# Extract longitude and latitude
def extract_lon(x):
    try:
        return eval(x)["lon"]
    except:
        return None

def extract_lat(x):
    try:
        return eval(x)["lat"]
    except:
        return None

raw_df['longitude'] = raw_df['geo_point_2d'].apply(extract_lon)
raw_df['latitude'] = raw_df['geo_point_2d'].apply(extract_lat)

geo_mapping = raw_df[['cha_lib', 'longitude', 'latitude']].dropna().drop_duplicates()
geo_mapping.rename(columns={'cha_lib': 'channel_name'}, inplace=True)

mapping = {}

for index, row in geo_mapping.iterrows():
    lon = row['longitude']
    lat = row['latitude']
    channel_name = row['channel_name']

    # Convert GPS (lon/lat) to SUMO (x/y)
    x, y = net.convertLonLat2XY(lon, lat)

    # Find neighboring edges within 100 meters only
    neighboring_edges = net.getNeighboringEdges(x, y, 100)

    if neighboring_edges:
        # Sort by real distance
        neighboring_edges.sort(key=lambda e: e[1])  # (edge, distance)

        closest_edge = neighboring_edges[0][0]  # Closest one
        mapping[channel_name] = closest_edge.getID()
    else:
        print(f"⚠️ No edge found near {channel_name} ({lon}, {lat}). Skipping.")

print(f"✅ Created mapping for {len(mapping)} streets (after precision fix).")

# Save it
mapping_df = pd.DataFrame(list(mapping.items()), columns=['channel_name', 'edge_id'])
mapping_df.to_csv(r"C:\Users\ASUS\Documents\Stage LS2N\nantes_traffic_archiver\dist\channel_to_edge_mapping_precise.csv", index=False)

print("✅ Precise mapping saved to channel_to_edge_mapping_precise.csv")
