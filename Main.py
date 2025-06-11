"""LS2N Simulator GUI for Traffic Simulation Management"""
# --- Import Required Libraries ---
import json
import tkinter
import tkinter.scrolledtext as scrolledtext
from tkinter import Tk, Frame, Label, BOTH, X, W, BOTTOM, END, NORMAL, DISABLED, StringVar, BooleanVar
from tkinter import ttk, messagebox
import os
import threading
import traceback
import Starter # This will now have the modified run_simulation
import Creator

# --- Define Config File Path ---
CONFIG_FILE = "gui_config.json"
# --- Define a file to store map-specific launch parameters ---
LAUNCH_PARAMS_FILENAME = "launch_params.json"


def save_settings():
    """Saves current GUI settings to a JSON file."""
    settings = {
        "create_map": CHX_Create.get(),
        "launch_map": CHX_Launch.get(),
        "truck_count": entry_truck_count.get(),
        "vehicle_type": CHX_VehType.get(),
        "infra_only": var_infra_only.get(),
        "launch_mode": var_launch_mode.get(),
        "sim_end_time_infra": var_sim_end_time_infra.get()
    }
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=4)
        log_message(f"Settings saved to {CONFIG_FILE}")
    except IOError as e:
        log_message(f"ERROR saving settings to {CONFIG_FILE}: {e}")


def load_settings():
    """Loads GUI settings from JSON file if it exists."""
    if not os.path.exists(CONFIG_FILE):
        print(f"{CONFIG_FILE} not found. Using default settings.")
        var_sim_end_time_infra.set("3600")
        toggle_infra_only()
        return

    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            settings = json.load(f)

        saved_create_map = settings.get("create_map", "")
        if saved_create_map in map_list: CHX_Create.set(saved_create_map)
        elif map_list and map_list[0] != "No Maps Found": CHX_Create.current(0)

        saved_launch_map = settings.get("launch_map", "")
        if saved_launch_map in map_list: CHX_Launch.set(saved_launch_map)
        elif map_list and map_list[0] != "No Maps Found": CHX_Launch.current(0)

        saved_truck_count = settings.get("truck_count", "10")
        try:
            count = int(saved_truck_count)
            entry_truck_count.delete(0, END)
            if count >= 0: entry_truck_count.insert(0, str(count))
            else: entry_truck_count.insert(0, "10")
        except ValueError:
            entry_truck_count.delete(0, END)
            entry_truck_count.insert(0, "10")

        saved_vehicle_type = settings.get("vehicle_type", "MissionVehicle")
        if saved_vehicle_type in CHX_VehType['values']: CHX_VehType.set(saved_vehicle_type)
        else: CHX_VehType.current(1)

        saved_infra_only = settings.get("infra_only", False)
        var_infra_only.set(bool(saved_infra_only))

        saved_launch_mode = settings.get("launch_mode", "Mode111")
        var_launch_mode.set(saved_launch_mode)

        saved_sim_end_time_infra = settings.get("sim_end_time_infra", "3600")
        var_sim_end_time_infra.set(saved_sim_end_time_infra)

        toggle_infra_only()
        print(f"Settings loaded from {CONFIG_FILE}")

    except (IOError, json.JSONDecodeError) as e:
        print(f"Error loading or parsing {CONFIG_FILE}: {e}. Using default settings.")
        var_sim_end_time_infra.set("3600")
        toggle_infra_only()


def on_closing():
    save_settings()
    window.destroy()


def get_available_maps():
    maps_dir = "cases/"
    available_maps = []
    if os.path.exists(maps_dir) and os.path.isdir(maps_dir):
        for item in os.listdir(maps_dir):
            item_path = os.path.join(maps_dir, item)
            if os.path.isdir(item_path):
                network_file_1 = os.path.join(item_path, "MyNetwork.net.xml")
                network_file_2 = os.path.join(item_path, "network.sumocfg")
                if os.path.exists(network_file_1) or os.path.exists(network_file_2):
                    available_maps.append(item)
    if not available_maps:
        messagebox.showerror("Error", "No map directories found in 'cases/' folder or they lack necessary files (e.g., MyNetwork.net.xml or network.sumocfg).")
        return ["No Maps Found"]
    return sorted(available_maps)


