import subprocess

# Paths
net_file = "C:/Users/ASUS/Documents/Stage LS2N/Nantes_simulation/cases/Nantes/MyNetwork.net.xml"
netcheck_script = "C:/Program Files (x86)/Eclipse/Sumo/tools/net/netcheck.py"
 # adjust if needed

# Edges
source_edge = "-14864"
destination_edge = "--12778#0"

# Check reachability from source
print(f"Checking if '{source_edge}' can reach other edges...")
subprocess.run([
    "python", netcheck_script,
    net_file,
    "--source", source_edge,
    "--selection-output", "selection_from_source.txt"
])

# Check reachability to destination
print(f"Checking who can reach '{destination_edge}'...")
subprocess.run([
    "python", netcheck_script,
    net_file,
    "--destination", destination_edge,
    "--selection-output", "selection_to_destination.txt"
], shell=True)


print("\nDone! ✅")
print("Now open SUMO-GUI, load your network, and visualize 'selection_from_source.txt' and 'selection_to_destination.txt' to see reachable edges.")
