# --- START OF FILE Starter.py ---

import os, sys, winsound
import traci
import random
import traci.constants as tc
import myPyLib as PL
import xml.etree.ElementTree as ET
import glob
from datetime import datetime
from myPyLib import getHeader
# from Lib.linecache import getline # Seems unused

# ---- NEW IMPORTS ----
import threading
import queue
import monitor_gui # Import the new GUI module
import time
# ---- END NEW IMPORTS ----

from os import path # Already imported via 'import os', but keep for clarity if preferred

# --- Environment Check ---
if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    print("ERROR: please declare environment variable 'SUMO_HOME'")
    sys.exit("Environment variable 'SUMO_HOME' not set.") # Exit if SUMO_HOME is missing

# --- Global Settings & Variables ---
sumoBinary = "C:/Program Files (x86)/Eclipse/Sumo/bin/sumo-gui"  # Adjust path if necessary
Entry1 = "-13963" # Example edge ID
Exit1 = "-2252"  # Example edge ID

# --- Globals for Monitor Communication & Shared State ---
data_queue = queue.Queue()
monitor_thread = None
mission_root_global = None # Parsed missions XML root
metadata_root_global = None # Parsed metadata XML root (needed for getAlternative)
routes_root_global = None # Parsed routes XML root (needed for some logic?)


# --- Helper Functions (Many from Original) ---

# Note: StateListener class seems unused if we fetch data directly in the loop. Removing for now.
# If you need its specific collision/emergency break logic, it would need integration.

def initMode(mode, mapName): # Added mapName as it seems necessary for config path
    global checkParking # Make sure checkParking is accessible if needed elsewhere
    print(f"Initiating mode: {mode} for map: {mapName}")
    # Check if config file exists (optional but good practice)
    config_path = f"cases/{mapName}/network.sumocfg"
    if not os.path.exists(config_path):
         print(f"Warning: SUMO config file not found at {config_path}")
         # Decide how to handle this - proceed? exit?

    # Assuming Entry1 and Exit1 are defined globally or passed in
    try:
        if mode and len(mode) > 4: # Basic check for mode format
            if(mode[4] == "0"):
                traci.edge.setMaxSpeed(Entry1, 0.3) # Use variables
                traci.edge.setMaxSpeed(Exit1, 0.5)
                checkParking = False
                print(f"Mode {mode}: Set edge speeds (Entry1: 0.3, Exit1: 0.5), checkParking=False")
            elif(mode[4] == "1"):
                traci.edge.setMaxSpeed(Entry1, 1.0)
                traci.edge.setMaxSpeed(Exit1, 1.0)
                checkParking = True
                print(f"Mode {mode}: Set edge speeds (Entry1: 1.0, Exit1: 1.0), checkParking=True")
            else:
                 print(f"Warning: Unknown setting for mode[4]: {mode[4]}. Using default speeds.")
                 # Optionally set default speeds here
            # Add logic for mode[5], mode[6] if they control other things like parking behaviour
        else:
             print(f"Warning: Invalid mode format '{mode}'. Cannot apply mode settings.")

        # VSS sign logic removed - was it used? Re-add if needed.
        # for speedID in traci.variablespeedsign.getIDList():
        #     print(speedID + " initiated with speed=" + val)

    except traci.TraCIException as e:
         print(f"TraCI Error during initMode: {e}. Check edge IDs '{Entry1}', '{Exit1}'.")
    except Exception as e:
        print(f"Unexpected Error during initMode: {e}")

    print("Initiating mode done.")

def getRemainingEdges(vehID):
    try:
        route = traci.vehicle.getRoute(vehID)
        index = traci.vehicle.getRouteIndex(vehID)
        return len(route) - index if index >= 0 else len(route)
    except traci.TraCIException as e:
        print(f"Warning: TraCI error getting route/index for {vehID}: {e}")
        return 0 # Or another sensible default

def isParkWaiting(vehID):
    # Requires getAction to work correctly with mission_root_global
    action = getAction(vehID, mission_root_global)
    if not action or action.get("type") != 'Park':
        return False
    try:
        return getRemainingEdges(vehID) <= 2 and traci.vehicle.getSpeed(vehID) < 0.1 # Use speed threshold
    except traci.TraCIException as e:
         print(f"Warning: TraCI error checking park waiting for {vehID}: {e}")
         return False


