# --- START OF FILE Main.py ---
import json # Needed for next commit, adding now is fine
import tkinter.scrolledtext as scrolledtext # Needed later for logging
from tkinter import *
from tkinter import ttk, messagebox
import Starter, Creator
import os
import threading # Added for Progress Bar

# --- Define Config File Path ---
CONFIG_FILE = "gui_config.json"

# --- Add Save Settings Function ---
def save_settings():
    """Saves current GUI settings to a JSON file."""
    settings = {
        "create_map": CHX_Create.get(),
        "launch_map": CHX_Launch.get(),
        "truck_count": entry_truck_count.get(),
        "vehicle_type": CHX_VehType.get(),
        "infra_only": var_infra_only.get(),
        "launch_mode": var_launch_mode.get()
    }
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(settings, f, indent=4)
        print(f"Settings saved to {CONFIG_FILE}") # Optional: confirmation
    except IOError as e:
        print(f"Error saving settings to {CONFIG_FILE}: {e}")
    except Exception as e:
        print(f"An unexpected error occurred while saving settings: {e}")

# --- Add Load Settings Function ---
def load_settings():
    """Loads GUI settings from JSON file if it exists."""
    if not os.path.exists(CONFIG_FILE):
        print(f"{CONFIG_FILE} not found. Using default settings.") # Optional
        return # No config file, do nothing

    try:
        with open(CONFIG_FILE, 'r') as f:
            settings = json.load(f)

        # Load Create Map (check if still valid)
        saved_create_map = settings.get("create_map", "")
        if saved_create_map in map_list:
            CHX_Create.set(saved_create_map)
        elif map_list and map_list[0] != "No Maps Found": # Fallback to first valid map
             CHX_Create.current(0)

        # Load Launch Map (check if still valid)
        saved_launch_map = settings.get("launch_map", "")
        if saved_launch_map in map_list:
            CHX_Launch.set(saved_launch_map)
        elif map_list and map_list[0] != "No Maps Found": # Fallback to first valid map
            CHX_Launch.current(0)

        # Load Truck Count (validate)
        saved_truck_count = settings.get("truck_count", "10")
        try:
            # Validate before setting
            count = int(saved_truck_count)
            if count >= 0:
                entry_truck_count.delete(0, END)
                entry_truck_count.insert(0, str(count))
            else: # Handle negative count if loaded
                 entry_truck_count.delete(0, END)
                 entry_truck_count.insert(0, "10") # Reset to default
        except ValueError: # Handle non-integer if loaded
            entry_truck_count.delete(0, END)
            entry_truck_count.insert(0, "10") # Reset to default

        # Load Vehicle Type (check if still valid)
        saved_vehicle_type = settings.get("vehicle_type", "MissionVehicle")
        if saved_vehicle_type in CHX_VehType['values']:
             CHX_VehType.set(saved_vehicle_type)
        else: # Fallback to default if invalid
             CHX_VehType.current(1) # MissionVehicle

        # Load Infra Only state
        saved_infra_only = settings.get("infra_only", False) # Default to False
        var_infra_only.set(bool(saved_infra_only)) # Ensure it's a boolean

        # Load Launch Mode
        saved_launch_mode = settings.get("launch_mode", "Mode111") # Default mode
        var_launch_mode.set(saved_launch_mode)

        # --- IMPORTANT: Update UI state based on loaded infra_only ---
        toggle_infra_only()

        print(f"Settings loaded from {CONFIG_FILE}") # Optional

    except (IOError, json.JSONDecodeError) as e:
        print(f"Error loading or parsing {CONFIG_FILE}: {e}. Using default settings.")
    except Exception as e:
        print(f"An unexpected error occurred while loading settings: {e}. Using default settings.")


# --- Add function to handle window closing ---
def on_closing():
    """Called when the user tries to close the window."""
    save_settings() # Save settings first
    window.destroy() # Then close the window