def style_widgets():
    try:
        window.tk.call("source", "Azure-ttk-theme-main/azure.tcl")
        window.tk.call("set_theme", "light")
    except tkinter.TclError: log_message("Azure TTK theme not found. Using default styles.")
    style = ttk.Style()
    style.configure("Card.TLabelframe", background="#ffffff", borderwidth=1, relief="solid")
    style.configure("Card.TLabelframe.Label", font=('Segoe UI', 11, 'bold'), background="#ffffff", foreground="#2c3e50")
    style.configure("TFrame", background="#ffffff")
    style.configure("TLabel", background="#ffffff", foreground="#2c3e50", font=('Segoe UI', 10))
    # ... (rest of styling as before) ...
    style.configure("TEntry", font=('Segoe UI', 10))
    style.configure("TCombobox", font=('Segoe UI', 10))
    style.configure("TButton", font=('Segoe UI', 10, 'bold'), padding=8)
    style.configure("TProgressbar", background="#e0e0e0", troughcolor="#ffffff")
    style.map("TButton", background=[('active', '#e0e0e0'), ('!active', '#f2f2f2')], foreground=[('pressed', '#2c3e50')])
    style.map("TButton", state=[('disabled', '!disabled')], background=[('disabled', '#d3d3d3')], foreground=[('disabled', '#a1a1a1')])


def create_instance():
    selected_map = CHX_Create.get()
    map_name = selected_map
    if map_name == "No Maps Found" or not selected_map:
        messagebox.showwarning("Missing selection", "Please select a valid map.")
        return

    vehicle_type = CHX_VehType.get()
    if not vehicle_type:
        messagebox.showwarning("Missing selection", "Please select a vehicle type.")
        return

    infra_only_checked = var_infra_only.get()
    sim_end_time_for_infra_val = None # Will hold the integer value

    if infra_only_checked:
        truck_count = 0
        try:
            sim_end_time_str = var_sim_end_time_infra.get().strip()
            if not sim_end_time_str: raise ValueError("Simulation End Time cannot be empty.")
            sim_end_time_for_infra_val = int(sim_end_time_str)
            if sim_end_time_for_infra_val <= 0: raise ValueError("Simulation End Time must be a positive integer.")
            log_message(f"Preparing infra setup for '{map_name}' (Sim End: {sim_end_time_for_infra_val}s).")
        except ValueError as e:
            messagebox.showerror("Invalid Input", f"Please enter a valid positive integer for Simulation End Time.\nError: {e}")
            return
    else:
        try:
            truck_count = int(entry_truck_count.get())
            if truck_count < 0: raise ValueError("Negative count")
            log_message(f"Creating instance for '{map_name}' with {truck_count} {vehicle_type}(s)...")
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter a valid non-negative number of trucks.")
            return

    progress_bar.pack(pady=(10, 0), fill=X, padx=5)
    progress_bar.start(10)
    btn_create.config(state=DISABLED) # ... (disable other relevant GUI elements)
    CHX_Create.config(state=DISABLED)
    CHX_VehType.config(state=DISABLED)
    chk_infra_only.config(state=DISABLED)
    # The states of entry_truck_count and entry_sim_end_time_infra are handled by toggle_infra_only
    # and will be restored correctly by it in _check_creator_thread

    # --- MODIFIED HERE: Pass sim_end_time_for_infra_val to the thread ---
    creator_thread = threading.Thread(
        target=_run_creator_thread,
        args=(map_name, truck_count, vehicle_type, infra_only_checked, sim_end_time_for_infra_val), # Added new args
        daemon=True
    )
    window.creator_result = {"success": False, "message": "", "error": None}
    creator_thread.start()
    window.after(100, _check_creator_thread, creator_thread, map_name, truck_count)


