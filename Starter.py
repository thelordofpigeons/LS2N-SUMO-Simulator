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
         # Try alternative common naming
         config_path = f"cases/{mapName}/Network.sumocfg" # Note capital N
         if not os.path.exists(config_path):
            print(f"Warning: SUMO config file not found at {config_path} or cases/{mapName}/network.sumocfg")
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
        count = traci.parkingarea.getVehicleCount(target_parking_area_id)
        # SUMO uses <param key="parkingArea.capacity" value="X"/> in the parkingArea definition
        # or <parkingArea id="Prk1" lane="-101938#11_0" startPos="10" endPos="60" capacity="10"/>
        # Check if 'capacity' is directly available as an attribute for the parkingArea object in TraCI
        # Trying to get capacity parameter, which is how it's often defined if not directly an attribute
        capacity_str = ""
        try:
            # This is the standard way to get <param> values associated with simulation objects
            capacity_str = traci.simulation.getParameter(target_parking_area_id, "parkingArea.capacity")
        except traci.TraCIException:
             # If getParameter fails, it might be directly available via parkingarea.getCapacity
             # This depends on the SUMO version and how parking areas are defined/queried.
             # Let's assume if the above fails, we try a more direct approach if available or fallback.
             # For now, let's assume the parameter method is primary.
             # If parkingArea.getCapacity exists and is reliable, it could be a fallback:
             # capacity = traci.parkingarea.getCapacity(target_parking_area_id)
             pass # Handled below

        if not capacity_str: # If getParameter returned empty or failed
            # Fallback or error: try to get it from the XML definition if really needed,
            # or assume a default, or make it a hard requirement for the parkingArea definition.
            # For now, if not found via getParameter, we'll log a warning.
            # A more robust solution would be to parse the additional file where parkings are defined.
            print(f"Warning: Capacity parameter not directly found for parking area '{target_parking_area_id}'. "
                  f"Ensure 'parkingArea.capacity' param is set or it's an attribute in your SUMO version.")
            # Attempting to read from a typical parkingArea definition attribute as a last resort
            # This is speculative and might not work for all SUMO versions or definitions.
            # A common way to define capacity is directly in the <parkingArea> tag:
            # <parkingArea id="Prk1" lane="..." capacity="10" .../>
            # However, traci.simulation.getParameter is usually for <param> sub-elements.
            # The traci.parkingarea module itself might have a getCapacity method in newer SUMO.
            # Let's assume for now that if getParameter doesn't work, we cannot determine capacity reliably.
            return False # Cannot determine fullness if capacity is unknown/unretrievable via TraCI

        capacity = int(capacity_str)
        return count >= capacity

    except traci.TraCIException as e:
        print(f"Warning: TraCI error checking fullness of parking area '{target_parking_area_id}': {e}")
        return False
    except (ValueError, TypeError) as e:
        print(f"Warning: Error converting capacity parameter '{capacity_str}' to int for '{target_parking_area_id}': {e}")
        return False
    except Exception as e:
        print(f"Warning: Unexpected error in isFull for '{target_parking_area_id}': {e}")
        return False


def assignMission(vehID, action):
    """Assigns the next mission step using TraCI commands and updates the action status in memory."""
    global mission_root_global

    if action is None:
        print(f"Warning: assignMission called with None action for {vehID}")
        return

    newTarget = action.get("target")
    newEdge = action.get("edge")
    actionType = action.get("type")

    if not newTarget or not newEdge or not actionType:
         print(f"ERROR: Incomplete action details for {vehID}: Type={actionType}, Target={newTarget}, Edge={newEdge}")
         return

    print(f"{vehID}: Assigning Action: Type={actionType}, Target={newTarget}, Edge={newEdge}")

    try:
        traci.vehicle.changeTarget(vehID, newEdge)
        stop_duration = 600
        if actionType == "Load" or actionType == "Unload":
            stop_duration = 180
            traci.vehicle.setParkingAreaStop(vehID, newTarget, duration=stop_duration)
            print(f"  {vehID}: Set ParkingAreaStop at '{newTarget}' for {stop_duration}s")
        elif actionType == "Park":
             traci.vehicle.setParkingAreaStop(vehID, newTarget, duration=stop_duration)
             print(f"  {vehID}: Set ParkingAreaStop at '{newTarget}' for {stop_duration}s")
        elif actionType == "Go":
             print(f"  {vehID}: Route set towards Edge '{newEdge}'. No stop defined.")
             pass
        else:
            print(f"Warning: Unknown action type '{actionType}' for {vehID}. Cannot set stop.")

        action.set("status", "1")
        print(f"  {vehID}: Action status set to '1'")

    except traci.TraCIException as e:
        print(f"ERROR: TraCI error assigning mission for {vehID} (Target:{newTarget}, Edge:{newEdge}): {e}")
    except Exception as e:
        print(f"ERROR: Unexpected error assigning mission for {vehID}: {e}")


