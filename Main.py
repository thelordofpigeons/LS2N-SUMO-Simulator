# --- START OF FILE Main.py ---
import json # Needed for next commit, adding now is fine
import tkinter.scrolledtext as scrolledtext # Needed later for logging
from tkinter import *
from tkinter import ttk, messagebox
import Starter, Creator
import os
import threading # Added for Progress Bar
import tkinter.scrolledtext as scrolledtext 
# --- Define Config File Path ---
CONFIG_FILE = "gui_config.json"


def save_settings():
    """Saves current GUI settings to a JSON file."""
    settings = {
        "create_map": CHX_Create.get(),
        "launch_map": CHX_Launch.get(),
        "truck_count": entry_truck_count.get(),
        "vehicle_type": CHX_VehType.get(),
        "infra_only": var_infra_only.get(),
        "launch_mode": var_launch_mode.get()
        # Add last_created_map if you implement that feature later
    }
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(settings, f, indent=4)
        log_message(f"Settings saved to {CONFIG_FILE}")
    except IOError as e:
        log_message(f"ERROR saving settings to {CONFIG_FILE}: {e}")
    except Exception as e:
        log_message(f"ERROR saving settings ({type(e).__name__}): {e}")


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
    log_message(f"Creating instance for '{map_name}' with {truck_count} {vehicle_type}(s)...")
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
            log_message(f"SUCCESS: {window.creator_result['message']}")
            messagebox.showinfo("Success", window.creator_result["message"]) # Keep popup for clear success
        else:
            error_details = f"\nDetails: {window.creator_result['error']}" if window.creator_result['error'] else ""
            log_message(f"ERROR: {window.creator_result['message']}{error_details}")
            messagebox.showerror("Error", window.creator_result["message"] + error_details) # Keep popup for errors
        log_message("-" * 20) # Add separator


# --- Replace the existing launch_instance function ---
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

    log_message(f"Initiating simulation process for {map_name} (Mode: {launch_mode})...")
    # Optional: Disable launch button to prevent multiple launches?
    # btn_launch.config(state=DISABLED)

    # --- Run Starter.start in a separate thread ---
    starter_thread = threading.Thread(
        target=_run_starter_thread,
        args=(map_name, launch_mode),
        daemon=True # Allows main GUI to exit even if sim thread has issues (can be debated)
    )
    starter_thread.start()

    # Log that the process has started (monitor window should appear via Starter)
    log_message("Simulation & Monitor process started in background.")
    log_message("You can continue using this setup window or close it.")
    messagebox.showinfo("Process Started", f"Simulation process for '{map_name}' initiated.\nA separate monitor window should appear shortly.")

# --- END of replacement for launch_instance ---
# --- Add this new helper function ---
def _run_starter_thread(map_name, launch_mode):
    """Worker function to run Starter.start in a thread."""
    try:
        # This call now blocks *this thread*, not the main GUI thread
        Starter.run_simulation(map_name, launch_mode)
        print(f"Starter thread for {map_name} finished.") # Log to console
        # Optionally, use root.after from here to schedule a log message in the main GUI
        # window.after(0, lambda: log_message(f"Simulation process for {map_name} completed."))
        # window.after(0, lambda: btn_launch.config(state=NORMAL)) # Re-enable button if disabled
    except Exception as e:
        # Log errors that happen deep within Starter execution to console/main log
        print(f"ERROR in Starter thread for {map_name} (Mode: {launch_mode}): {e}")
        import traceback
        traceback.print_exc()
        # Try logging to the main GUI log area using schedule_callback (needs window access or queue)
        # For simplicity now, just print. A queue back to Main.py would be better.
        # window.after(0, lambda: log_message(f"ERROR in simulation thread: {e}"))
        # window.after(0, lambda: btn_launch.config(state=NORMAL)) # Re-enable button on error too
# --- End of new helper function ---
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
main_frame.pack(pady=15, padx=10, fill=BOTH, expand=True) # Allow frame to expand
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
        # Checkbox is checked: Disable entry, set value to 0
        entry_truck_count.delete(0, END)
        entry_truck_count.insert(0, "0")
        entry_truck_count.config(state=DISABLED)
    else:
        # Checkbox is unchecked: Enable entry, reset value to 10
        entry_truck_count.config(state=NORMAL) # <<< This line is simplified
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
log_frame = ttk.Frame(window, padding=(10, 5))
log_frame.pack(fill=X, expand=False, side=BOTTOM, padx=10, pady=(0, 10))

log_label = ttk.Label(log_frame, text="Log Output:", font=("Segoe UI", 10, "bold"))
log_label.pack(anchor=W)

log_area = scrolledtext.ScrolledText(
    log_frame,
    height=8, # Adjust height as needed
    wrap=WORD, # Wrap lines at word boundaries
    font=("Consolas", 9), # Use a monospace font for logs if preferred
    state=DISABLED, # Start as read-only
    bg="#f0f0f0",
    fg="#1a1a1a"
)
log_area.pack(fill=BOTH, expand=True)

# --- Add Log Message Function ---
def log_message(message):
    """Appends a message to the log area."""
    log_area.config(state=NORMAL) # Enable writing
    log_area.insert(END, message + "\n")
    log_area.config(state=DISABLED) # Disable writing
    log_area.see(END) # Scroll to the end

log_message("LS2N Simulator Ready.")
log_message("Please select map and options, then Create or Launch.")

window.protocol("WM_DELETE_WINDOW", on_closing)
# Run App
window.mainloop()
# --- END OF FILE Main.py ---