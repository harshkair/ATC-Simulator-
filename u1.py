import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import random
import tkinter as tk
from pymongo import MongoClient

# MongoDB connection
client = MongoClient('mongodb://localhost:27017/')  # Connect to MongoDB server
db = client['flight_atc']  # Create or retrieve the flight_atc database
flight_info1 = db['flight_info1']  # Reference flight_info1 collection
finished_1 = db['finished_1']  # Reference finished_1 collection

class Window:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Flight Information")
        self.root.geometry("250x250")

class FlightWindow:
    def __init__(self, flight_info, blimp, button, radar_display):
        self.flight_info = flight_info
        self.blimp = blimp
        self.button = button
        self.radar_display = radar_display
        self.root = tk.Tk()
        self.root.title("Flight Details")
        self.root.geometry("400x300")  # Set a larger size for the window
        self.cancel_id = None  # Initialize cancel_id attribute

        for i, (key, value) in enumerate(flight_info.items()):
            if key == "Status":
                if value == "Passing":
                    tk.Label(self.root, text="Status: Passing").grid(row=i, column=0, sticky="w")
                else:
                    tk.Label(self.root, text=f"{key}: {value}").grid(row=i, column=0, sticky="w")
            elif key not in ["Source", "Destination"]:  # Exclude source and destination
                tk.Label(self.root, text=f"{key}: {value}").grid(row=i, column=0, sticky="w")

        if flight_info["Status"] != "Passing":
            if flight_info["Status"] == "Takeoff":
                tk.Label(self.root, text="Destination:").grid(row=i+1, column=0, sticky="w")
                tk.Label(self.root, text=flight_info["Destination"]).grid(row=i+1, column=1, sticky="w")
            if flight_info["Status"] == "Landing":
                tk.Label(self.root, text="Source:").grid(row=i+2, column=0, sticky="w")
                tk.Label(self.root, text=flight_info["Source"]).grid(row=i+2, column=1, sticky="w")
            if flight_info["Status"] != "Passing":
                tk.Label(self.root, text="Runway Number:").grid(row=i+3, column=0, sticky="w")
                self.runway_entry = tk.Entry(self.root)
                self.runway_entry.grid(row=i+3, column=1)

                tk.Label(self.root, text="Boarding/Arrival Gate Number:").grid(row=i+4, column=0, sticky="w")
                self.gate_entry = tk.Entry(self.root)
                self.gate_entry.grid(row=i+4, column=1)

        tk.Label(self.root, text="Heading:").grid(row=i+5, column=0, sticky="w")
        self.heading_entry = tk.Entry(self.root)
        self.heading_entry.grid(row=i+5, column=1)

        tk.Label(self.root, text="Level:").grid(row=i+6, column=0, sticky="w")
        self.level_entry = tk.Entry(self.root)
        self.level_entry.grid(row=i+6, column=1)

        tk.Button(self.root, text="Submit", command=self.submit).grid(row=i+7, columnspan=2)

    def submit(self):
        if self.flight_info["Status"] != "Passing":
            runway = self.runway_entry.get()
            gate = self.gate_entry.get()
            if runway.isdigit() and 1 <= int(runway) <= 7:
                self.flight_info["Runway Number"] = int(runway)
            else:
                tk.messagebox.showerror("Error", "Runway number should be an integer between 1 and 7.")
                return

            if gate.isdigit() and 1 <= int(gate) <= 12:
                self.flight_info["Gate Number"] = int(gate)
            else:
                tk.messagebox.showerror("Error", "Gate number should be an integer between 1 and 12.")
                return

        heading = self.heading_entry.get()
        if heading.isdigit():
            self.flight_info["Heading"] = int(heading)
        else:
            tk.messagebox.showerror("Error", "Heading should be an integer.")
            return

        level = self.level_entry.get()
        self.flight_info["Level"] = level

        # Update MongoDB finished_1 collection
        finished_1.insert_one(self.flight_info)

        # Close the flight info window
        self.root.destroy()

        # Remove blimp and button
        del self.radar_display.blimps[self.blimp]
        self.button.destroy()
        self.radar_display.redraw_plot()

        # Move flight to finished dictionary
        self.radar_display.move_to_finished(self.flight_info)