# --- MODIFIED HERE: _run_creator_thread now handles saving launch_params.json ---
def _run_creator_thread(map_name, truck_count, vehicle_type, is_infra_setup, sim_end_time_if_infra):
    """Worker function to run Creator.create and save launch params if infra_only."""
    try:
        Creator.create(map_name, truck_count, vehicle_type) # This part remains the same

        # --- Save launch parameters if it was an infra setup ---
        map_case_path = os.path.join("cases", map_name)
        launch_params_file = os.path.join(map_case_path, LAUNCH_PARAMS_FILENAME)

        if is_infra_setup:
            params_to_save = {
                "is_infra_only": True,
                "sim_end_time": sim_end_time_if_infra
            }
            try:
                with open(launch_params_file, 'w', encoding='utf-8') as f:
                    json.dump(params_to_save, f, indent=4)
                log_message(f"Saved infra launch params for {map_name} to {launch_params_file}")
                success_message = f"Infrastructure setup for {map_name} (Sim End: {sim_end_time_if_infra}s). Creator.create called with 0 trucks."
            except IOError as e:
                log_message(f"ERROR saving launch params for {map_name}: {e}")
                # Decide if this is a critical failure for the whole "Create" operation
                success_message = f"Infra setup for {map_name} done, BUT FAILED to save launch params: {e}"
                # window.creator_result["success"] could be set to False here if critical
        else:
            success_message = f"Creator.create: {truck_count} trucks created on {map_name}"
            # If not infra_only, we might want to remove any old launch_params.json
            if os.path.exists(launch_params_file):
                try:
                    os.remove(launch_params_file)
                    log_message(f"Removed old launch_params.json for {map_name}.")
                except OSError as e:
                    log_message(f"Warning: Could not remove old launch_params.json for {map_name}: {e}")


        window.creator_result["success"] = True # Assuming Creator.create itself didn't fail
        window.creator_result["message"] = success_message

    except Exception as e: # Catch errors from Creator.create
        error_msg = f"Creator.create error for {map_name}: {e}"
        print(error_msg)
        traceback.print_exc()
        window.creator_result["success"] = False
        window.creator_result["message"] = f"Failed during Creator.create for {map_name}."
        window.creator_result["error"] = e


def _check_creator_thread(thread, map_name, truck_count):
    if thread.is_alive():
        window.after(100, _check_creator_thread, thread, map_name, truck_count)
    else:
        progress_bar.stop()
        progress_bar.pack_forget()
        btn_create.config(state=NORMAL)
        CHX_Create.config(state=NORMAL)
        chk_infra_only.config(state=NORMAL)
        toggle_infra_only() # Restores states of truck_count and sim_end_time_infra entries
        CHX_VehType.config(state=NORMAL)

        if window.creator_result["success"]:
            log_message(f"SUCCESS: {window.creator_result['message']}")
            messagebox.showinfo("Success", window.creator_result["message"])
        else:
            error_details = f"\nDetails: {type(window.creator_result.get('error')).__name__}: {window.creator_result.get('error')}" if window.creator_result.get('error') else ""
            log_message(f"ERROR: {window.creator_result['message']}{error_details}")
            messagebox.showerror("Error", window.creator_result["message"] + error_details)
        log_message("-" * 20)


