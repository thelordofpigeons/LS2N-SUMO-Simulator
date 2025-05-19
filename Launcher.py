import os
import sys
import random  # For random.randint, random.choice
import xml.etree.ElementTree as ET

import traci
import traci.constants as tc  # Used for stop states
import myPyLib


class StateListener(traci.StepListener):
    """
    Listens to TraCI steps to retrieve and process simulation state.
    """

    def __init__(self, vehicle_ids, routes_path="", mission_path="", emergency_break_threshold=-4.0):
        """
        Initializes the StateListener.
        Args:
            vehicle_ids (list): List of vehicle IDs to monitor.
            routes_path (str): Path to the routes XML file.
            mission_path (str): Path to the missions XML file.
            emergency_break_threshold (float): Threshold for detecting emergency breaks.
        """
        super().__init__()
        print("__init__ StateListener!")
        self.vehicle_ids = vehicle_ids
        self.emergency_break_threshold = emergency_break_threshold
        self.vehicles = {}
        self.emergency_break = False
        self.collision = False

        print(f"StateListener received routesPath={routes_path}")
        print(f"StateListener received missionPath={mission_path}")

        self.routes_root = None
        self.mission_root = None

        if routes_path and os.path.exists(routes_path):
            try:
                routes_tree = ET.parse(routes_path)
                self.routes_root = routes_tree.getroot()
            except ET.ParseError as e:
                print(
                    f"StateListener Error: Could not parse routes file '{routes_path}': {e}")
        else:
            print(
                f"StateListener Warning: Routes file not found or path empty: '{routes_path}'")

        if mission_path and os.path.exists(mission_path):
            try:
                mission_tree = ET.parse(mission_path)
                self.mission_root = mission_tree.getroot()
            except ET.ParseError as e:
                print(
                    f"StateListener Error: Could not parse mission file '{mission_path}': {e}")
        else:
            print(
                f"StateListener Warning: Mission file not found or path empty: '{mission_path}'")

    def step(self, t=0):
        """
        Called at each simulation step.
        """
        self.retrieve_state()
        self.check_collision()
        return True

    def retrieve_state(self):
        """
        Receives and stores data for subscribed vehicles.
        """
        for vehicle_id in list(self.vehicle_ids):
            if vehicle_id in traci.vehicle.getIDList():
                try:
                    self.vehicles[vehicle_id] = traci.vehicle.getSubscriptionResults(
                        vehicle_id)
                except traci.TraCIException as e:
                    print(
                        f"StateListener: TraCI error for {vehicle_id} in retrieve_state: {e}")
                    if vehicle_id in self.vehicles:
                        del self.vehicles[vehicle_id]
                    if vehicle_id in self.vehicle_ids:
                        self.vehicle_ids.remove(vehicle_id)
            else:
                if vehicle_id in self.vehicles:
                    del self.vehicles[vehicle_id]
                if vehicle_id in self.vehicle_ids:
                    self.vehicle_ids.remove(vehicle_id)

    def print_state(self):
        """
        Prints data for monitored vehicles (example).
        """
        for vehicle_id in self.vehicle_ids:
            # Prefix with _ if not used further
            _vehicle_data = self.vehicles.get(vehicle_id)

    def check_collision(self):
        """
        If SUMO detects a collision (e.g. teleports a vehicle) set the collision flag.
        """
        if traci.simulation.getStartingTeleportNumber() > 0:
            print("\nCollision occurred (teleport detected)...")
            self.collision = True

    def check_emergency_break(self):
        """
        If any vehicle decelerates more than the emergencyBreakThreshold set the emergencyBreak flag.
        """
        for vehicle_id in self.vehicle_ids:
            vehicle_data = self.vehicles.get(vehicle_id)
            if vehicle_data:
                acceleration = vehicle_data.get(tc.VAR_ACCELERATION)
                if acceleration is not None and (acceleration * 10 < self.emergency_break_threshold):
                    print(f"\nEmergency braking required for {vehicle_id}...")
                    self.emergency_break = True


def init_vehicles(vehicle_listener_instance):
    """
    Example function to initialize or print info about vehicles known to a listener.
    """
    print("Initializing vehicles (example)...")
    if not hasattr(vehicle_listener_instance, 'vehicles'):
        print("Listener instance has no 'vehicles' attribute.")
        return

    for vehicle_id, vehicle_data in vehicle_listener_instance.vehicles.items():
        if vehicle_data is not None:
            try:
                vehicle_type = traci.vehicle.getTypeID(vehicle_id)
                print(f"ID: {vehicle_id}, Type: {vehicle_type}")
            except traci.TraCIException as e:
                print(f"Error getting type for {vehicle_id}: {e}")