def isFull(target_parking_area_id):
    """Checks if a specific parking area is full using getParameter for capacity."""
    try:
        # Get the current number of vehicles parked
        count = traci.parkingarea.getVehicleCount(target_parking_area_id)

        # Get the capacity defined as a parameter for the parking area
        capacity_str = traci.simulation.getParameter(target_parking_area_id, "parkingArea.capacity")

        if capacity_str is None or capacity_str == "": # Handle missing parameter gracefully
            print(f"Warning: Capacity parameter not found for parking area '{target_parking_area_id}'. Assuming not full.")
            return False # Cannot determine fullness if capacity is unknown

        capacity = int(capacity_str) # Convert capacity string to integer

        # Uncomment for debugging if needed
        # print(f"Debug isFull: Parking '{target_parking_area_id}': Count={count}, Capacity={capacity}")

        # Return True if count is greater than or equal to capacity
        return count >= capacity

    except traci.TraCIException as e:
        # Handle errors like invalid parking ID or disconnected TraCI
        print(f"Warning: TraCI error checking fullness of parking area '{target_parking_area_id}': {e}")
        # Decide on behavior: assume not full, or raise error? Assuming not full is often safer.
        return False
    except (ValueError, TypeError) as e:
        # Handle errors if the capacity parameter string isn't a valid integer
        print(f"Warning: Error converting capacity parameter '{capacity_str}' to int for '{target_parking_area_id}': {e}")
        return False # Assume not full if capacity is invalid
    except Exception as e:
        # Catch any other unexpected errors during the check
        print(f"Warning: Unexpected error in isFull for '{target_parking_area_id}': {e}")
        return False


def assignMission(vehID, action):
    """Assigns the next mission step using TraCI commands and updates the action status in memory."""
    global mission_root_global # Ensure modification happens on the global object

    if action is None:
        print(f"Warning: assignMission called with None action for {vehID}")
        return

    newTarget = action.get("target") # Parking Area ID or Stop ID
    newEdge = action.get("edge")     # Target Edge for routing
    actionType = action.get("type")

    if not newTarget or not newEdge or not actionType:
         print(f"ERROR: Incomplete action details for {vehID}: Type={actionType}, Target={newTarget}, Edge={newEdge}")
         # Optionally set status to error or skip
         return

    print(f"{vehID}: Assigning Action: Type={actionType}, Target={newTarget}, Edge={newEdge}")

    try:
        # --- Set Route Target ---
        traci.vehicle.changeTarget(vehID, newEdge)

        # --- Set Stop Conditions ---
        stop_duration = 600 # Default duration (e.g., for Park)
        if actionType == "Load" or actionType == "Unload":
            stop_duration = 180 # Shorter duration for Load/Unload
            # Use parkingArea stop if target is a parkingArea ID
            # This assumes Load/Unload targets are ParkingArea IDs from your metadata
            # Adjust if targets are BusStop IDs or ContainerStop IDs
            traci.vehicle.setParkingAreaStop(vehID, newTarget, duration=stop_duration)
            print(f"  {vehID}: Set ParkingAreaStop at '{newTarget}' for {stop_duration}s")
        elif actionType == "Park":
             traci.vehicle.setParkingAreaStop(vehID, newTarget, duration=stop_duration)
             print(f"  {vehID}: Set ParkingAreaStop at '{newTarget}' for {stop_duration}s")
        elif actionType == "Go":
             print(f"  {vehID}: Route set towards Edge '{newEdge}'. No stop defined.")
             # No stop needed for 'Go' action, target edge handles routing
             pass
        else:
            print(f"Warning: Unknown action type '{actionType}' for {vehID}. Cannot set stop.")

        # --- CRUCIAL: Update the status IN MEMORY ---
        action.set("status", "1") # Mark as assigned/in progress
        print(f"  {vehID}: Action status set to '1'")

    except traci.TraCIException as e:
        print(f"ERROR: TraCI error assigning mission for {vehID} (Target:{newTarget}, Edge:{newEdge}): {e}")
        # How to handle? Maybe retry, skip, set error status?
        # action.set("status", "error") # Example
    except Exception as e:
        print(f"ERROR: Unexpected error assigning mission for {vehID}: {e}")


def getAction(vehID, mission_root):
    """Gets the current pending action (status != '3') for a vehicle."""
    # Prioritize global if available and valid
    root_to_use = mission_root_global if mission_root_global is not None else mission_root
    if root_to_use is None:
        # print(f"Debug: getAction - No mission root available for {vehID}") # Debug
        return None

    for mission in root_to_use.findall(".//mission[@id='{}']".format(vehID)): # More efficient XPath
        for action in mission.findall("action"):
            if action.get("status") != "3":
                # print(f"Debug: getAction - Found action for {vehID}: Type={action.get('type')}, Status={action.get('status')}") # Debug
                return action
        # If loop finishes, all actions are '3' or no actions exist
        # print(f"Debug: getAction - No pending action found for {vehID}") # Debug
        return None # No pending action found for this vehicle
    # print(f"Debug: getAction - Mission ID {vehID} not found in mission root.") # Debug
    return None # Vehicle mission not found