def getAction(vehID, mission_root):
    root_to_use = mission_root_global if mission_root_global is not None else mission_root
    if root_to_use is None:
        return None
    for mission in root_to_use.findall(".//mission[@id='{}']".format(vehID)):
        for action in mission.findall("action"):
            if action.get("status") != "3":
                return action
        return None
    return None


def setAction(vehID, mission_root, newAction):
    global mission_root_global
    root_to_use = mission_root_global if mission_root_global is not None else mission_root
    if root_to_use is None: return

    action_updated = False
    for mission in root_to_use.findall(".//mission[@id='{}']".format(vehID)):
        for action in mission.findall("action"):
            if action.get("status") != "3":
                old_target = action.get('target')
                action.set('target', newAction.get('target'))
                action.set('edge', newAction.get('edge'))
                action.set('type', newAction.get('type'))
                action.set('status', '0')
                print(f"{vehID}: Replaced action target '{old_target}' with '{newAction.get('target')}', status reset to '0'")
                action_updated = True
                return
    if not action_updated:
        print(f"Warning: setAction - Could not find pending action to replace for {vehID}")


def get_mission_action_info(vehID):
    global mission_root_global
    if mission_root_global is None:
        return {"type": "N/A", "target": "N/A", "status": "No Missions"}

    action = getAction(vehID, mission_root_global)

    if action is not None:
         return {
                "type": action.get("type", "N/A"),
                "target": action.get("target", "N/A"),
                "status": action.get("status", "0")
            }
    else:
        for mission in mission_root_global.findall(".//mission[@id='{}']".format(vehID)):
             if len(mission.findall("action")) > 0:
                  all_done = True
                  for act in mission.findall("action"):
                      if act.get("status") != "3":
                          all_done = False; break
                  if all_done:
                       last_action = mission.findall("action")[-1]
                       return { "type": last_action.get("type", "N/A"),
                                "target": last_action.get("target", "N/A"),
                                "status": "Completed" }
             break
        return {"type": "Unknown", "target": "Unknown", "status": "Unknown"}