def get_random_in_out_edges(map_metadata):
    """
    Selects random input and output edges based on provided metadata.
    Args:
        map_metadata: An object or dict expected to have 'northIn', 'southOut', etc.
    Returns:
        list: [input_edge, output_edge] or None if metadata is missing.
    """
    if not all(hasattr(map_metadata, attr) for attr in ['northIn', 'southOut', 'southIn', 'northOut']):
        print("Error: map_metadata missing required edge list attributes.")
        return None

    if random.randint(0, 1):
        input_edge = random.choice(map_metadata.northIn)
        output_edge = random.choice(map_metadata.southOut)
    else:
        input_edge = random.choice(map_metadata.southIn)
        output_edge = random.choice(map_metadata.northOut)
    return [input_edge, output_edge]


def start_traci_and_listener(map_name, _mode_name):
    """
    Starts TraCI, parses route/mission files, and adds a StateListener.
    """
    routes_path_local = f"cases/{map_name}/MyRoutes.rou.xml"
    mission_path_local = f"cases/{map_name}/Missions.mis.xml"

    print("Starting the TraCI server...")
    sumo_binary = "C:/Program Files (x86)/Eclipse/Sumo/bin/sumo-gui"
    sumo_cfg_file = f"cases/{map_name}/Network.sumocfg"
    if not os.path.exists(sumo_cfg_file):
        sumo_cfg_file = f"cases/{map_name}/network.sumocfg"
        if not os.path.exists(sumo_cfg_file):
            print(
                f"ERROR: SUMO config file not found for map {map_name} at {sumo_cfg_file} (or Network.sumocfg)")
            sys.exit(1)

    sumo_cmd = [sumo_binary, "-c", sumo_cfg_file]
    traci.start(sumo_cmd)

    print("Subscribing to vehicle data (via StateListener)...")
    print("Constructing a StateListener...")
    state_listener = StateListener(
        ["0", "1"], routes_path=routes_path_local, mission_path=mission_path_local)
    traci.addStepListener(state_listener)


def assign_mission_action(veh_id, action_element):
    """
    Assigns a specific mission action to a vehicle.
    """
    new_target = action_element.get("target")
    action_type = action_element.get("type")
    target_edge = action_element.get("edge", new_target)

    if not new_target or not action_type:
        print(
            f"Error: Incomplete action for {veh_id}: Target='{new_target}', Type='{action_type}'")
        return

    print(
        f"Assigning Mission for {veh_id}: Type={action_type}, Target='{new_target}', Edge='{target_edge}'")

    try:
        if not target_edge:
            print(
                f"Error: No valid edge determined for action {action_type} for vehicle {veh_id}")
            return

        traci.vehicle.changeTarget(veh_id, target_edge)

        if action_type == "Load" or action_type == "Unload":
            print(
                f"  Action: {action_type} for {veh_id} at stop '{new_target}' on edge '{target_edge}'")
            # Assuming new_target is a defined stop ID (e.g., parkingArea, busStop, containerStop)
            # The exact stop command depends on the type of stop.
            # For container stops (if CS0 is the ID of a <containerStop>):
            # traci.vehicle.setContainerStop(veh_id, new_target_stop_id, duration=150) # e.g. new_target is "CS0"
            # For parking areas used as stops:
            traci.vehicle.setParkingAreaStop(veh_id, new_target, duration=150)
            # For bus stops:
            # traci.vehicle.setStop(veh_id, new_target_stop_id, duration=150, flags=tc.STOP_DEFAULT)

        elif action_type == "Park":
            print(f"  Action: Park for {veh_id} at parkingArea '{new_target}'")
            traci.vehicle.setParkingAreaStop(veh_id, new_target, duration=100)

        elif action_type == "Go":
            print(f"  Action: Go for {veh_id}, target edge '{target_edge}'")

    except traci.TraCIException as e:
        print(f"TraCI Error in assign_mission_action for {veh_id}: {e}")
    except IOError as e_io:  # More specific for file-related issues if any were here
        print(f"IOError in assign_mission_action for {veh_id}: {e_io}")
    except ValueError as e_val:  # More specific for value conversion issues
        print(f"ValueError in assign_mission_action for {veh_id}: {e_val}")
    # Keep a general Exception for truly unexpected issues, but try to be specific first
    except Exception as e_unexp:  # W0718 here is acceptable if truly unexpected
        print(
            f"Unexpected error in assign_mission_action for {veh_id}: {e_unexp}")