def setAction(vehID, mission_root, newAction):
    """Finds the current pending action and replaces its attributes with newAction's."""
    global mission_root_global # Ensure modification happens on the global object
    root_to_use = mission_root_global if mission_root_global is not None else mission_root
    if root_to_use is None: return

    action_updated = False
    for mission in root_to_use.findall(".//mission[@id='{}']".format(vehID)):
        for action in mission.findall("action"):
            if action.get("status") != "3":
                old_target = action.get('target')
                action.set('target', newAction.get('target'))
                action.set('edge', newAction.get('edge'))
                action.set('type', newAction.get('type')) # Also update type if needed
                action.set('status', '0') # Reset status so it gets assigned again
                print(f"{vehID}: Replaced action target '{old_target}' with '{newAction.get('target')}', status reset to '0'")
                action_updated = True
                return # Assume only one pending action needs replacing
    if not action_updated:
        print(f"Warning: setAction - Could not find pending action to replace for {vehID}")


def get_mission_action_info(vehID):
    """Gets the current action details from the global parsed mission XML."""
    global mission_root_global # Access the global variable
    if mission_root_global is None:
        return {"type": "N/A", "target": "N/A", "status": "No Missions"}

    action = getAction(vehID, mission_root_global) # Use getAction to find the pending one

    if action is not None:
         return {
                "type": action.get("type", "N/A"),
                "target": action.get("target", "N/A"),
                "status": action.get("status", "0") # Default to 0 if missing
            }
    else:
        # Check if mission exists but all actions are done
        for mission in mission_root_global.findall(".//mission[@id='{}']".format(vehID)):
             if len(mission.findall("action")) > 0: # Mission exists and had actions
                  # Check if ALL are status 3 (or if last one is 3?)
                  all_done = True
                  for act in mission.findall("action"):
                      if act.get("status") != "3":
                          all_done = False
                          break
                  if all_done:
                       # Return last action's info but with status 'Completed'
                       last_action = mission.findall("action")[-1]
                       return { "type": last_action.get("type", "N/A"),
                                "target": last_action.get("target", "N/A"),
                                "status": "Completed" }
             # If mission exists but has no actions, or couldn't determine completed state
             break # Stop after finding the mission element
        # If mission wasn't found or state unclear
        return {"type": "Unknown", "target": "Unknown", "status": "Unknown"}