# --- Main Simulation Function ---
# --- MODIFIED HERE ---
def run_simulation(mapName_param, mode, simulation_end_seconds=None):
    global data_queue, monitor_thread, mission_root_global, metadata_root_global, routes_root_global
    global mapName
    mapName = mapName_param

    data_queue = queue.Queue()

    base_path = f"cases/{mapName}"
    mission_file_path = f"{base_path}/missions.mis.xml"
    metadata_file_path = f"{base_path}/metaData.xml"
    routes_file_path = f"{base_path}/MyRoutes.rou.xml"
    config_file_path = f"{base_path}/network.sumocfg"
    # Also check for Network.sumocfg (capital N)
    if not os.path.exists(config_file_path):
        config_file_path_alt = f"{base_path}/Network.sumocfg"
        if os.path.exists(config_file_path_alt):
            config_file_path = config_file_path_alt
        else:
            print(f"ERROR: SUMO config file not found at {config_file_path} or {config_file_path_alt}")
            # Decide how to handle: return or raise error
            return


    print("Parsing configuration files...")
    try:
        mission_tree = ET.parse(mission_file_path)
        mission_root_global = mission_tree.getroot()
        print(f"Successfully parsed missions from {mission_file_path}")
    except FileNotFoundError:
        print(f"ERROR: Mission file not found: {mission_file_path}")
        mission_root_global = None
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

    directory = mode
    parent_dir = f"{base_path}/results/"
    folderPath = os.path.join(parent_dir, directory)
    try:
        if not path.exists(folderPath):
            os.makedirs(folderPath)
            print(f"Created results directory: {folderPath}")
    except OSError as e:
         print(f"ERROR creating results directory {folderPath}: {e}")

    def gui_thread_target():
        try:
            print("Monitor GUI thread starting.")
            monitor_gui.start_monitor_gui(data_queue)
            print("Monitor GUI thread finished.")
        except Exception as e:
            print(f"ERROR in Monitor GUI thread: {e}")
            traceback.print_exc()

    monitor_thread = threading.Thread(target=gui_thread_target, daemon=True)
    monitor_thread.start()
    print("Waiting for GUI thread to initialize...")
    time.sleep(1.5)

    sumoConfig = ["-c", config_file_path, "-S"]
    sumoCmd = [sumoBinary, sumoConfig[0], sumoConfig[1], sumoConfig[2]]

    step = 0
    ttWaiting = 0
    nbTrucks = PL.countTrucks(mission_root_global) if mission_root_global else 0
    print(f"Number of trucks detected in mission file: {nbTrucks}")

    inTrucks = []
    outTrucks = []
    inPort = []
    begin = datetime.now()

    dynamicAvgSpeeds=[]
    dynamicSpeeds=[]

    distances = PL.initList(nbTrucks, 0.0)
    speeds = PL.initList(nbTrucks, 0.0)
    speedFactors = PL.initList(nbTrucks, 0.0)
    co2s = PL.initList(nbTrucks, 0.0)
    noxs = PL.initList(nbTrucks, 0.0)

    truckReport = ""
    distancesRep = getHeader(nbTrucks, "trk") + "\n"
    speedsRep = getHeader(nbTrucks, "trk") + "\n"
    speedFactorsRep = getHeader(nbTrucks, "trk") + "\n"
    co2sRep = getHeader(nbTrucks, "trk") + "\n"
    noxsRep = getHeader(nbTrucks, "trk") + "\n"

    blocked_counter = {}
    
    # --- MODIFIED HERE: Determine max_steps ---
    max_steps = 30000 # Default
    if simulation_end_seconds is not None and simulation_end_seconds > 0:
        max_steps = int(simulation_end_seconds) # Assuming 1 step = 1 second
        print(f"Simulation end time set by GUI: {max_steps} steps/seconds.")
    else:
        print(f"Using default simulation end time: {max_steps} steps/seconds.")
    # --- END MODIFICATION ---


    print(f"Starting simulation at {begin.strftime('%H:%M:%S')}")
    print(f"Map: {mapName}, Mode: {mode}, Max Steps: {max_steps}")

    simulation_running = True
    try:
        print("Attempting to start TraCI...")
        traci.start(sumoCmd)
        print("TraCI Connection Established.")
        initMode(mode, mapName)

        while simulation_running:
            try:
                traci.simulationStep()
                step += 1
                current_step_truck_data_for_gui = []
                active_truck_ids = set(traci.vehicle.getIDList())

                currentTrucks_this_step = []
                dynamicSpeeds = []

                for vehID in active_truck_ids:
                    if "trk" in vehID:
                        currentTrucks_this_step.append(vehID)
                        if vehID not in inTrucks: inTrucks.append(vehID)

                        index = -1
                        try:
                           index = int(vehID[3:]) - 1
                           if index < 0 or index >= nbTrucks: index = -1
                        except ValueError: index = -1

                        mission_info = get_mission_action_info(vehID)
                        road_id, speed_ms, wait_time_accumulated, distance_step, speed_factor, co2_step, nox_step, is_stopped, current_speed_kmh = "N/A", 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, False, 0.0
                        try:
                            road_id = traci.vehicle.getRoadID(vehID)
                            speed_ms = traci.vehicle.getSpeed(vehID)
                            current_speed_kmh = speed_ms * 3.6
                            wait_time_accumulated = traci.vehicle.getAccumulatedWaitingTime(vehID)
                            distance_step = traci.vehicle.getDistance(vehID)
                            speed_factor = traci.vehicle.getSpeedFactor(vehID)
                            co2_step = traci.vehicle.getCO2Emission(vehID)
                            nox_step = traci.vehicle.getNOxEmission(vehID)
                            is_stopped = traci.vehicle.isStopped(vehID)
                            if current_speed_kmh > 100: print(f"*** alert *** {vehID} speed= {current_speed_kmh:.1f} km/h")
                            if speed_factor > 2: print(f"*** alert *** {vehID} speedFactor= {speed_factor:.1f}")
                        except traci.TraCIException: road_id = "Departed?"

                        truck_info_bundle = {
                            "id": vehID, "action_type": mission_info["type"],
                            "action_target": mission_info["target"], "mission_status": mission_info["status"],
                            "road_id": road_id, "speed": current_speed_kmh, "wait_time": wait_time_accumulated
                        }
                        current_step_truck_data_for_gui.append(truck_info_bundle)

                        action = getAction(vehID, mission_root_global)
                        if action is not None:
                            current_action_status = action.get("status", "0")
                            action_type = action.get("type")
                            action_target = action.get("target")

                            if current_action_status == '0':
                                assignMission(vehID, action)
                            elif current_action_status == '1':
                                status_updated_this_step = False
                                try:
                                    if mode[6] == "1" and not is_stopped and action_type != 'Go':
                                        target_full = False
                                        if action_target: target_full = isFull(action_target)
                                        if target_full and speed_factor > 0.5:
                                            print(f"{vehID}: Target '{action_target}' is full. Reducing speed factor to 0.5")
                                            traci.vehicle.setSpeedFactor(vehID, 0.5)
                                        elif not target_full and speed_factor < 1.0:
                                            print(f"{vehID}: Target '{action_target}' not full. Increasing speed factor to 1.0")
                                            traci.vehicle.setSpeedFactor(vehID, 1.0)
                                except IndexError: pass # Mode string too short
                                except traci.TraCIException as e: print(f"Warning: TraCI error adjusting speed factor for {vehID}: {e}")

                                if action_type == 'Park':
                                    try:
                                        if mode[5] == "0":
                                            if is_stopped: action.set('status', '2'); status_updated_this_step = True; print(f"{vehID}: Parked (Mode *0*). Status -> '2'.")
                                            elif isParkWaiting(vehID):
                                                alternativeAction = PL.getAlternative(metadata_root_global, action_target)
                                                if alternativeAction != "no alternatives" and isinstance(alternativeAction, ET.Element):
                                                     traci.vehicle.replaceStop(vehID, duration=0, flags=0)
                                                     setAction(vehID, mission_root_global, alternativeAction)
                                                else: print(f"{vehID}: No alternative parking found.")
                                        elif mode[5] == "1":
                                             if is_stopped: action.set('status', '2'); status_updated_this_step = True; print(f"{vehID}: Parked (Mode *1*). Status -> '2'.")
                                             elif action_target and isFull(action_target):
                                                 alternativeAction = PL.getAlternative(metadata_root_global, action_target)
                                                 if alternativeAction != "no alternatives" and isinstance(alternativeAction, ET.Element) and not isFull(alternativeAction.get("target")):
                                                      traci.vehicle.replaceStop(vehID, duration=0, flags=0)
                                                      setAction(vehID, mission_root_global, alternativeAction)
                                                      print(f"{vehID}: Found alternative parking '{alternativeAction.get('target')}'. Replacing action.")
                                                 else: print(f"{vehID}: Target full and no suitable alternative found (Mode *1*).")
                                    except IndexError: pass # Mode string too short
                                    except traci.TraCIException as e: print(f"Warning: TraCI error during parking logic for {vehID}: {e}")
                                elif action_type in ['Load', 'Unload'] and is_stopped and not status_updated_this_step:
                                    action.set('status', '2'); status_updated_this_step = True; print(f"{vehID}: Stopped for {action_type}. Status -> '2'.")
                                elif action_type == 'Go' and not status_updated_this_step:
                                     try:
                                         if traci.vehicle.getRouteIndex(vehID) == len(traci.vehicle.getRoute(vehID)) - 1:
                                              action.set('status', '3'); status_updated_this_step = True; print(f"{vehID}: Reached end of route for Go. Status -> '3'.")
                                     except traci.TraCIException: pass
                            elif current_action_status == '2':
                                if action_type in ['Load', 'Unload', 'Park'] and not is_stopped:
                                    action.set('status', '3'); print(f"{vehID}: Finished stop for {action_type}. Status -> '3'.")

                        if index != -1:
                            if distance_step > 0: distances[index] += distance_step / 1000.0
                            dynamicSpeeds.append(current_speed_kmh)
                            if speed_ms >= 0: speeds[index] += current_speed_kmh
                            if speed_factor >= 0: speedFactors[index] += speed_factor
                            if co2_step > 0: co2s[index] += co2_step / 1000.0
                            if nox_step > 0: noxs[index] += nox_step / 1000.0
                            if speed_ms < 0.1: ttWaiting += 1

                    if vehID not in blocked_counter: blocked_counter[vehID] = 0
                    current_speed_teleport_check = traci.vehicle.getSpeed(vehID)
                    if current_speed_teleport_check < 0.1: blocked_counter[vehID] += 1
                    else: blocked_counter[vehID] = 0
                    if blocked_counter[vehID] > 60 and not "trk" in vehID:
                        print(f"⚡ {vehID} blocked for {blocked_counter[vehID]} steps. Attempting teleport...")
                        try:
                            current_lane = traci.vehicle.getLaneID(vehID)
                            current_pos = traci.vehicle.getLanePosition(vehID)
                            lane_len = traci.lane.getLength(current_lane)
                            move_to_pos = min(lane_len - 1.0, current_pos + 15.0)
                            traci.vehicle.moveTo(vehID, current_lane, move_to_pos)
                            print(f"  {vehID} teleported on {current_lane} to position {move_to_pos:.1f}")
                            blocked_counter[vehID] = 0
                        except traci.TraCIException as e: print(f"  Error teleporting {vehID}: {e}."); blocked_counter[vehID] = 0
                        except Exception as e: print(f"  Unexpected error during teleport for {vehID}: {e}"); blocked_counter[vehID] = 0

                if current_step_truck_data_for_gui:
                    data_queue.put(current_step_truck_data_for_gui)

                active_truck_ids_this_step = set(currentTrucks_this_step)
                for v_id in inTrucks:
                   if v_id not in active_truck_ids_this_step and v_id not in outTrucks:
                       print(f"Truck {v_id} exited simulation.")
                       outTrucks.append(v_id)

                interval = 60
                if step % interval == 0 or step == 1:
                    print(f"\n--- Reporting Interval: Step {step} ---")
                    avgSpeed_interval = sum(dynamicSpeeds) / len(dynamicSpeeds) if dynamicSpeeds else 0.0 # Corrected this line
                    # dynamicAvgSpeeds was reset above, should use dynamicSpeeds from current interval
                    
                    parked_count, total_capacity, capacity_percent = 0, 0, 0.0
                    try:
                        # Ensure Parking1 and Parking2 are valid IDs in your simulation
                        # These might need to be dynamically discovered or configured per map
                        prk1_id, prk2_id = "Parking1", "Parking2" # Example IDs, replace with actual
                        if metadata_root_global: # If metadata is loaded, try to get parking IDs from there
                            parking_elements = metadata_root_global.find(".//parkings")
                            if parking_elements is not None and len(parking_elements) >= 2:
                                prk1_id = parking_elements[0].get("value") # Assuming 'value' is the ID
                                prk2_id = parking_elements[1].get("value")
                        
                        cap1_str = traci.simulation.getParameter(prk1_id, "parkingArea.capacity")
                        cap2_str = traci.simulation.getParameter(prk2_id, "parkingArea.capacity")
                        total_capacity = (int(cap1_str) if cap1_str else 0) + \
                                         (int(cap2_str) if cap2_str else 0)
                        parked_count = traci.parkingarea.getVehicleCount(prk1_id) + \
                                       traci.parkingarea.getVehicleCount(prk2_id)
                        capacity_percent = (parked_count * 100.0 / total_capacity) if total_capacity > 0 else 0.0
                        print(f"  Parking Stats: Total Parked={parked_count}, Total Capacity={total_capacity}")
                    except traci.TraCIException as e: print(f"Warning: Error getting parking info via TraCI: {e}")
                    except (ValueError, TypeError, IndexError) as e: print(f"Warning: Error processing parking capacity/IDs: {e}")

                    if truckReport == "":
                        truckReport = "step;time;inTrucks[#];Total distance[km/T.U];Average Speed[km/h/truck];parked[#];Parkings[%];Total CO2[g/T.U];Total NOx[g/T.U];TWT [T.U];inPort[#];Current Trucks[#]\n"
                    report_line = f"{step};{step / interval:.1f};{len(inTrucks)};{sum(distances):.3f};{avgSpeed_interval:.2f};{parked_count};{capacity_percent:.1f};{sum(co2s):.3f};{sum(noxs):.3f};{ttWaiting};{len(inPort)};{len(currentTrucks_this_step)}\n"
                    truckReport += report_line
                    print(f"Report Line: {report_line.strip()}")

                    distancesRep += PL.listToLine(distances, 1) + "\n"
                    speedsRep += PL.listToLine(speeds, interval) + "\n"
                    speedFactorsRep += PL.listToLine(speedFactors, interval) + "\n"
                    co2sRep += PL.listToLine(co2s, 1) + "\n"
                    noxsRep += PL.listToLine(noxs, 1) + "\n"

                    distances, speeds, speedFactors, co2s, noxs = (PL.initList(nbTrucks, 0.0) for _ in range(5))
                    ttWaiting = 0

                if nbTrucks > 0 and len(outTrucks) == nbTrucks:
                    print(f"\nAll {nbTrucks} trucks have exited. Ending simulation at step {step}.")
                    simulation_running = False
                elif step >= max_steps: # Check against potentially modified max_steps
                    print(f"\nMaximum steps ({max_steps}) reached. Ending simulation.")
                    simulation_running = False
            except traci.TraCIException as e: print(f"\nERROR: TraCI Error during step {step}: {e}"); simulation_running = False
            except KeyboardInterrupt: print("\nKeyboardInterrupt. Stopping..."); simulation_running = False
            except Exception as e: print(f"\nERROR: Unexpected Error during step {step}: {e}"); traceback.print_exc(); simulation_running = False
    except traci.TraCIException as e: print(f"\nERROR: Failed TraCI connection or fatal error: {e}")
    except Exception as e: print(f"\nERROR: Unexpected error before simulation loop: {e}"); traceback.print_exc()
    finally:
        print("\n--- Simulation Loop Finished ---")
        end = datetime.now()
        duration_sim = end - begin
        print(f"Simulation started at {begin.strftime('%H:%M:%S')} ended at {end.strftime('%H:%M:%S')} (Duration: {duration_sim})")
        print('Saving results files...')
        try:
            report_header = f"Simulation started at {begin.strftime('%H:%M:%S')} ended at {end.strftime('%H:%M:%S')}\n"
            report_path = os.path.join(folderPath, f"{mode}_Truck Report.csv")
            with open(report_path, "w") as f: f.write(report_header + truckReport)
            print(f"Saved: {report_path}")
            file_mappings = {"_DistancesRep.csv": distancesRep, "_SpeedsRep.csv": speedsRep, "_SpeedFactorsRep.csv": speedFactorsRep, "_co2sRep.csv": co2sRep, "_noxsRep.csv": noxsRep}
            for suffix, data_str in file_mappings.items():
                file_path = os.path.join(folderPath, f"{mode}{suffix}")
                with open(file_path, "w") as f: f.write(data_str)
                print(f"Saved: {file_path}")
        except IOError as e: print(f"ERROR saving report files to {folderPath}: {e}")
        except Exception as e: print(f"ERROR during report saving: {e}")

        print("Sending shutdown signal to Monitor GUI...")
        if data_queue: data_queue.put("SHUTDOWN")
        print("Closing TraCI connection...")
        try: traci.close(); print("TraCI closed.")
        except traci.TraCIException as e: print(f"Warning: TraCI exception during close: {e}")
        except Exception as e: print(f"Warning: Error closing TraCI: {e}")

        print("Waiting briefly for GUI thread...")
        if monitor_thread and monitor_thread.is_alive():
             monitor_thread.join(timeout=2.0)
             if monitor_thread.is_alive(): print("Warning: Monitor GUI thread did not exit cleanly.")
        print("--- Starter.run_simulation finished ---")

start = run_simulation

if __name__ == "__main__":
    mapName_main = "Nantes"
    mode_main = "Mode111"
    # Example direct execution with a specific end time
    # run_simulation(mapName_main, mode_main, simulation_end_seconds=500)
    run_simulation(mapName_main, mode_main) # Default max_steps
    print("Direct execution of Starter.py complete.")

# --- END OF FILE Starter.py ---