def get_pending_action(veh_id, mission_tree_root):
    """
    Gets the first pending action (status != '3') for a vehicle from the mission XML root.
    """
    if mission_tree_root is None:
        return None
    mission_element = mission_tree_root.find(f".//mission[@id='{veh_id}']")
    if mission_element is not None:
        for action_element in mission_element.findall("action"):
            if action_element.get("status") != "3":
                return action_element
    return None


def get_current_target_for_inprogress_action(veh_id, mission_tree_root):
    """
    Gets the target of the current in-progress action (status == '1').
    """
    if mission_tree_root is None:
        return None
    mission_element = mission_tree_root.find(f".//mission[@id='{veh_id}']")
    if mission_element is not None:
        for action_element in mission_element.findall("action"):
            if action_element.get("status") == "1":
                return action_element.get("target")
    return None


def launch_simulation(map_name, mode_name):
    """
    Main simulation launch function.
    """
    if 'SUMO_HOME' not in os.environ:
        sys.exit("ERROR: please declare environment variable 'SUMO_HOME'")
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    if tools not in sys.path:
        sys.path.append(tools)

    print(
        f"--- Launching simulation for map: {map_name}, mode: {mode_name} ---")

    sumo_binary = "C:/Program Files (x86)/Eclipse/Sumo/bin/sumo-gui"
    sumo_cfg_file = f"cases/{map_name}/network.sumocfg"
    if not os.path.exists(sumo_cfg_file):
        sumo_cfg_file = f"cases/{map_name}/Network.sumocfg"
        if not os.path.exists(sumo_cfg_file):
            print(f"ERROR: SUMO config file not found for map {map_name}")
            sys.exit(1)

    sumo_config_args = ["-c", sumo_cfg_file, "-S"]
    sumo_cmd_list = [sumo_binary] + sumo_config_args

    twt_trucks = 0
    co_trucks = 0
    co2_trucks = 0
    stats_data_list = []

    mission_file_path = f"cases/{map_name}/missions.mis.xml"
    mission_tree_root = None
    if os.path.exists(mission_file_path):
        try:
            mission_tree = ET.parse(mission_file_path)
            mission_tree_root = mission_tree.getroot()
        except ET.ParseError as e:
            print(f"Error parsing mission file '{mission_file_path}': {e}")
    else:
        print(f"Warning: Mission file not found: {mission_file_path}")

    traci.start(sumo_cmd_list)
    step = 0
    max_steps = 3000

    while step < max_steps:
        traci.simulationStep()
        current_active_vehicles = traci.vehicle.getIDList()

        for veh_id in current_active_vehicles:
            if "trk" in veh_id:
                vehicle_stats = myPyLib.getData(veh_id)
                twt_trucks += vehicle_stats[1]
                co2_trucks += vehicle_stats[2]
                co_trucks += vehicle_stats[3]
                stats_data_list.append(vehicle_stats)

                if mission_tree_root:
                    action = get_pending_action(veh_id, mission_tree_root)
                    if action is not None:
                        action_status = action.get("status")
                        action_type = action.get("type")
                        action_target = action.get("target")

                        if action_status == '0':
                            assign_mission_action(veh_id, action)
                            action.set('status', '1')
                            print(
                                f"{veh_id}: New action '{action_type}' Target='{action_target}'. "
                                f"Status -> '1'."
                            )
                        elif action_status == '1':
                            try:
                                stop_state = traci.vehicle.getStopState(veh_id)
                                # is_stopped_for_action = False # W0612: Unused if not used to change flow

                                # IMPORTANT: Verify these stop state constants for your SUMO version!
                                # tc.STOP_CONTAINER_TRIGGERED is typically bit 3 (value 8)
                                # tc.STOP_BUS_STOPPING is typically bit 2 (value 4)
                                # tc.STOP_WAITING_FOR_PERSON is typically bit 4 (value 16)
                                # Original '33' was (32 | 1) - likely incorrect for loading.
                                # Let's assume loading/unloading happens at container stops or bus stops.
                                vehicle_stopped_for_loading = (
                                    (action_type == 'Load' or action_type == 'Unload') and
                                    (stop_state & tc.STOP_CONTAINER_STOPPING or  # Value 8
                                     stop_state & tc.STOP_BUS_STOPPING or       # Value 4
                                     stop_state & tc.STOP_WAITING_FOR_PERSON)   # Value 16
                                )
                                # Or if the original '33' was a custom/observed state for your setup:
                                # vehicle_stopped_for_loading = (
                                # (action_type == 'Load' or action_type == 'Unload') and stop_state == 33
                                # )

                                if vehicle_stopped_for_loading:
                                    action.set('status', '3')
                                    print(
                                        f"{veh_id}: {action_type} completed. Status -> '3'.")
                                # Value 1
                                elif action_type == 'Park' and (stop_state & tc.STOP_PARKING):
                                    action.set('status', '2')
                                    print(
                                        f"{veh_id}: Parked. Status -> '2'. Target: {action_target}")
                                elif action_type == 'Go':
                                    current_road = traci.vehicle.getRoadID(
                                        veh_id)
                                    if current_road == action_target or not traci.vehicle.getRoute(veh_id):
                                        # Changed to '3' for "Go" completion
                                        action.set('status', '3')
                                        print(
                                            f"{veh_id}: Go action completed. Status -> '3'.")
                            except traci.TraCIException as e:
                                print(
                                    f"TraCI error checking stop state for {veh_id}: {e}")
                        # elif action_status == '2':
                            # If status is '2' (e.g., Parked), what makes it move to '3'?
                            # Example: if no longer stopped for parking.
                            # if action_type == 'Park' and not (traci.vehicle.getStopState(veh_id) & tc.STOP_PARKING):
                            #    action.set('status', '3')
                            #    print(f"{veh_id}: Finished Parking. Status -> '3'.")
                            # This part (W0107: unnecessary-pass) had no logic.
                            # If actions in status '2' need conditions to move to '3', add them here.

        if step > 0 and step % 100 == 0:
            print(f"\n--- Simulation Report at Step {step} ---")
            # print(f"  Total Truck Waiting Time (TWTtrk): {twt_trucks}")
            # print(f"  Total Truck CO2 Emissions (CO2trk): {co2_trucks}")
            # print(f"  Total Truck CO Emissions (COtrk): {co_trucks}")

        step += 1
        if not current_active_vehicles and step > 50:
            print("No more vehicles in simulation. Ending early.")
            break

    if mission_tree_root is not None:
        try:
            final_mission_tree_str = ET.tostring(
                mission_tree_root, encoding='unicode')
            with open(f"cases/{map_name}/missions_final_state.mis.xml", "w", encoding="utf-8") as f_out:
                f_out.write(final_mission_tree_str)
            print(
                f"Saved final mission states to cases/{map_name}/missions_final_state.mis.xml")
        except IOError as e_save_io:  # More specific
            print(f"IOError saving final mission states: {e_save_io}")
        except ET.ParseError as e_save_parse:  # If tostring created invalid XML somehow
            print(
                f"ParseError related to saving final mission states: {e_save_parse}")

    myPyLib.save(stats_data_list)
    print("\nSimulation loop finished.")
    print("Stopping the TraCI server...")
    traci.close()