# --- Main Simulation Function ---
def run_simulation(mapName_param, mode):
    global data_queue, monitor_thread, mission_root_global, metadata_root_global, routes_root_global
    global mapName # Set global mapName used by other functions if needed
    mapName = mapName_param

    # --- Initialize Queue ---
    data_queue = queue.Queue() # Ensure it's a fresh queue

    # --- File Paths ---
    base_path = f"cases/{mapName}"
    mission_file_path = f"{base_path}/missions.mis.xml"
    metadata_file_path = f"{base_path}/metaData.xml" # Corrected case
    routes_file_path = f"{base_path}/MyRoutes.rou.xml" # Assuming this is needed
    config_file_path = f"{base_path}/network.sumocfg"

    # --- Parse Configuration/Mission Files ---
    print("Parsing configuration files...")
    try:
        mission_tree = ET.parse(mission_file_path)
        mission_root_global = mission_tree.getroot()
        print(f"Successfully parsed missions from {mission_file_path}")
    except FileNotFoundError:
        print(f"ERROR: Mission file not found: {mission_file_path}")
        mission_root_global = None
        # Decide whether to exit or continue without missions
    except ET.ParseError as e:
        print(f"ERROR: Failed to parse mission file {mission_file_path}: {e}")
        mission_root_global = None

    try:
        metadata_tree = ET.parse(metadata_file_path)
        metadata_root_global = metadata_tree.getroot()
        print(f"Successfully parsed metadata from {metadata_file_path}")
    except FileNotFoundError:
        print(f"ERROR: Metadata file not found: {metadata_file_path}")
        metadata_root_global = None
    except ET.ParseError as e:
        print(f"ERROR: Failed to parse metadata file {metadata_file_path}: {e}")
        metadata_root_global = None

    try:
        routes_tree = ET.parse(routes_file_path)
        routes_root_global = routes_tree.getroot()
        print(f"Successfully parsed routes from {routes_file_path}")
    except FileNotFoundError:
        print(f"Warning: Routes file not found: {routes_file_path}")
        routes_root_global = None
    except ET.ParseError as e:
        print(f"Warning: Failed to parse routes file {routes_file_path}: {e}")
        routes_root_global = None

    # --- Create Results Directory ---
    directory = mode
    parent_dir = f"{base_path}/results/"
    folderPath = os.path.join(parent_dir, directory)
    try:
        if not path.exists(folderPath):
            os.makedirs(folderPath) # Use makedirs to create parent dirs if needed
            print(f"Created results directory: {folderPath}")
    except OSError as e:
         print(f"ERROR creating results directory {folderPath}: {e}")
         # Decide whether to continue without saving results

    # --- Start Monitor GUI Thread ---
    def gui_thread_target():
        try:
            print("Monitor GUI thread starting.")
            monitor_gui.start_monitor_gui(data_queue)
            print("Monitor GUI thread finished.")
        except Exception as e:
            print(f"ERROR in Monitor GUI thread: {e}")
            import traceback
            traceback.print_exc()

    monitor_thread = threading.Thread(target=gui_thread_target, daemon=True)
    monitor_thread.start()
    print("Waiting for GUI thread to initialize...")
    time.sleep(1.5) # Give GUI thread a moment longer

    # --- SUMO Command ---
    # Ensure paths use forward slashes or are raw strings for cross-platform compatibility if needed
    # config_file_path_traci = config_file_path.replace("\\", "/") # Example
    sumoConfig = ["-c", config_file_path, "-S"] # Use variable path
    sumoCmd = [sumoBinary, sumoConfig[0], sumoConfig[1], sumoConfig[2]]

    # --- Initialize Simulation Variables (from original 'start') ---
    step = 0
    ttWaiting = 0 # Total truck waiting time per interval?
    nbTrucks = PL.countTrucks(mission_root_global) if mission_root_global else 0
    print(f"Number of trucks detected in mission file: {nbTrucks}")

    inTrucks = [] # List of trucks that have entered simulation
    outTrucks = [] # List of trucks that have left simulation
    inPort = [] # Trucks currently inside specific area (Entry1/Exit1 logic)
    begin = datetime.now()

    dynamicAvgSpeeds=[]
    dynamicSpeeds=[] # Speeds within the current interval

    # Statistics Lists (per truck, reset each interval)
    distances = PL.initList(nbTrucks, 0.0)
    speeds = PL.initList(nbTrucks, 0.0)
    speedFactors = PL.initList(nbTrucks, 0.0)
    co2s = PL.initList(nbTrucks, 0.0)
    noxs = PL.initList(nbTrucks, 0.0)

    # Report Strings (accumulated over simulation)
    truckReport = ""
    distancesRep = getHeader(nbTrucks, "trk") + "\n"
    speedsRep = getHeader(nbTrucks, "trk") + "\n"
    speedFactorsRep = getHeader(nbTrucks, "trk") + "\n"
    co2sRep = getHeader(nbTrucks, "trk") + "\n"
    noxsRep = getHeader(nbTrucks, "trk") + "\n"

    blocked_counter = {}
    # parked = 0 # Removed, use traci.parkingarea.getVehicleCount directly if needed
    # capacity = 0 # Removed, calculate dynamically if needed

    max_steps = 30000 # Define max steps as a variable

    print(f"Starting simulation at {begin.strftime('%H:%M:%S')}")
    print(f"Map: {mapName}, Mode: {mode}, Max Steps: {max_steps}")

    # --- Main Simulation Loop ---
    simulation_running = True
    try:
        print("Attempting to start TraCI...")
        traci.start(sumoCmd)
        print("TraCI Connection Established.")
        initMode(mode, mapName) # Initialize mode after connection

        while simulation_running:
            try:
                traci.simulationStep()
                step += 1
                current_step_truck_data_for_gui = [] # Data bundle for monitor GUI
                active_truck_ids = set(traci.vehicle.getIDList()) # Get active vehicles

                currentTrucks_this_step = [] # IDs of trucks active in this step for stats
                dynamicSpeeds = [] # Reset speeds for this step's average calculation

                # --- Main Vehicle Processing ---
                for vehID in active_truck_ids:

                    # --- Process Trucks Only ---
                    if "trk" in vehID:
                        currentTrucks_this_step.append(vehID) # Add to list for interval stats
                        if vehID not in inTrucks: inTrucks.append(vehID) # Track first appearance

                        index = -1
                        try:
                           index = int(vehID[3:]) - 1 # Calculate index for stats lists
                           if index < 0 or index >= nbTrucks:
                               print(f"Warning: Truck ID '{vehID}' resulted in invalid index {index}. Skipping stats update.")
                               index = -1 # Prevent list index error
                        except ValueError:
                           print(f"Warning: Could not parse index from truck ID '{vehID}'. Skipping stats update.")
                           index = -1

                        # --- Get Mission Info (for GUI and Logic) ---
                        mission_info = get_mission_action_info(vehID)

                        # --- Get TraCI Data (for GUI and Stats) ---
                        road_id = "N/A"
                        speed_ms = 0.0
                        wait_time_accumulated = 0.0
                        distance_step = 0.0
                        speed_factor = 1.0
                        co2_step = 0.0
                        nox_step = 0.0
                        is_stopped = False
                        current_speed_kmh = 0.0

                        try:
                            # Efficiently get multiple values if possible (SUMO version dependent)
                            # Example: subResults = traci.vehicle.getSubscriptionResults(vehID) if subscribed
                            road_id = traci.vehicle.getRoadID(vehID)
                            speed_ms = traci.vehicle.getSpeed(vehID)
                            wait_time_accumulated = traci.vehicle.getAccumulatedWaitingTime(vehID)
                            distance_step = traci.vehicle.getDistance(vehID) # Distance covered in the last step
                            speed_factor = traci.vehicle.getSpeedFactor(vehID)
                            co2_step = traci.vehicle.getCO2Emission(vehID)
                            nox_step = traci.vehicle.getNOxEmission(vehID)
                            is_stopped = traci.vehicle.isStopped(vehID)
                            current_speed_kmh = speed_ms * 3.6

                            # Alert checks (from original)
                            if current_speed_kmh > 100: print(f"*** alert *** {vehID} speed= {current_speed_kmh:.1f} km/h")
                            if speed_factor > 2: print(f"*** alert *** {vehID} speedFactor= {speed_factor:.1f}")

                        except traci.TraCIException as e:
                            # Vehicle might have just left - use default values
                            print(f"Warning: TraCIException for {vehID} (likely departed): {e}")
                            road_id = "Departed?" # Indicate departure

                        # --- Prepare Data Bundle for GUI Monitor ---
                        truck_info_bundle = {
                            "id": vehID,
                            "action_type": mission_info["type"],
                            "action_target": mission_info["target"],
                            "mission_status": mission_info["status"],
                            "road_id": road_id,
                            "speed": current_speed_kmh,
                            "wait_time": wait_time_accumulated # Total accumulated wait time
                        }
                        current_step_truck_data_for_gui.append(truck_info_bundle)

                        # --- Original Core Mission Logic ---
                        action = getAction(vehID, mission_root_global) # Get current pending action

                        if action is not None:
                            current_action_status = action.get("status", "0")
                            action_type = action.get("type")
                            action_target = action.get("target") # e.g., ParkingArea ID

                            if current_action_status == '0':
                                # Assign the mission if status is '0'
                                assignMission(vehID, action) # This sets status to '1' internally

                            elif current_action_status == '1': # Action is in progress
                                # Check for completion conditions or parking logic
                                status_updated_this_step = False # Flag to prevent multiple updates

                                # Speed factor adjustment logic (mode[6])
                                try:
                                    if mode[6] == "1" and not is_stopped and action_type != 'Go':
                                        target_full = False
                                        if action_target: # Check if target exists
                                            target_full = isFull(action_target) # Check if associated parking area is full

                                        if target_full:
                                            if speed_factor > 0.5:
                                                print(f"{vehID}: Target '{action_target}' is full. Reducing speed factor to 0.5")
                                                traci.vehicle.setSpeedFactor(vehID, 0.5)
                                        elif speed_factor < 1.0: # Target not full, restore speed
                                            print(f"{vehID}: Target '{action_target}' not full. Increasing speed factor to 1.0")
                                            traci.vehicle.setSpeedFactor(vehID, 1.0)
                                except IndexError:
                                    print(f"Warning: Mode string '{mode}' too short for speed factor logic (mode[6]).")
                                except traci.TraCIException as e:
                                     print(f"Warning: TraCI error adjusting speed factor for {vehID}: {e}")


                                # Parking specific logic (mode[5])
                                if action_type == 'Park':
                                    try:
                                        if mode[5] == "0": # Mode without proactive check
                                            if is_stopped:
                                                print(f"{vehID}: Stopped for Park action (Mode *0*). Status -> '2'.")
                                                action.set('status', '2')
                                                status_updated_this_step = True
                                            elif isParkWaiting(vehID): # Custom function checking proximity and speed
                                                print(f"{vehID}: Park waiting detected (Mode *0*). Finding alternative.")
                                                alternativeAction = PL.getAlternative(metadata_root_global, action_target) # Needs metadata
                                                if alternativeAction != "no alternatives" and isinstance(alternativeAction, ET.Element):
                                                     traci.vehicle.replaceStop(vehID, duration=0, flags=0) # Clear existing stop intention
                                                     setAction(vehID, mission_root_global, alternativeAction) # Replace action in memory
                                                     # Action status is reset to '0' by setAction, will be assigned next step
                                                else:
                                                     print(f"{vehID}: No alternative parking found.")
                                        elif mode[5] == "1": # Mode with proactive check
                                             if is_stopped:
                                                 print(f"{vehID}: Stopped for Park action (Mode *1*). Status -> '2'.")
                                                 action.set('status', '2')
                                                 status_updated_this_step = True
                                             # Proactive check if target is full
                                             elif action_target and isFull(action_target):
                                                 print(f"{vehID}: Target parking '{action_target}' is full (Mode *1*). Finding alternative.")
                                                 alternativeAction = PL.getAlternative(metadata_root_global, action_target)
                                                 if alternativeAction != "no alternatives" and isinstance(alternativeAction, ET.Element) and not isFull(alternativeAction.get("target")):
                                                      print(f"{vehID}: Found alternative parking '{alternativeAction.get('target')}'. Replacing action.")
                                                      traci.vehicle.replaceStop(vehID, duration=0, flags=0)
                                                      setAction(vehID, mission_root_global, alternativeAction)
                                                 else:
                                                      print(f"{vehID}: Target full and no suitable alternative found.")
                                             # Add else if needed: What happens if not stopped and not full? Keep status '1'.

                                    except IndexError:
                                        print(f"Warning: Mode string '{mode}' too short for parking logic (mode[5]).")
                                    except traci.TraCIException as e:
                                        print(f"Warning: TraCI error during parking logic for {vehID}: {e}")

                                # Load/Unload completion check
                                elif action_type in ['Load', 'Unload'] and is_stopped and not status_updated_this_step:
                                    print(f"{vehID}: Stopped for {action_type} action. Status -> '2'.")
                                    action.set('status', '2')
                                    status_updated_this_step = True

                                # Go completion check (often immediate or based on reaching edge?)
                                # This needs clarification - when is 'Go' completed? Reaching target edge?
                                # For now, assume 'Go' completes when status is manually changed or mission ends.
                                # Let's tentatively set it to '3' if the route index reaches the end?
                                elif action_type == 'Go' and not status_updated_this_step:
                                     try:
                                         route_idx = traci.vehicle.getRouteIndex(vehID)
                                         route_len = len(traci.vehicle.getRoute(vehID))
                                         if route_idx == route_len - 1: # Reached last edge of current route
                                              print(f"{vehID}: Reached end of route for Go action. Status -> '3'.")
                                              action.set('status', '3') # Mark 'Go' as done when route ends
                                              status_updated_this_step = True
                                     except traci.TraCIException: pass # Ignore errors if vehicle departing


                            elif current_action_status == '2': # Action is 'done' (e.g., stopped for Load/Unload/Park)
                                # Check condition to move to status '3' (e.g., no longer stopped)
                                if action_type in ['Load', 'Unload', 'Park'] and not is_stopped:
                                    print(f"{vehID}: Finished stop for {action_type}. Status -> '3'.")
                                    action.set('status', '3')
                                # 'Go' transitions handled in status '1' check for now

                            # Persist mission_root_global changes if needed (e.g., save XML periodically)
                            # if step % 100 == 0: save_mission_xml(mission_root_global, mission_file_path)


                        # --- Original Statistics Collection ---
                        if index != -1: # Only update stats if index is valid
                            if distance_step > 0:
                                distances[index] += distance_step / 1000.0 # Add distance from this step in km

                            dynamicSpeeds.append(current_speed_kmh) # Collect for interval average

                            if speed_ms >= 0:
                                speeds[index] += current_speed_kmh # Sum speeds for truck's avg speed calc later

                            if speed_factor >= 0:
                                speedFactors[index] += speed_factor # Sum speed factors

                            if co2_step > 0:
                                co2s[index] += co2_step / 1000.0 # Sum CO2 in g

                            if nox_step > 0:
                                noxs[index] += nox_step / 1000.0 # Sum NOx in g

                            if speed_ms < 0.1: # Use threshold for waiting
                                ttWaiting += 1 # Increment total waiting ticks over the interval

                    # --- End Truck Processing (`if "trk" in vehID`) ---

                    # --- Teleportation Logic (Apply to all vehicles?) ---
                    if vehID not in blocked_counter: blocked_counter[vehID] = 0
                    current_speed = traci.vehicle.getSpeed(vehID) # Get speed again if not truck

                    if current_speed < 0.1:
                        blocked_counter[vehID] += 1
                    else:
                        blocked_counter[vehID] = 0

                    if blocked_counter[vehID] > 60: # Increased threshold slightly
                        if not "trk" in vehID:
                            print(f"⚡ {vehID} blocked for {blocked_counter[vehID]} steps. Attempting teleport...")
                            try:
                                route = traci.vehicle.getRoute(vehID)
                                route_index = traci.vehicle.getRouteIndex(vehID)
                                # Simple teleport: move ahead on the *current* edge if possible
                                current_lane = traci.vehicle.getLaneID(vehID)
                                current_pos = traci.vehicle.getLanePosition(vehID)
                                lane_len = traci.lane.getLength(current_lane)
                                move_to_pos = min(lane_len - 1.0, current_pos + 15.0) # Move 15m ahead or near end

                                traci.vehicle.moveTo(vehID, current_lane, move_to_pos)
                                print(f"  {vehID} teleported on {current_lane} to position {move_to_pos:.1f}")
                                blocked_counter[vehID] = 0 # Reset counter after teleport
                            except traci.TraCIException as e:
                                print(f"  Error teleporting {vehID}: {e}. Vehicle may have departed.")
                                blocked_counter[vehID] = 0 # Reset anyway
                            except Exception as e:
                                print(f"  Unexpected error during teleport logic for {vehID}: {e}")
                                blocked_counter[vehID] = 0

                # --- End of Vehicle Processing Loop ---

                # --- Send data to GUI Monitor ---
                if current_step_truck_data_for_gui: # Only send if trucks were processed
                    data_queue.put(current_step_truck_data_for_gui)

                # --- Update outTrucks list ---
                active_truck_ids_this_step = set(currentTrucks_this_step)
                for v_id in inTrucks:
                   if v_id not in active_truck_ids_this_step and v_id not in outTrucks:
                       print(f"Truck {v_id} exited simulation.")
                       outTrucks.append(v_id)

                # --- Interval Reporting Logic (Original) ---
                interval = 60 # steps per minute (adjust if step != 1 second)
                if step % interval == 0 or step == 1:
                    print(f"\n--- Reporting Interval: Step {step} ---")
                    # Calculate dynamic average speed for the interval
                    avgSpeed_interval = sum(dynamicAvgSpeeds) / len(dynamicAvgSpeeds) if dynamicAvgSpeeds else 0.0
                    dynamicAvgSpeeds = [] # Reset for next interval

                    # Calculate parking capacity (if needed)
                    parked_count = 0
                    total_capacity = 0
                    capacity_percent = 0.0
                    try:
                        # Your lines:
                        total_capacity = int(traci.simulation.getParameter("Parking1", "parkingArea.capacity")) + int(traci.simulation.getParameter("Parking2", "parkingArea.capacity"))
                        parked_count = traci.parkingarea.getVehicleCount("Parking1") + traci.parkingarea.getVehicleCount("Parking2")

                        # Calculate percentage
                        capacity_percent = (parked_count * 100.0 / total_capacity) if total_capacity > 0 else 0.0
                        print(f"  Parking Stats: Total Parked={parked_count}, Total Capacity={total_capacity}")

                    except traci.TraCIException as e:
                        print(f"Warning: Error getting parking info via TraCI: {e}")
                    except (ValueError, TypeError) as e:
                        # Catches errors if getParameter returns None or non-numeric string
                        print(f"Warning: Error processing parking capacity parameter: {e}")
                    # --- End parking stats calculation ---

                    # Build Report String Line
                    if truckReport == "":
                        truckReport = "step;time;inTrucks[#];Total distance[km/T.U];Average Speed[km/h/truck];parked[#];Parkings[%];Total CO2[g/T.U];Total NOx[g/T.U];TWT [T.U];inPort[#];Current Trucks[#]\n"

                    report_line = f"{step};{step / interval:.1f};{len(inTrucks)};"
                    report_line += f"{sum(distances):.3f};{avgSpeed_interval:.2f};"
                    report_line += f"{parked_count};{capacity_percent:.1f};" # Use calculated values
                    report_line += f"{sum(co2s):.3f};{sum(noxs):.3f};"
                    report_line += f"{ttWaiting};{len(inPort)};{len(currentTrucks_this_step)}\n"
                    truckReport += report_line
                    print(f"Report Line: {report_line.strip()}")

                    # Append individual stats to report strings
                    distancesRep += PL.listToLine(distances, 1) + "\n"
                    speedsRep += PL.listToLine(speeds, interval) + "\n" # Average speed over interval
                    speedFactorsRep += PL.listToLine(speedFactors, interval) + "\n" # Average speed factor
                    co2sRep += PL.listToLine(co2s, 1) + "\n" # Total CO2 over interval
                    noxsRep += PL.listToLine(noxs, 1) + "\n" # Total NOx over interval

                    # Reset interval statistics
                    distances = PL.initList(nbTrucks, 0.0)
                    speeds = PL.initList(nbTrucks, 0.0)
                    speedFactors = PL.initList(nbTrucks, 0.0)
                    co2s = PL.initList(nbTrucks, 0.0)
                    noxs = PL.initList(nbTrucks, 0.0)
                    ttWaiting = 0 # Reset waiting time counter for interval

                # --- Check Simulation End Conditions ---
                if nbTrucks > 0 and len(outTrucks) == nbTrucks:
                    print(f"\nAll {nbTrucks} trucks have exited. Ending simulation at step {step}.")
                    simulation_running = False
                elif step >= max_steps:
                    print(f"\nMaximum steps ({max_steps}) reached. Ending simulation.")
                    simulation_running = False

                # Basic throttling (optional)
                # time.sleep(0.01)

            except traci.TraCIException as e:
                print(f"\nERROR: TraCI Error during simulation step {step}: {e}")
                print("Attempting to end simulation gracefully...")
                simulation_running = False # Stop on major TraCI error
            except KeyboardInterrupt: # Allow Ctrl+C to stop
                 print("\nKeyboardInterrupt received. Stopping simulation...")
                 simulation_running = False
            except Exception as e:
                 print(f"\nERROR: Unexpected Error during simulation step {step}: {e}")
                 import traceback
                 traceback.print_exc() # Print full traceback for debugging
                 simulation_running = False # Stop on other errors

        # --- End of Simulation Loop (`while simulation_running:`) ---

    except traci.TraCIException as e:
        print(f"\nERROR: Failed to establish TraCI connection or fatal TraCI error: {e}")
        # Cannot proceed without TraCI
    except Exception as e:
        print(f"\nERROR: An unexpected error occurred before simulation loop: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # --- Post-Simulation Processing & Cleanup ---
        print("\n--- Simulation Loop Finished ---")

        # --- Save Report Files (Original Logic) ---
        end = datetime.now()
        duration_sim = end - begin
        print(f"Simulation started at {begin.strftime('%H:%M:%S')} ended at {end.strftime('%H:%M:%S')} (Duration: {duration_sim})")
        print('Saving results files...')

        try:
            # Save Truck Report
            report_header = f"Simulation started at {begin.strftime('%H:%M:%S')} ended at {end.strftime('%H:%M:%S')}\n"
            report_path = os.path.join(folderPath, f"{mode}_Truck Report.csv")
            with open(report_path, "w") as f:
                f.write(report_header + truckReport)
            print(f"Saved: {report_path}")

            # Save Individual Stats Reports
            file_mappings = {
                "_DistancesRep.csv": distancesRep,
                "_SpeedsRep.csv": speedsRep,
                "_SpeedFactorsRep.csv": speedFactorsRep,
                "_co2sRep.csv": co2sRep,
                "_noxsRep.csv": noxsRep,
            }
            for suffix, data_str in file_mappings.items():
                file_path = os.path.join(folderPath, f"{mode}{suffix}")
                with open(file_path, "w") as f:
                    f.write(data_str)
                print(f"Saved: {file_path}")

            # Add back the Excel grouping logic if needed here
            # Be careful with dependencies (pandas) and file paths

        except IOError as e:
            print(f"ERROR saving report files to {folderPath}: {e}")
        except Exception as e:
            print(f"ERROR during report saving: {e}")


        # --- Signal GUI and Close TraCI ---
        print("Sending shutdown signal to Monitor GUI...")
        if data_queue: # Check if queue exists
             data_queue.put("SHUTDOWN")

        print("Closing TraCI connection...")
        try:
            traci.close()
            print("TraCI closed.")
        except traci.TraCIException as e:
             print(f"Warning: TraCI exception during close: {e}")
        except Exception as e:
            print(f"Warning: Error closing TraCI: {e}")

        print("Waiting briefly for GUI thread...")
        if monitor_thread and monitor_thread.is_alive():
             monitor_thread.join(timeout=2.0) # Wait max 2 seconds for GUI thread
             if monitor_thread.is_alive():
                  print("Warning: Monitor GUI thread did not exit cleanly.")

        print("--- Starter.run_simulation finished ---")
        # Removed sys.exit() - let the calling script (Main.py) control exit

# --- Ensure helper functions like getAlternative use metadata_root_global ---
# Example modification:
# def getAlternative(target): # Removed metadataRoot parameter
#    global metadata_root_global
#    if metadata_root_global is None: return "no alternatives"
#    # ... rest of the logic using metadata_root_global ...


# --- Define 'start' as an alias for run_simulation ---
# This allows Main.py to keep calling Starter.start
start = run_simulation

# --- Main execution block (for running Starter.py directly) ---
if __name__ == "__main__":
    # Example direct execution
    mapName_main = "Nantes"
    mode_main = "Mode111"
    print(f"Running Starter.py directly: Map={mapName_main}, Mode={mode_main}")
    run_simulation(mapName_main, mode_main) # Call the main function
    print("Direct execution of Starter.py complete.")

# --- END OF FILE Starter.py ---