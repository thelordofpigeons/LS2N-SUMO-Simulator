from tkinter import *
from tkinter import ttk, messagebox
import Starter, Creator
import os

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

    style.map("TButton",
              background=[('active', '#e0e0e0'), ('!active', '#f2f2f2')],
              foreground=[('pressed', '#2c3e50')])

def create_instance():
    selected_map = CHX_Create.get()
    if not selected_map:
        messagebox.showwarning("Missing selection", "Please select a map.")
        return

    if var_infra_only.get():
        truck_count = 0
    else:
        try:
            truck_count = int(entry_truck_count.get())
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter a valid number of trucks.")
            return

    status_var.set(f"Creating instance with {truck_count} trucks...")
    vehicle_type = CHX_VehType.get()
    Creator.create(selected_map.split()[0], truck_count, vehicle_type)

    messagebox.showinfo("Success", f"{truck_count} trucks created on {selected_map}")
    status_var.set("Instance created successfully.")

def launch_instance():
    selected_map = CHX_Launch.get()
    if not selected_map:
        messagebox.showwarning("Missing selection", "Please select a map.")
        return

    messagebox.showinfo("Launching", f"Launching simulation on {selected_map}")
    status_var.set("Launching simulation...")
    window.quit()
    Starter.start(selected_map.split()[0], "Mode111")

# GUI Setup
window = Tk()
window.title("🚛 LS2N Simulator")
window.geometry("800x500")
window.configure(bg="#ffffff")

style_widgets()

# Main Frame
main_frame = Frame(window, bg="#ffffff")
main_frame.pack(pady=30)

# Header
title = Label(main_frame, text="LS2N Traffic Simulator", font=("Segoe UI", 22, "bold"),
              bg="#ffffff", fg="#2c3e50")
title.grid(row=0, column=0, columnspan=2, pady=10)

# Create Section (Card)
create_frame = ttk.LabelFrame(main_frame, text="🛠 Create Instance", style="Card.TLabelframe", padding=20)
create_frame.grid(row=1, column=0, padx=30, pady=10, ipadx=5, ipady=5)

ttk.Label(create_frame, text="Map Selection:").pack(anchor=W)
CHX_Create = ttk.Combobox(create_frame, values=["Nantes 1 (Est)", "Nantes 2 (Ouest)"], width=28)
CHX_Create.pack(pady=5)

#Frame to choose the number of trucks
ttk.Label(create_frame, text="Number of Trucks:").pack(anchor=W, pady=(10, 0))
entry_truck_count = ttk.Entry(create_frame, width=10)
entry_truck_count.insert(0, "10")
entry_truck_count.pack(pady=5)

#Frame to choose the vehicle type
ttk.Label(create_frame, text="Vehicle Type:").pack(anchor=W, pady=(10, 0))
CHX_VehType = ttk.Combobox(create_frame, values=["Truck", "MissionVehicle"], width=28)
CHX_VehType.current(1)  # Default to MissionVehicle
CHX_VehType.pack(pady=5)


# Infrastructure only checkbox
def toggle_infra_only():
    if var_infra_only.get():
        entry_truck_count.delete(0, END)
        entry_truck_count.insert(0, "0")
        entry_truck_count.config(state=DISABLED)
    else:
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
chk_infra_only.pack(anchor=W, pady=(10, 0))

ttk.Button(create_frame, text="🚀 Create", command=create_instance).pack(pady=15)

# Launch Section (Card)
launch_frame = ttk.LabelFrame(main_frame, text="🚦 Launch Simulation", style="Card.TLabelframe", padding=20)
launch_frame.grid(row=1, column=1, padx=30, pady=10, ipadx=5, ipady=5)

ttk.Label(launch_frame, text="Map Selection:").pack(anchor=W)
CHX_Launch = ttk.Combobox(launch_frame, values=["Nantes 1 (Est)", "Nantes 2 (Ouest)"], width=28)
CHX_Launch.pack(pady=5)

ttk.Button(launch_frame, text="🎯 Launch", command=launch_instance).pack(pady=15)

# Status Bar
status_var = StringVar()
status_var.set("Ready.")
status_bar = Label(window, textvariable=status_var, relief=SUNKEN, anchor=W,
                   bg="#f9f9f9", font=("Segoe UI", 10), fg="#2c3e50")
status_bar.pack(fill=X, side=BOTTOM)

# Run App
window.mainloop()