# --- MODIFIED HERE: launch_instance now checks for launch_params.json ---
def launch_instance():
    selected_map = CHX_Launch.get()
    map_name = selected_map
    if map_name == "No Maps Found" or not selected_map:
        log_message("Please select a valid map in the 'Launch Simulation' section first.")
        messagebox.showwarning("Missing selection", "Please select a valid map.")
        return

    launch_mode = var_launch_mode.get().strip()
    if not launch_mode:
        log_message("Launch Mode cannot be empty.")
        messagebox.showwarning("Missing Input", "Please enter a Launch Mode.")
        return

    # --- Check for map-specific launch parameters ---
    sim_end_time_for_starter = None # Default is None, Starter will use its own default
    map_case_path = os.path.join("cases", map_name)
    launch_params_file = os.path.join(map_case_path, LAUNCH_PARAMS_FILENAME)

    if os.path.exists(launch_params_file):
        try:
            with open(launch_params_file, 'r', encoding='utf-8') as f:
                params = json.load(f)
            if params.get("is_infra_only") and "sim_end_time" in params:
                sim_end_time_for_starter = int(params["sim_end_time"])
                log_message(f"Launching {map_name} as infra-only with sim_end_time: {sim_end_time_for_starter}s (from {LAUNCH_PARAMS_FILENAME})")
            else:
                log_message(f"Found {LAUNCH_PARAMS_FILENAME} for {map_name}, but not an infra_only setup or sim_end_time missing.")
        except (IOError, json.JSONDecodeError, ValueError) as e:
            log_message(f"Warning: Could not read or parse {launch_params_file} for {map_name}: {e}. Using default simulation duration.")
        except Exception as e: # General catch
            log_message(f"Unexpected error reading {launch_params_file} for {map_name}: {e}. Using default simulation duration.")


    log_message(f"Initiating simulation process for {map_name} (Mode: {launch_mode})...")
    btn_launch.config(state=DISABLED)

    # --- Pass sim_end_time_for_starter to the thread ---
    starter_thread = threading.Thread(
        target=_run_starter_thread,
        args=(map_name, launch_mode, sim_end_time_for_starter), # Added sim_end_time_for_starter
        daemon=True
    )
    starter_thread.start()
    log_message("Simulation & Monitor process started in background.")
    # ... (rest of message)
    messagebox.showinfo("Process Started", f"Simulation process for '{map_name}' initiated.\nA separate monitor window should appear shortly. The launch button will re-enable on completion/error.")


# --- MODIFIED HERE: _run_starter_thread now accepts sim_end_time ---
def _run_starter_thread(map_name, launch_mode, sim_end_time=None):
    """Worker function to run Starter.start in a thread, possibly with a custom end time."""
    try:
        # Pass the sim_end_time to Starter.run_simulation
        Starter.run_simulation(map_name, launch_mode, simulation_end_seconds=sim_end_time)
        print(f"Starter thread for {map_name} finished.")
        # ... (logging as before) ...
        window.after(0, lambda: log_message(f"Simulation process for {map_name} (Mode: {launch_mode}) completed."))
    except Exception as e:
        error_msg = f"ERROR in Starter thread for {map_name} (Mode: {launch_mode}): {e}"
        print(error_msg)
        traceback.print_exc()
        # ... (logging as before) ...
        window.after(0, lambda: log_message(error_msg))
    finally:
        window.after(0, lambda: btn_launch.config(state=NORMAL))


# --- GUI Setup (largely unchanged, ensure var_sim_end_time_infra is defined before load_settings) ---
window = Tk()
window.title("🚛 LS2N Simulator")
window.geometry("800x600")
window.configure(bg="#ffffff")

style_widgets() # Call this before creating ttk widgets if it sets global styles
map_list = get_available_maps() # Get maps before creating Comboboxes

main_frame = Frame(window, bg="#ffffff")
main_frame.pack(pady=15, padx=10, fill=BOTH, expand=True)
main_frame.columnconfigure(0, weight=1)
main_frame.columnconfigure(1, weight=1)
main_frame.rowconfigure(1, weight=1)

title = Label(main_frame, text="LS2N Traffic Simulator", font=("Segoe UI", 22, "bold"), bg="#ffffff", fg="#2c3e50")
title.grid(row=0, column=0, columnspan=2, pady=10, sticky="ew")

create_frame = ttk.LabelFrame(main_frame, text="🛠 Create Instance", style="Card.TLabelframe", padding=20)
create_frame.grid(row=1, column=0, padx=30, pady=10, ipadx=5, ipady=5, sticky='nsew')

ttk.Label(create_frame, text="Map Selection:").pack(anchor=W, padx=5)
CHX_Create = ttk.Combobox(create_frame, values=map_list, width=28, state="readonly")
if map_list and map_list[0] != "No Maps Found": CHX_Create.current(0)
CHX_Create.pack(pady=5, fill=X, padx=5)

ttk.Label(create_frame, text="Number of Trucks:").pack(anchor=W, pady=(10, 0), padx=5)
entry_truck_count = ttk.Entry(create_frame, width=10)
# entry_truck_count.insert(0, "10") # Value set by load_settings or toggle_infra_only
entry_truck_count.pack(pady=5, anchor=W, padx=5)