# --- Function to get available maps ---
def get_available_maps():
    """Scans the 'cases/' directory for subdirectories (maps)."""
    maps_dir = "cases/"
    available_maps = []
    if os.path.exists(maps_dir) and os.path.isdir(maps_dir):
        for item in os.listdir(maps_dir):
            item_path = os.path.join(maps_dir, item)
            # Check if it's a directory and potentially contains expected files
            # (simple check for now, could be more robust)
            if os.path.isdir(item_path):
                 # Basic check if it looks like a map case (e.g., has a .net.xml file)
                 network_file = os.path.join(item_path, "MyNetwork.net.xml") # Or Network.sumocfg
                 if os.path.exists(network_file):
                    available_maps.append(item) # Use directory name as map name
    if not available_maps:
        messagebox.showerror("Error", "No map directories found in 'cases/' folder or they lack necessary files.")
        # Return a default or empty list to prevent errors down the line
        return ["No Maps Found"]
    return sorted(available_maps) # Sort alphabetically

def style_widgets():
    window.tk.call("source", "Azure-ttk-theme-main/azure.tcl")
    window.tk.call("set_theme", "light")

    style = ttk.Style()

    style.configure("Card.TLabelframe", background="#ffffff", borderwidth=1, relief="solid")
    style.configure("Card.TLabelframe.Label", font=('Segoe UI', 11, 'bold'), background="#ffffff", foreground="#2c3e50")

    style.configure("TFrame", background="#ffffff")
    style.configure("TLabel", background="#ffffff", foreground="#2c3e50", font=('Segoe UI', 10))
    style.configure("TEntry", font=('Segoe UI', 10))
    style.configure("TCombobox", font=('Segoe UI', 10))
    style.configure("TButton", font=('Segoe UI', 10, 'bold'), padding=8)
    style.configure("TProgressbar", background="#e0e0e0", troughcolor="#ffffff") # Style progress bar

    style.map("TButton",
              background=[('active', '#e0e0e0'), ('!active', '#f2f2f2')],
              foreground=[('pressed', '#2c3e50')])
    style.map("TButton",
              state=[('disabled', '!disabled')], # Add styling for disabled state if needed
              background=[('disabled', '#d3d3d3')],
              foreground=[('disabled', '#a1a1a1')])

def create_instance():
    selected_map = CHX_Create.get()
    # Adjust map name extraction if needed, assuming map name is the directory name now
    map_name = selected_map # Directly use the selected directory name

    if map_name == "No Maps Found" or not selected_map:
        messagebox.showwarning("Missing selection", "Please select a valid map.")
        return

    if var_infra_only.get():
        truck_count = 0
    else:
        try:
            truck_count = int(entry_truck_count.get())
            if truck_count < 0: raise ValueError("Negative count")
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter a valid non-negative number of trucks.")
            return

    vehicle_type = CHX_VehType.get()
    if not vehicle_type:
         messagebox.showwarning("Missing selection", "Please select a vehicle type.")
         return

    # --- Start Progress Bar Logic ---
    status_var.set(f"Creating instance for '{map_name}'...")
    progress_bar.pack(pady=(10, 0), fill=X, padx=5) # Show progress bar
    progress_bar.start(10) # Start indeterminate progress
    btn_create.config(state=DISABLED) # Disable button
    CHX_Create.config(state=DISABLED)
    entry_truck_count.config(state=DISABLED)
    CHX_VehType.config(state=DISABLED)
    chk_infra_only.config(state=DISABLED)

    # --- Run Creator.create in a separate thread ---
    creator_thread = threading.Thread(
        target=_run_creator_thread,
        args=(map_name, truck_count, vehicle_type),
        daemon=True # Allows main program to exit even if thread is running
    )
    # Store thread result/exception
    window.creator_result = {"success": False, "message": "", "error": None}
    creator_thread.start()

    # --- Check thread completion ---
    window.after(100, _check_creator_thread, creator_thread, map_name, truck_count)