class RadarDisplay:
    def __init__(self, window):
        self.window = window
        self.fig, self.ax = plt.subplots(figsize=(8, 8))
        self.ax.set_aspect('equal')
        self.ax.set_xlim(-10, 10)
        self.ax.set_ylim(-10, 10)
        self.ax.set_facecolor('black')
        self.blimps = {}  # Dictionary to store blimp plots
        self.buttons = {}  # Dictionary to store button widgets
        self.flight_info = []  # List to store flight information dictionaries
        self.finished = {}  # Dictionary to store finished flight information
        self.current_flight_index = 0  # Track the current flight index
        self.create_flight_info()  # Generate initial flight information
        self.create_initial_blimps()  # Create initial blimps to display

        # Add rotating lime-colored line
        self.rotating_line, = self.ax.plot([], [], color='lime', linewidth=2)
        self.animation = animation.FuncAnimation(self.fig, self.update_rotation, frames=360, interval=10)

        # Schedule adding new blimps
        self.add_blimps_schedule()

    def create_flight_info(self):
        # Generate initial flight information dictionaries
        num_flights = random.randint(10, 20)
        for _ in range(num_flights):
            flight_info = self.generate_flight_info()
            self.flight_info.append({"info": flight_info, "taken_care_of": False})  # Mark flights as not taken care of initially
            # Update MongoDB flight_info1 collection
            flight_info1.insert_one(flight_info)

    def create_initial_blimps(self):
        # Create initial blimps to display (up to 5)
        for _ in range(5):
            self.add_blimp_and_button()

    def add_blimp_and_button(self):
        if self.current_flight_index < len(self.flight_info):
            flight_info = self.flight_info[self.current_flight_index]["info"]
            x = random.uniform(-10, 10)
            y = random.uniform(-10, 10)
            flight_number = flight_info["Flight Number"]
            blimp = self.ax.annotate(flight_number, (x, y), color='lime', fontsize=15, ha='center')  # Set blimp color to green
            self.blimps[blimp] = flight_info
            button_text = f"{flight_number}\n(Blimp {self.current_flight_index + 1})"
            button = tk.Button(self.window.root, text=button_text)
            button.grid(row=len(self.blimps) + 1, column=0, pady=5)
            self.buttons[blimp] = button
            button.config(command=lambda b=blimp: self.open_flight_window(b))
            self.current_flight_index += 1

    def add_blimps_schedule(self):
        # Schedule adding new blimps until all flights are taken care of
        self.window.root.after(10000, self.add_blimp_and_button_delayed)

    def add_blimp_and_button_delayed(self):
        if not all(flight["taken_care_of"] for flight in self.flight_info):
            self.add_blimp_and_button()
            self.add_blimps_schedule()  # Schedule next addition

    def open_flight_window(self, blimp):
        flight_info = self.blimps[blimp]
        button = self.buttons[blimp]
        FlightWindow(flight_info, blimp, button, self)  # Pass blimp object as argument

    def move_to_finished(self, flight_info):
        for flight in self.flight_info:
            if flight["info"] == flight_info:
                self.finished[flight_info["Flight Number"]] = flight_info
                self.flight_info.remove(flight)
                break

    def update_rotation(self, frame):
        radius = 10
        x = [0, radius * np.sin(np.radians(frame))]
        y = [0, radius * np.cos(np.radians(frame))]
        self.rotating_line.set_data(x, y)
        return self.rotating_line,

    def generate_flight_info(self):
        # Generate random flight information
        flight_number = f"FL{random.randint(1, 100)}"
        model = random.choice(["Boeing 737", "Airbus A320", "Boeing 787", "Airbus A380"])
        source = random.choice(["New York", "Los Angeles", "London", "Tokyo", "Paris"])
        destination = random.choice(["Sydney", "Dubai", "Beijing", "Singapore", "Toronto"])
        heading = random.randint(0, 360)  # Random heading in degrees
        status = random.choice(["Landing", "Takeoff", "Passing"])
        return {
            "Flight Number": flight_number,
            "Model": model,
            "Source": source,
            "Destination": destination,
            "Heading": heading,
            "Status": status
        }

    def redraw_plot(self):
        self.ax.clear()
        self.ax.set_aspect('equal')
        self.ax.set_xlim(-10, 10)
        self.ax.set_ylim(-10, 10)
        self.rotating_line, = self.ax.plot([], [], color='lime', linewidth=2)
        self.animation = animation.FuncAnimation(self.fig, self.update_rotation, frames=360, interval=10, init_func=self.init_rotation)
        for blimp, flight_info in self.blimps.items():
            x, y = blimp.get_position()  # Retrieve position of the blimp annotation
            flight_number = flight_info["Flight Number"]
            self.ax.annotate(flight_number, (x, y), color='lime', fontsize=15, ha='center')  # Annotate blimps with flight number
        plt.draw()

    def init_rotation(self):
        self.rotating_line.set_data([], [])
        return self.rotating_line,

if __name__ == "__main__":
    window = Window()
    radar_display = RadarDisplay(window)
    plt.show()
