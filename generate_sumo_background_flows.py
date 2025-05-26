#!/usr/bin/env python3

import pandas as pd
import xml.etree.ElementTree as ET
from xml.dom import minidom
import argparse
import os
import re # Uncommented for sanitizing channel names
import sys

SIMULATION_END_TIME = 3600

MAPPING_FILE_PATH = "cases/Nantes/channel_to_sumo_paths.csv"
# OUTPUT_FILE_PATH will be defined in main() using os.path.join

def sanitize_for_xml_id(text: str) -> str:
    """Sanitizes a string to be a valid XML ID by removing/replacing invalid characters."""
    # Ensure text is a string
    text = str(text).strip()
    # Replace spaces and most non-alphanumeric characters (excluding underscore, period, hyphen) with underscores
    text = re.sub(r'[^\w.-]', '_', text)
    # Ensure it doesn't start with a digit, period, or hyphen, which are invalid for XML IDs
    if not text or text[0].isdigit() or text.startswith('.') or text.startswith('-'):
        text = "_" + text
    return text

def main():
    parser = argparse.ArgumentParser(description="Generate SUMO background traffic flows.")
    parser.add_argument("traffic_data_path", help="Path to the cleaned traffic data parquet file.")
    args = parser.parse_args()

    print(f"Traffic data path: {args.traffic_data_path}")

    # 1. Parquet File Loading
    try:
        traffic_df = pd.read_parquet(args.traffic_data_path)
        print(f"Successfully loaded traffic data from {args.traffic_data_path}")
    except FileNotFoundError:
        print(f"Error: Traffic data Parquet file not found at {args.traffic_data_path}")
        sys.exit(1)
    except Exception as e: # Catch other potential pandas errors during loading
        print(f"Error loading traffic data from {args.traffic_data_path}: {e}")
        sys.exit(1)

    # 2. CSV Mapping File Loading with Fallback
    try:
        mapping_df = pd.read_csv(MAPPING_FILE_PATH)
        print(f"Successfully loaded mapping data from {MAPPING_FILE_PATH}")
    except FileNotFoundError:
        print(f"Warning: Mapping file '{MAPPING_FILE_PATH}' not found. Using fallback data.")
        fallback_data = {
            'channel_name': ['channel_A', 'channel_B', 'channel_C_unmapped'],
            'sumo_flow_origin_edge_id': ['edge1', 'edge3', 'edgeX'],
            'sumo_flow_destination_edge_id': ['edge2', 'edge4', 'edgeY']
            # 'sumo_paths' column will be missing, as per fallback spec for this step
        }
        mapping_df = pd.DataFrame(fallback_data)
        print("Using fallback mapping_df:")
    except Exception as e: # Catch other potential pandas errors
        print(f"Error loading mapping data from {MAPPING_FILE_PATH}: {e}. Using fallback data.")
        fallback_data = {
            'channel_name': ['channel_A', 'channel_B', 'channel_C_unmapped'],
            'sumo_flow_origin_edge_id': ['edge1', 'edge3', 'edgeX'],
            'sumo_flow_destination_edge_id': ['edge2', 'edge4', 'edgeY']
        }
        mapping_df = pd.DataFrame(fallback_data)
        print("Using fallback mapping_df due to error:")

    # 4. Aggregate Traffic Data
    if 'flow' not in traffic_df.columns:
        print("Error: 'flow' column not found in traffic data. Cannot calculate average flows.")
        sys.exit(1)

    # Ensure 'flow' column is numeric. Coerce errors, turning non-convertible values to NaN.
    traffic_df['flow'] = pd.to_numeric(traffic_df['flow'], errors='coerce')

    # Group by channel_name and calculate the mean of the 'flow'.
    # This results in a Series with channel_name as index.
    average_flows_by_channel = traffic_df.groupby('channel_name')['flow'].mean()

    # Handle potential NaN values that might arise if a channel had all non-numeric flows
    # or if the 'flow' column was empty or all NaN for a channel after coercion.
    average_flows_by_channel = average_flows_by_channel.fillna(0)

    # Prepare Output Directory
    OUTPUT_DIR = "cases/Nantes/"
    OUTPUT_FILE_PATH = os.path.join(OUTPUT_DIR, "background_traffic.rou.xml")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"Output will be written to: {OUTPUT_FILE_PATH}")

    # Create XML Structure
    routes_elem = ET.Element('routes')
    routes_elem.set('xmlns:xsi', 'http://www.w3.org/2001/XMLSchema-instance')
    routes_elem.set('xsi:noNamespaceSchemaLocation', 'http://sumo.dlr.de/xsd/routes_file.xsd')

    # Define <vType> Element
    vtype_elem = ET.SubElement(routes_elem, 'vType')
    vtype_elem.set('id', "background_car")
    vtype_elem.set('vClass', "passenger")
    vtype_elem.set('guiShape', "car")
    vtype_elem.set('length', "5")
    vtype_elem.set('maxSpeed', "70") # SUMO default is m/s. "70" used as per spec, could mean km/h.
    vtype_elem.set('color', "0,255,0") # Green color

    # Iterate and Generate <flow> Elements
    traffic_channel_names = set(average_flows_by_channel.index)
    
    # Ensure 'channel_name' column exists in mapping_df before creating the set
    if 'channel_name' not in mapping_df.columns:
        print(f"Error: 'channel_name' column not found in mapping_df. Columns available: {mapping_df.columns}")
        mapped_channel_names = set() 
        if mapping_df.empty:
             print("Warning: mapping_df is empty.")
    else:
        mapped_channel_names = set(mapping_df['channel_name'])

    for index, row in mapping_df.iterrows():
        channel_name = row.get('channel_name')
        sumo_origin_edge = row.get('sumo_flow_origin_edge_id')
        sumo_destination_edge = row.get('sumo_flow_destination_edge_id')

        if channel_name is None or sumo_origin_edge is None or sumo_destination_edge is None:
            print(f"Warning: Skipping mapping row index {index} due to missing critical data (channel_name, origin, or destination). Row: {row.to_dict()}")
            continue
            
        avg_flow = average_flows_by_channel.get(channel_name, 0)

        if avg_flow > 0:
            sanitized_channel_id_name = sanitize_for_xml_id(channel_name) # Use the reactivated function
            
            flow_elem = ET.SubElement(routes_elem, 'flow')
            flow_elem.set('id', f"flow_{sanitized_channel_id_name}")
            flow_elem.set('type', "background_car") # Matches vType id
            flow_elem.set('from', str(sumo_origin_edge))
            flow_elem.set('to', str(sumo_destination_edge))
            flow_elem.set('vehsPerHour', str(int(round(avg_flow))))
            flow_elem.set('departLane', "best")
            flow_elem.set('departSpeed', "max")
            flow_elem.set('begin', "0")
            flow_elem.set('end', str(SIMULATION_END_TIME))
            flow_elem.set('departPos', "base")
    
    # Log Unmapped Channels
    unmapped_channels_in_traffic_data = list(traffic_channel_names - mapped_channel_names)
    if unmapped_channels_in_traffic_data:
        unmapped_channels_in_traffic_data.sort() 
        print(f"Warning: The following channels were found in traffic data but not in the mapping file and were skipped for flow generation: {unmapped_channels_in_traffic_data}")

    # Pretty Print and Write XML Output
    try:
        rough_string = ET.tostring(routes_elem, 'utf-8')
        reparsed = minidom.parseString(rough_string)
        pretty_xml_as_string = reparsed.toprettyxml(indent="  ")

        with open(OUTPUT_FILE_PATH, "w", encoding="utf-8") as f:
            f.write(pretty_xml_as_string)
        print(f"\nSuccessfully generated SUMO background traffic flows at {OUTPUT_FILE_PATH}")

        # User Instructions
        print("\nScript finished successfully.")
        print(f"Generated SUMO background traffic flows at: {OUTPUT_FILE_PATH}")
        print("Reminder: To use these flows in your simulation, you need to add them to your SUMO configuration file (.sumocfg).")
        print("For example, if your existing route file is 'MyRoutes.rou.xml', update the <input> section like this:")
        print("<route-files value=\"MyRoutes.rou.xml,background_traffic.rou.xml\"/>") # Corrected quoting for XML attribute
        print("Ensure 'background_traffic.rou.xml' is accessible from the location of your .sumocfg file, or adjust the path accordingly.")

    except IOError as e:
        print(f"Error writing output XML file: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred during XML writing: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
