# ============================
# Creator_realflux.py (Final Version)
# ============================

import pandas as pd
import random
import xml.etree.ElementTree as ET
import os

def create(mapName, real_flux_path, mapping_path):
    """
    Create a .rou.xml file based on real traffic flow estimation and real SUMO edges.

    :param mapName: Name of the SUMO map (optional for future)
    :param real_flux_path: Path to the cleaned traffic CSV
    :param mapping_path: Path to the channel_name to SUMO edge mapping CSV
    """

    print("🚦 Loading real traffic data...")
    df = pd.read_csv(real_flux_path)

    # Make sure timestamp is datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')

    # Only keep positive flows
    df = df[df['flow'] > 0]

    print(f"✅ Loaded {len(df)} traffic records.")

    # Load the channel_name → edge_id mapping
    mapping_df = pd.read_csv(mapping_path)
    channel_to_edge = dict(zip(mapping_df['channel_name'], mapping_df['edge_id']))

    print(f"✅ Loaded mapping for {len(channel_to_edge)} streets.")

    # Create the root of the XML
    routes = ET.Element("routes")

    # Define vehicle type (you can add more types later)
    vtype = ET.SubElement(routes, "vType", id="car", accel="2.0", decel="4.5", length="5", maxSpeed="50", sigma="0.5", color="1,0,0")

    veh_id_counter = 0  # Unique ID for vehicles

    # For each street + time
    for index, row in df.iterrows():
        channel_name = row['channel_name']
        flow = row['flow']  # vehicles per hour
        timestamp = row['timestamp']

        # Skip if this street is not mapped
        if channel_name not in channel_to_edge:
            continue

        edge_id = channel_to_edge[channel_name]

        # Calculate vehicle injection
        vehicles_per_hour = flow
        if vehicles_per_hour <= 0:
            continue

        # Average spacing between vehicles in seconds
        average_interval = 3600 / vehicles_per_hour  
        current_time = timestamp.hour * 3600 + timestamp.minute * 60  # seconds since midnight

        num_vehicles = int(vehicles_per_hour / 4)  # ⚡ (adjust density scaling here)

        for i in range(num_vehicles):
            depart_time = current_time + i * average_interval

            vehicle = ET.SubElement(routes, "vehicle",
                id=f"veh_{veh_id_counter}",
                type="car",
                depart=str(round(depart_time, 2)),
                departLane="best",
                departSpeed="max"
            )

            # Assign route based on real edge
            route = ET.SubElement(vehicle, "route", edges=edge_id)

            veh_id_counter += 1

    # Save the new .rou.xml
    tree = ET.ElementTree(routes)
    output_file = f"MyRoutes_realflux.rou.xml"
    output_path = os.path.join(os.getcwd(), output_file)
    tree.write(output_path)

    print(f"✅ Realistic traffic file saved: {output_path}")
#create( mapName="nantes",real_flux_path=r"C:\Users\ASUS\Documents\Stage LS2N\nantes_traffic_archiver\dist\cleaned_traffic_data.csv",mapping_path=r"C:\Users\ASUS\Documents\Stage LS2N\nantes_traffic_archiver\dist\channel_to_edge_mapping_precise.csv")