def _run_creator_thread(map_name, truck_count, vehicle_type):
    """Worker function to run Creator.create."""
    try:
        Creator.create(map_name, truck_count, vehicle_type)
        window.creator_result["success"] = True
        window.creator_result["message"] = f"{truck_count} trucks created on {map_name}"
    except Exception as e:
        print(f"Error during Creator.create: {e}") # Log the full error
        window.creator_result["success"] = False
        window.creator_result["message"] = f"Failed to create instance for {map_name}."
        window.creator_result["error"] = e # Store exception

def _check_creator_thread(thread, map_name, truck_count):
    """Checks if the creator thread is finished and updates GUI."""
    if thread.is_alive():
        # Thread still running, check again later
        window.after(100, _check_creator_thread, thread, map_name, truck_count)
    else:
        # Thread finished
        progress_bar.stop()
        progress_bar.pack_forget() # Hide progress bar
        btn_create.config(state=NORMAL) # Re-enable button
        CHX_Create.config(state=NORMAL)
        # Re-enable truck count entry only if infra-only is not checked
        if not var_infra_only.get():
            entry_truck_count.config(state=NORMAL)
        CHX_VehType.config(state=NORMAL)
        chk_infra_only.config(state=NORMAL)


        if window.creator_result["success"]:
            messagebox.showinfo("Success", window.creator_result["message"])
            status_var.set("Instance created successfully.")
        else:
            # Show a more specific error if available
            error_details = f"\nDetails: {window.creator_result['error']}" if window.creator_result['error'] else ""
            messagebox.showerror("Error", window.creator_result["message"] + error_details)
            status_var.set("Instance creation failed.")

def launch_instance():
    selected_map = CHX_Launch.get()
    # Adjust map name extraction if needed
    map_name = selected_map

    if map_name == "No Maps Found" or not selected_map:
        messagebox.showwarning("Missing selection", "Please select a valid map.")
        return
    
     # --- START: Get and validate launch mode ---
    launch_mode = var_launch_mode.get().strip() # Get from StringVar and remove leading/trailing whitespace
    if not launch_mode:
        messagebox.showwarning("Missing Input", "Please enter a Launch Mode.")
        return
    # --- END: Get and validate launch mode ---

    messagebox.showinfo("Launching", f"Launching simulation on {map_name} with mode '{launch_mode}'")
    status_var.set(f"Launching simulation on {map_name} (Mode: {launch_mode})...")

    try:
        window.quit() # Quit GUI before blocking call
        Starter.start(map_name, launch_mode) # Pass the user-defined mode
    except Exception as e:
        print(f"Error during Starter.start for {map_name} (Mode: {launch_mode}): {e}")
        # Status update won't be visible as GUI is closed
        # status_var.set("Simulation launch failed.")


# --- GUI Setup ---
window = Tk()
window.title("🚛 LS2N Simulator")
window.geometry("800x550") # Increased height slightly for progress bar
window.configure(bg="#ffffff")

style_widgets()

# Get maps dynamically
map_list = get_available_maps()

# Main Frame
main_frame = Frame(window, bg="#ffffff")
main_frame.pack(pady=30, fill=BOTH, expand=True) # Allow frame to expand
main_frame.columnconfigure(0, weight=1) # Make columns expandable
main_frame.columnconfigure(1, weight=1)
main_frame.rowconfigure(1, weight=1)
# Header
title = Label(main_frame, text="LS2N Traffic Simulator", font=("Segoe UI", 22, "bold"),
              bg="#ffffff", fg="#2c3e50")
# Spanning across columns that can resize
title.grid(row=0, column=0, columnspan=2, pady=10, sticky="ew")

# Create Section (Card)
create_frame = ttk.LabelFrame(main_frame, text="🛠 Create Instance", style="Card.TLabelframe", padding=20)
# Use sticky='nsew' to make it fill the grid cell
create_frame.grid(row=1, column=0, padx=30, pady=10, ipadx=5, ipady=5, sticky='nsew')
# Allow content packing to align nicely
create_frame.pack_propagate(False) # Prevent children from shrinking the frame

