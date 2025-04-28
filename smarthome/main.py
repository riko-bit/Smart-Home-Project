import tkinter as tk
from tkinter import filedialog, messagebox
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import os   # For path

from modules.battery import Battery
from modules.load_profile import ElectricLoad
from modules.met_data import MeteorologicalData
from modules.calculations import Calculations

PEAK_START = 17
PEAK_END = 22

class EnergyAnalyzerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Energy Analyzer")
        self.threshold = tk.DoubleVar(value=3.0)

        # Universal default directory for file selection
        self.default_directory = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data'))

        # File selection
        tk.Label(root, text="Select Load Profile File:").grid(row=0, column=0, padx=5, pady=5)
        tk.Button(root, text="Browse", command=self.select_load_file).grid(row=0, column=1, padx=5, pady=5)

        tk.Label(root, text="Select Meteorological Data File:").grid(row=1, column=0, padx=5, pady=5)
        tk.Button(root, text="Browse", command=self.select_meteorology_file).grid(row=1, column=1, padx=5, pady=5)

        # Threshold input
        tk.Label(root, text="Set Threshold:").grid(row=2, column=0, padx=5, pady=5)
        tk.Entry(root, textvariable=self.threshold).grid(row=2, column=1, padx=5, pady=5)

        # Analyze button
        tk.Button(root, text="Analyze", command=self.run_analysis).grid(row=3, column=0, columnspan=2, pady=10)

        # Output area
        self.output_text = tk.Text(root, wrap=tk.WORD, height=15, width=50)
        self.output_text.grid(row=4, column=0, columnspan=2, padx=5, pady=5)

        # Initialize file paths as None
        self.load_file_path = None
        self.met_file_path = None

    def select_load_file(self):
        # Open file dialog for selecting the load profile file
        self.load_file_path = filedialog.askopenfilename(
            filetypes=[("Excel files", "*.xlsx")],
            initialdir=self.default_directory  # Set universal default directory
        )
        if self.load_file_path:
            try:
                # Validate file format or load preview here
                print(f"Load profile file selected: {self.load_file_path}")
                self.default_load_dir = os.path.dirname(self.load_file_path)
            except Exception as e:
                messagebox.showerror("Error", f"Error loading file: {str(e)}")

    def select_meteorology_file(self):
        # Open file dialog for selecting the meteorological data file
        self.met_file_path = filedialog.askopenfilename(
            filetypes=[("CSV files", "*.csv")],
            initialdir=self.default_directory  # Set universal default directory
        )
        if self.met_file_path:
            try:
                # Validate file format or load preview here
                print(f"Meteorological data file selected: {self.met_file_path}")
                self.default_met_dir = os.path.dirname(self.met_file_path)
            except Exception as e:
                messagebox.showerror("Error", f"Error loading file: {str(e)}")


    def run_analysis(self):
        if not self.load_file_path or not self.met_file_path:
            messagebox.showerror("Error", "Please select both load profile and meteorological data files.")
            return
        
        try:                            
            # Load data
            winter_profile_df, summer_profile_df = ElectricLoad.from_excel(self.load_file_path)
            winter_meteorological_df, summer_meteorological_df = MeteorologicalData.from_csv(self.met_file_path)

            threshold = self.threshold.get()                    # Get the threshold value
            print(f"Threshold set to: {threshold}")
            peak_hours = list(range(PEAK_START, PEAK_END + 1))  # Define peak hours
            print(f"Peak hours: {peak_hours}")

            print("\n===================WINTER PROFILE===================\n")

            temp = self.generate_hourly_profile(winter_profile_df)
            max_rated_power = max(temp['Power (kW)'])  # Get the maximum rated power
            print(f"Max load set to: {max_rated_power}")

            # Create a battery instance for winter
            battery = Battery(      # Create a battery instance
                capacity=max_rated_power * 0.5,  # 50% of max rated power as capacity
                charge_rate=0.2,    # Charge rate set to 0.2 kW
                discharge_rate=0.3,     # Discharge rate set to 0.3 kW
                soc=(max_rated_power * 0.5) * 0.1,  # Initial SoC set to 10% of capacity
                panel_area=10,
                panel_efficiency=.70,
            )

            battery_winter_profile_df, winter_soc = battery.simulate_battery(winter_profile_df, winter_meteorological_df, threshold, peak_hours)    # Manage battery for winter profile
            shifted_winter_profile_df = Calculations.shift_loads(battery_winter_profile_df, threshold, peak_hours)    # Shift winter profile

            print(f"\nOriginal Profile: {type(winter_profile_df)}, Shape: {np.shape(winter_profile_df)}")
            print(f"Battery Profile: {type(battery_winter_profile_df)}, Shape: {np.shape(battery_winter_profile_df)}")
            print(f"Shifted Profile: {type(shifted_winter_profile_df)}, Shape: {np.shape(shifted_winter_profile_df)}")    

            winter_hourly = EnergyAnalyzerApp.generate_adjusted_profile(winter_profile_df)  # Generate adjusted winter profile
            battery_winter_hourly = EnergyAnalyzerApp.generate_adjusted_profile(winter_profile_df, battery_winter_profile_df)
            shifted_winter_hourly = EnergyAnalyzerApp.generate_adjusted_profile(shifted_winter_profile_df, battery_winter_profile_df)

            winter_cost = Calculations.calculate_energy_cost(winter_hourly, peak_hours)
            battery_winter_cost = Calculations.calculate_energy_cost(battery_winter_hourly, peak_hours)
            shifted_winter_cost = Calculations.calculate_energy_cost(shifted_winter_hourly, peak_hours)

            # Display results in the output text box
            self.output_text.delete("1.0", tk.END)
            self.output_text.insert(tk.END, f"Winter Hourly Energy Cost (Original): {winter_cost:.3f} $\n")
            self.output_text.insert(tk.END, f"Winter Hourly Energy Cost (Battery): {battery_winter_cost:.3f} $\n")
            self.output_text.insert(tk.END, f"Winter Hourly Energy Cost (Shifted): {shifted_winter_cost:.3f} $\n")

            print("\n===================SUMMER PROFILE===================\n")

            temp = self.generate_hourly_profile(summer_profile_df)
            max_rated_power = max(temp['Power (kW)'])  # Get the maximum rated power
            print(f"Max load set to: {max_rated_power}")

            # Create a battery instance for summer
            battery = Battery(      # Create a battery instance
                capacity=max_rated_power * 0.5,  # 50% of max rated power as capacity
                charge_rate=0.2,    # Charge rate set to 0.2 kW
                discharge_rate=0.3,     # Discharge rate set to 0.3 kW
                soc=0.1 * max_rated_power * 0.5,  # Initial SoC set to 10% of capacity
                panel_area=10,
                panel_efficiency=.70,
            )

            battery_summer_profile_df, summer_soc = battery.simulate_battery(summer_profile_df, summer_meteorological_df, threshold, peak_hours)    # Manage battery for summer profile
            shifted_summer_profile_df = Calculations.shift_loads(battery_summer_profile_df, threshold, peak_hours)    # Shift summer profile

            print(f"\nOriginal Profile: {type(summer_profile_df)}, Shape: {np.shape(summer_profile_df)}")                 # Display the original profile
            print(f"Battery Profile: {type(battery_summer_profile_df)}, Shape: {np.shape(battery_summer_profile_df)}")
            print(f"Shifted Profile: {type(shifted_summer_profile_df)}, Shape: {np.shape(shifted_summer_profile_df)}") 

            summer_hourly = EnergyAnalyzerApp.generate_adjusted_profile(summer_profile_df)
            battery_summer_hourly = EnergyAnalyzerApp.generate_adjusted_profile(summer_profile_df, battery_summer_profile_df)
            shifted_summer_hourly = EnergyAnalyzerApp.generate_adjusted_profile(shifted_summer_profile_df, battery_summer_profile_df)
            
            summer_cost = Calculations.calculate_energy_cost(summer_hourly, peak_hours)
            battery_summer_cost = Calculations.calculate_energy_cost(battery_summer_hourly, peak_hours)
            shifted_summer_cost = Calculations.calculate_energy_cost(shifted_summer_hourly, peak_hours)

            # Display results in the output text box
            self.output_text.insert(tk.END, f"\nSummer Hourly Energy Cost (Original): {summer_cost:.3f} $\n")
            self.output_text.insert(tk.END, f"Summer Hourly Energy Cost (Battery): {battery_summer_cost:.3f} $\n")
            self.output_text.insert(tk.END, f"Summer Hourly Energy Cost (Shifted): {shifted_summer_cost:.3f} $\n")

            # Plot the profiles
            self.plot_seasonal_profiles(
                winter_hourly, battery_winter_hourly, shifted_winter_hourly, winter_meteorological_df, winter_soc, winter_cost, battery_winter_cost, shifted_winter_cost,
                summer_hourly, battery_summer_hourly, shifted_summer_hourly, summer_meteorological_df, summer_soc, summer_cost, battery_summer_cost, shifted_summer_cost,
                threshold, peak_hours
            )

        except Exception as e:
            messagebox.showerror("Error", str(e))

    @staticmethod
    def plot_seasonal_profiles(winter_hourly, battery_winter_hourly, shifted_winter_hourly, winter_meteorological_df, winter_soc, winter_cost, battery_winter_cost, shifted_winter_cost,
                               summer_hourly, battery_summer_hourly, shifted_summer_hourly, summer_meteorological_df, summer_soc, summer_cost, battery_summer_cost, shifted_summer_cost,
                               threshold, peak_hours):
        """Plot winter and summer profiles as bar charts."""

        # Meteorological data plots
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10))
        width = 0.50
        x = np.arange(24)

        ax1.bar(x, winter_meteorological_df['Irradiation (kW/m^2)'], width, label='Solar Irradiation', color='yellow', alpha=0.7)
        ax1.set_title('Winter Meteorological Data')
        ax1.set_xlabel('Hour of Day')
        ax1.set_ylabel('Irradiation (kW/m^2)')
        ax1.set_xticks(x)
        ax1.set_xticklabels([str(i) for i in range(24)])
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        ax2.bar(x, summer_meteorological_df['Irradiation (kW/m^2)'], width, label='Solar Irradiation', color='yellow', alpha=0.7)
        ax2.set_title('Summer Meteorological Data')
        ax2.set_xlabel('Hour of Day')
        ax2.set_ylabel('Irradiation (kW/m^2)')
        ax2.set_xticks(x)
        ax2.set_xticklabels([str(i) for i in range(24)])
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.show()

        # State of Charge plots
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10))
        width = 0.50
        x = np.arange(24)

        ax1.bar(x, winter_soc['State of Charge (%)'], width, label='Battery SoC', color='orange', alpha=0.7)
        ax1.set_title('Winter SoC')
        ax1.set_xlabel('Hour of Day')
        ax1.set_ylabel('State of Charge (%)')
        ax1.set_xticks(x)
        ax1.set_xticklabels([str(i) for i in range(24)])
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        ax2.bar(x, summer_soc['State of Charge (%)'], width, label='Battery SoC', color='orange', alpha=0.7)
        ax2.set_title('Summer SoC')
        ax2.set_xlabel('Hour of Day')
        ax2.set_ylabel('State of Charge (%)')
        ax2.set_xticks(x)
        ax2.set_xticklabels([str(i) for i in range(24)])
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.show()

        # Load profiles
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10))
        width = 0.3
        x = np.arange(24)

        ax1.bar(x - width, winter_hourly['Power (kW)'], width, label='Original Profile', color='blue', alpha=0.7)
        ax1.bar(x, battery_winter_hourly['Power (kW)'], width, label='Battery Profile', color='green', alpha=0.7)
        ax1.bar(x + width, shifted_winter_hourly['Power (kW)'], width, label='Shifted Profile', color='red', alpha=0.7)
        ax1.axvspan(min(peak_hours)-0.5, max(peak_hours)+0.5, color='yellow', alpha=0.2, label='Peak Hours')
        ax1.axhline(threshold, color='black', linestyle='--', linewidth=1.5, label='Threshold')
        ax1.set_title('Winter Load Profiles')
        ax1.set_xlabel('Hour of Day')
        ax1.set_ylabel('Power (kW)')
        ax1.set_xticks(x)
        ax1.set_xticklabels([str(i) for i in range(24)])
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        ax2.bar(x - width, summer_hourly['Power (kW)'], width, label='Original Profile', color='blue', alpha=0.7)
        ax2.bar(x, battery_summer_hourly['Power (kW)'], width, label='Battery Profile', color='green', alpha=0.7)
        ax2.bar(x + width, shifted_summer_hourly['Power (kW)'], width, label='Shifted Profile', color='red', alpha=0.7)
        ax2.axvspan(min(peak_hours)-0.5, max(peak_hours)+0.5, color='yellow', alpha=0.2, label='Peak Hours')
        ax2.axhline(threshold, color='black', linestyle='--', linewidth=1.5, label='Threshold')
        ax2.set_title('Summer Load Profiles')
        ax2.set_xlabel('Hour of Day')
        ax2.set_ylabel('Power (kW)')
        ax2.set_xticks(x)
        ax2.set_xticklabels([str(i) for i in range(24)])
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.show()

        # Cost graphs
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10))
        width = 0.3
        x = 3

        ax1.bar(x - width, winter_cost, width, label='Original Profile', color='blue', alpha=0.7)
        ax1.bar(x, battery_winter_cost, width, label='Battery Profile', color='green', alpha=0.7)
        ax1.bar(x + width, shifted_winter_cost, width, label='Shifted Profile', color='red', alpha=0.7)
        ax1.set_title('Winter Cost Calculations')
        ax1.set_ylabel('Cost ($)')
        ax1.set_xticks([x - width, x, x + width])
        ax1.set_xticklabels(['Original\nProfile', 'Battery\nProfile', 'Shifted\nProfile'])
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        ax2.bar(x - width, summer_cost, width, label='Original Profile', color='blue', alpha=0.7)
        ax2.bar(x, battery_summer_cost, width, label='Battery Profile', color='green', alpha=0.7)
        ax2.bar(x + width, shifted_summer_cost, width, label='Shifted Profile', color='red', alpha=0.7)
        ax2.set_title('Summer Cost Calculations')
        ax2.set_ylabel('Cost ($)')
        ax2.set_xticks([x - width, x, x + width])
        ax2.set_xticklabels(['Original\nProfile', 'Battery\nProfile', 'Shifted\nProfile'])
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.show()

    @staticmethod
    def generate_adjusted_profile(df, battery_df=None):
        """Generate the adjusted profile, considering battery discharge if provided."""
        
        # Generate the hourly profile for the given dataframe
        hourly_profile = EnergyAnalyzerApp.generate_hourly_profile(df)
        
        # If battery_df is provided, adjust the profile by subtracting battery discharge
        if battery_df is not None:
            # Extract battery discharge entries from the battery_df
            battery_entries = battery_df[battery_df['Name'].str.contains('Battery Discharge', na=False)]
            
            # Create battery discharge profile
            battery_discharge = pd.DataFrame(0, index=np.arange(24), columns=['Power (kW)'])
            
            # Sum up battery discharge for each hour
            for _, row in battery_entries.iterrows():
                hour = int(row['Start'])
                discharge = abs(row['Rated Power (kW)'])  # Convert negative discharge to positive
                battery_discharge.loc[hour, 'Power (kW)'] += discharge
            
            # Subtract battery discharge from the original hourly profile
            hourly_profile['Power (kW)'] -= battery_discharge['Power (kW)']
        
        return hourly_profile

    @staticmethod
    def generate_hourly_profile(df):
        """Generate hourly power profile from appliance usage."""
        
        # Create an empty DataFrame to store hourly data
        hourly_profile = pd.DataFrame(0, index=np.arange(24), columns=['Power (kW)'])
        
        # Iterate through each row (appliance data)
        for _, row in df.iterrows():
            start_time = row['Start']
            end_time = row['End']
            power = row['Rated Power (kW)']
            
            if start_time < end_time:
                hourly_profile.loc[int(start_time):int(end_time)-1, 'Power (kW)'] += power
            else:
                hourly_profile.loc[int(start_time):23, 'Power (kW)'] += power
                hourly_profile.loc[0:int(end_time)-1, 'Power (kW)'] += power
        
        return hourly_profile


# Show the plot
plt.show()
# Run the GUI application
if __name__ == "__main__":
    root = tk.Tk()
    app = EnergyAnalyzerApp(root)
    root.mainloop()