ttk.Label(create_frame, text="Vehicle Type:").pack(anchor=W, pady=(10, 0), padx=5)
CHX_VehType = ttk.Combobox(create_frame, values=["Truck", "MissionVehicle"], width=28, state="readonly")
# CHX_VehType.current(1) # Value set by load_settings
CHX_VehType.pack(pady=5, fill=X, padx=5)

var_sim_end_time_infra = StringVar() # Value set by load_settings

def toggle_infra_only():
    if var_infra_only.get():
        entry_truck_count.delete(0, END)
        entry_truck_count.insert(0, "0")
        entry_truck_count.config(state=DISABLED)
        lbl_sim_end_time_infra.pack(anchor=W, pady=(10,0), padx=5)
        entry_sim_end_time_infra.pack(pady=5, anchor=W, padx=5)
        entry_sim_end_time_infra.config(state=NORMAL)
    else:
        entry_truck_count.config(state=NORMAL)
        entry_truck_count.delete(0, END)
        entry_truck_count.insert(0, "10") # Default for non-infra
        lbl_sim_end_time_infra.pack_forget()
        entry_sim_end_time_infra.pack_forget()
        entry_sim_end_time_infra.config(state=DISABLED)

var_infra_only = BooleanVar() # Value set by load_settings
chk_infra_only = ttk.Checkbutton(create_frame, text="Run infrastructure only (no trucks)",
                                 variable=var_infra_only, command=toggle_infra_only)
chk_infra_only.pack(anchor=W, pady=(10, 0), padx=5)

lbl_sim_end_time_infra = ttk.Label(create_frame, text="Simulation End Time (Infra only, seconds):")
entry_sim_end_time_infra = ttk.Entry(create_frame, textvariable=var_sim_end_time_infra, width=10)

btn_create = ttk.Button(create_frame, text="🚀 Create", command=create_instance)
btn_create.pack(pady=15)
progress_bar = ttk.Progressbar(create_frame, mode='indeterminate', length=200)

# --- Launch Section ---
launch_frame = ttk.LabelFrame(main_frame, text="🚦 Launch Simulation", style="Card.TLabelframe", padding=20)
launch_frame.grid(row=1, column=1, padx=30, pady=10, ipadx=5, ipady=5, sticky='nsew')
launch_frame.pack_propagate(False)

ttk.Label(launch_frame, text="Map Selection:").pack(anchor=W, padx=5)
CHX_Launch = ttk.Combobox(launch_frame, values=map_list, width=28, state="readonly")
if map_list and map_list[0] != "No Maps Found": CHX_Launch.current(0) # Default if available
CHX_Launch.pack(pady=5, fill=X, padx=5)

ttk.Label(launch_frame, text="Launch Mode:").pack(anchor=W, pady=(10, 0), padx=5)
var_launch_mode = StringVar() # Value set by load_settings
entry_launch_mode = ttk.Entry(launch_frame, textvariable=var_launch_mode, width=30)
entry_launch_mode.pack(pady=5, fill=X, padx=5)

btn_launch = ttk.Button(launch_frame, text="🎯 Launch", command=launch_instance)
btn_launch.pack(pady=15)

# --- Log Area ---
log_frame = ttk.Frame(window, padding=(10, 5))
log_frame.pack(fill=X, expand=False, side=BOTTOM, padx=10, pady=(0, 10))
log_label = ttk.Label(log_frame, text="Log Output:", font=("Segoe UI", 10, "bold"))
log_label.pack(anchor=W)
log_area = scrolledtext.ScrolledText(log_frame, height=8, wrap=tkinter.WORD, font=("Consolas", 9), state=DISABLED, bg="#f0f0f0", fg="#1a1a1a")
log_area.pack(fill=BOTH, expand=True)

def log_message(message):
    log_area.config(state=NORMAL)
    log_area.insert(END, message + "\n")
    log_area.config(state=DISABLED)
    log_area.see(END)

# --- Load settings and initialize UI state ---
load_settings() # This must be called AFTER all UI elements it might affect are defined.

log_message("LS2N Simulator Ready.")
log_message("Please select map and options, then Create or Launch.")
window.protocol("WM_DELETE_WINDOW", on_closing)
window.mainloop()
# --- END OF FILE Main.py ---