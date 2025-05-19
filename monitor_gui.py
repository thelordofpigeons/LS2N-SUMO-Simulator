# --- START OF FILE monitor_gui.py ---
import tkinter as tk
from tkinter import ttk
import queue
import time  # For basic throttling if needed
import threading


class MonitorWindow:
    def __init__(self, root, data_queue):
        self.root = root
        self.data_queue = data_queue
        self.root.title("Simulation Monitor")
        self.root.geometry("800x400")

        # --- Data Storage ---
        self.truck_data = {}  # Store last known data keyed by truck ID

        # --- Treeview Setup ---
        self.tree_frame = ttk.Frame(self.root, padding="10")
        self.tree_frame.pack(fill=tk.BOTH, expand=True)

        # Define columns
        columns = ("truck_id", "action_type", "action_target",
                   "mission_status", "current_edge", "speed", "wait_time")
        self.tree = ttk.Treeview(
            self.tree_frame, columns=columns, show="headings", height=15)

        # Define headings
        self.tree.heading("truck_id", text="Truck ID")
        self.tree.heading("action_type", text="Action Type")
        self.tree.heading("action_target", text="Action Target")
        self.tree.heading("mission_status", text="Mission Status")
        self.tree.heading("current_edge", text="Current Edge")
        self.tree.heading("speed", text="Speed (km/h)")
        self.tree.heading("wait_time", text="Waiting Time (s)")

        # Configure column widths (adjust as needed)
        self.tree.column("truck_id", width=80, anchor=tk.W)
        self.tree.column("action_type", width=100, anchor=tk.W)
        self.tree.column("action_target", width=120, anchor=tk.W)
        self.tree.column("mission_status", width=100, anchor=tk.CENTER)
        self.tree.column("current_edge", width=120, anchor=tk.W)
        self.tree.column("speed", width=80, anchor=tk.E)
        self.tree.column("wait_time", width=100, anchor=tk.E)

        # Add scrollbar
        scrollbar = ttk.Scrollbar(
            self.tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.pack(fill=tk.BOTH, expand=True)

        # --- Start Update Loop ---
        # How often to check the queue (adjust as needed)
        self.update_interval_ms = 500
        self.check_queue()  # Start the process

    def check_queue(self):
        """Checks the queue for new data and updates the Treeview."""
        try:
            while not self.data_queue.empty():
                # Process all available data bundles since last check
                update_bundle = self.data_queue.get_nowait()

                # Check if it's a special signal (e.g., shutdown)
                if update_bundle == "SHUTDOWN":
                    print("Monitor GUI received shutdown signal.")
                    # Optionally disable controls or show a message
                    self.root.title("Simulation Monitor (Finished)")
                    return  # Stop checking the queue

                # Assuming update_bundle is a list of truck dictionaries
                if isinstance(update_bundle, list):
                    self.update_treeview(update_bundle)
                else:
                    print(
                        f"Monitor Warning: Received unexpected data type in queue: {type(update_bundle)}")

        except queue.Empty:
            # Queue is empty, nothing to do right now
            pass
        except Exception as e:
            # Log unexpected errors
            print(f"Error processing monitor queue: {e}")

        # Reschedule the check
        self.root.after(self.update_interval_ms, self.check_queue)

    def update_treeview(self, current_trucks_data):
        """Updates the Treeview with the latest data."""
        # Keep track of trucks currently in the treeview
        current_tree_ids = set(self.tree.get_children())
        updated_this_cycle = set()

        for truck_info in current_trucks_data:
            truck_id = truck_info.get("id", None)
            if not truck_id:
                continue

            updated_this_cycle.add(truck_id)
            values_tuple = (
                truck_id,
                truck_info.get("action_type", "N/A"),
                truck_info.get("action_target", "N/A"),
                truck_info.get("mission_status", "N/A"),
                truck_info.get("road_id", "N/A"),
                f"{truck_info.get('speed', 0.0):.1f}",
                f"{truck_info.get('wait_time', 0.0):.1f}"
            )

            if truck_id in current_tree_ids:
                # Update existing item
                self.tree.item(truck_id, values=values_tuple)
            else:
                # Insert new item
                self.tree.insert("", tk.END, iid=truck_id, values=values_tuple)

            # Store data for potential future use (e.g., highlighting changes)
            self.truck_data[truck_id] = truck_info

        # Remove trucks from treeview that are no longer in the simulation data
        ids_to_remove = current_tree_ids - updated_this_cycle
        for item_id in ids_to_remove:
            self.tree.delete(item_id)
            if item_id in self.truck_data:
                del self.truck_data[item_id]  # Clean up stored data


# --- Main function to start the GUI (usually called by Starter.py) ---
def start_monitor_gui(data_queue):
    root = tk.Tk()
    app = MonitorWindow(root, data_queue)
    root.mainloop()


# --- Example Usage (for testing monitor_gui.py directly) ---
if __name__ == "__main__":
    # Create a dummy queue for testing
    test_queue = queue.Queue()

    # Function to simulate data coming from Starter.py
    def simulate_data_sender(q):
        truck_counter = 0
        step = 0
        action_types = ["Load", "Park", "Go", "Unload"]
        targets = ["CS0", "Prk1", "Out1", "CS1"]
        statuses = ["0", "1", "2", "3"]
        edges = ["edge1", "edge2", "edge3", "-9857_0"]

        while True:
            step += 1
            sim_data = []
            num_trucks_this_step = min(5, step)  # Simulate trucks appearing

            for i in range(1, num_trucks_this_step + 1):
                truck_id = f"trk{i}"
                sim_data.append({
                    "id": truck_id,
                    "action_type": action_types[step % len(action_types)],
                    "action_target": targets[(i+step) % len(targets)],
                    "mission_status": statuses[step % len(statuses)],
                    "road_id": edges[(i * step) % len(edges)],
                    "speed": max(0, 20.5 - (step % 25) + i),
                    "wait_time": max(0, (step % 30 - 15) + i*2)
                })

            # Add a disappearing truck sometimes
            if step % 10 == 0 and num_trucks_this_step > 2:
                sim_data.pop(1)  # Remove second truck

            q.put(sim_data)
            print(f"Sim: Sent data for step {step}")
            time.sleep(1.5)  # Simulate time between steps

            if step > 25:  # Simulate end
                q.put("SHUTDOWN")
                print("Sim: Sent SHUTDOWN")
                break

    # Start the simulator thread
    sim_thread = threading.Thread(
        target=simulate_data_sender, args=(test_queue,), daemon=True)
    sim_thread.start()

    # Start the GUI
    start_monitor_gui(test_queue)

# --- END OF FILE monitor_gui.py ---