if __name__ == "__main__":
    sim_map_name = "Nantes"
    sim_mode_name = "NOCITS"

    try:
        launch_simulation(sim_map_name, sim_mode_name)
    except traci.TraCIException as e_traci_main:  # More specific for TraCI issues
        print(
            f"A TraCI error occurred during the simulation launch: {e_traci_main}")
        import traceback
        traceback.print_exc()
    except RuntimeError as e_rt_main:  # Catch runtime errors that might not be TraCI specific
        print(f"A runtime error occurred: {e_rt_main}")
        import traceback
        traceback.print_exc()
    # Keep general Exception for truly unexpected issues
    except Exception as e_main:  # W0718 here is acceptable as a last resort
        print(
            f"An unexpected error occurred during the simulation launch: {e_main}")
        import traceback
        traceback.print_exc()
    finally:
        # Check if TraCI connection exists before trying to close it
        # A simple way is to see if a basic command works or if it's connected.
        # However, traci.close() itself handles cases where it's not connected.
        # The 'isEmbedded' was one way, but if not available, direct close is fine.
        try:
            if traci.getConnection():  # Check if a connection object exists
                print("Ensuring TraCI is closed.")
                # wait=False can prevent hanging if SUMO already exited
                traci.close(wait=False)
        except (NameError, AttributeError):  # traci might not be imported or connection not made
            pass  # Nothing to close
        except traci.TraCIException:  # If traci.close() itself fails
            print("TraCIException during final close attempt.")