ttk.Label(create_frame, text="Map Selection:").pack(anchor=W, padx=5)
CHX_Create = ttk.Combobox(create_frame, values=map_list, width=28, state="readonly")
if map_list and map_list[0] != "No Maps Found": CHX_Create.current(0) # Select first map if available
CHX_Create.pack(pady=5, fill=X, padx=5) # Fill available width



#Frame to choose the number of trucks
ttk.Label(create_frame, text="Number of Trucks:").pack(anchor=W, pady=(10, 0), padx=5)
entry_truck_count = ttk.Entry(create_frame, width=10)
entry_truck_count.insert(0, "10")
entry_truck_count.pack(pady=5, anchor=W, padx=5) # Anchor west

#Frame to choose the vehicle type
ttk.Label(create_frame, text="Vehicle Type:").pack(anchor=W, pady=(10, 0), padx=5)
CHX_VehType = ttk.Combobox(create_frame, values=["Truck", "MissionVehicle"], width=28, state="readonly")
CHX_VehType.current(1)  # Default to MissionVehicle
CHX_VehType.pack(pady=5, fill=X, padx=5)

# Infrastructure only checkbox
def toggle_infra_only():
    if var_infra_only.get():
        entry_truck_count.delete(0, END)
        entry_truck_count.insert(0, "0")
        entry_truck_count.config(state=DISABLED)
    else:
        # Only enable if the create button is also enabled (i.e., not during creation)
        if btn_create['state'] == NORMAL:
            entry_truck_count.config(state=NORMAL)
        entry_truck_count.delete(0, END)
        entry_truck_count.insert(0, "10")

var_infra_only = BooleanVar()
chk_infra_only = ttk.Checkbutton(
    create_frame,
    text="Run infrastructure only (no trucks)",
    variable=var_infra_only,
    command=toggle_infra_only
)
chk_infra_only.pack(anchor=W, pady=(10, 0), padx=5)

# --- Create Button and Progress Bar ---
btn_create = ttk.Button(create_frame, text="🚀 Create", command=create_instance)
btn_create.pack(pady=15)

progress_bar = ttk.Progressbar(create_frame, mode='indeterminate', length=200)
# Don't pack progress_bar here initially, pack it when create_instance runs

# Launch Section (Card)
launch_frame = ttk.LabelFrame(main_frame, text="🚦 Launch Simulation", style="Card.TLabelframe", padding=20)
launch_frame.grid(row=1, column=1, padx=30, pady=10, ipadx=5, ipady=5, sticky='nsew')
launch_frame.pack_propagate(False)

ttk.Label(launch_frame, text="Map Selection:").pack(anchor=W, padx=5)
CHX_Launch = ttk.Combobox(launch_frame, values=map_list, width=28, state="readonly")
if map_list and map_list[0] != "No Maps Found": CHX_Launch.current(0) # Select first map if available
CHX_Launch.pack(pady=5, fill=X, padx=5)

# --- START: Add Launch Mode Input ---
ttk.Label(launch_frame, text="Launch Mode:").pack(anchor=W, pady=(10, 0), padx=5)
var_launch_mode = StringVar(value="Mode111") # Default value
entry_launch_mode = ttk.Entry(launch_frame, textvariable=var_launch_mode, width=30)
entry_launch_mode.pack(pady=5, fill=X, padx=5)
# --- END: Add Launch Mode Input ---

btn_launch = ttk.Button(launch_frame, text="🎯 Launch", command=launch_instance)
btn_launch.pack(pady=15)

load_settings()
# Status Bar
status_var = StringVar()
status_var.set("Ready.")
status_bar = Label(window, textvariable=status_var, relief=SUNKEN, anchor=W,
                   bg="#f9f9f9", font=("Segoe UI", 10), fg="#2c3e50")
status_bar.pack(fill=X, side=BOTTOM)

window.protocol("WM_DELETE_WINDOW", on_closing)
# Run App
window.mainloop()
# --- END OF FILE Main.py ---