import pandas as pd

class Battery:
    def __init__(self, capacity: float, charge_rate: float, discharge_rate: float, soc: float, panel_area: float, panel_efficiency: float):
        self.capacity = capacity  # kWh
        self.charge_rate = charge_rate  # kW
        self.discharge_rate = discharge_rate  # kW
        self.soc = soc  # State of charge (%)
        self.panel_area = panel_area  # m^2
        self.panel_efficiency = panel_efficiency  # Efficiency (decimal)

    def simulate_battery(self, profile_df, solar_irradiance_df, threshold, peak_hours):
        """
        Simulate the battery operation, adjusting the device consumption based on the available solar power and battery SoC.

        Args:
            profile_df (DataFrame): Hourly energy consumption profile (kW).
            solar_irradiance_df (DataFrame): Hourly solar irradiance values (kW/m^2).
            peak_hours (list): List of hours considered as peak hours.

        Returns:
            DataFrame: Modified profile with adjusted rated powers.
        """
        print(f"\nSimulating Battery...")
        discharge_log = []  # List to store discharge details per hour
        soc_log = []  # List to store SoC values per hour
        hourly_powers = self.calculate_hourly_power(profile_df)  # Calculate hourly power consumption

        for hour in range(24):
            irradiance = 0  
            if hour in solar_irradiance_df['Hour'].values:  # Get solar irradiance for the current hour
                irradiance_row = solar_irradiance_df[solar_irradiance_df['Hour'] == hour]
                irradiance = irradiance_row.iloc[0]['Irradiation (kW/m^2)']

            print(f"Hour {hour} - Solar irradiance: {irradiance:.2f} kW/m^2, Current SoC: {self.soc:.2f}%")
            soc_log.append({'Hour': hour, 'State of Charge (%)': self.soc})  # Log the current SoC
            
            if self.soc < 80:   # Charge battery with solar energy if SoC is below 80%
                if hour in peak_hours:
                    # In peak hours, charge up to 50% if solar irradiance is available
                    if self.soc < 50 and irradiance > 0:
                        self.charge_battery_with_solar(irradiance, in_peak_hours=True)
                else:
                    if irradiance > 0:
                        self.charge_battery_with_solar(irradiance, in_peak_hours=False)

            if hour in peak_hours:  # Discharge logic during peak hours
                discharge_info = self.discharge_battery(hourly_powers[hour], threshold, hour)
                discharge_log.append(discharge_info)
                
                if self.soc < 30 or irradiance > 0:  # Recharge if SoC is below 30% in peak hours or solar energy is available
                    self.charge_battery_with_solar(irradiance, in_peak_hours=True)
                
            else:
                discharge_log.append({'Hour': hour, 'Discharge (kW)': 0, 'State of Charge (%)': self.soc})

        discharge_df = pd.DataFrame(discharge_log)  # Combine all discharge information into a single DataFrame
        print(f"\n{discharge_df}")
        soc_df = pd.DataFrame(soc_log)  # Convert SoC log into a DataFrame
        print(f"\n{soc_df}")

        updated_df = self.update_profile(profile_df, discharge_df)

        print(f"Battery Simulation Complete.")
        return updated_df, soc_df

    def discharge_battery(self, hourly_power, threshold, hour):
        """
        Attempt to discharge the battery during peak hours to reduce power consumption.

        Args:
            hourly_power (float): The power consumption for the current hour.
            threshold (float): The threshold for minimum power consumption.
            hour (int): The current hour being processed.

        Returns:
            dict: A dictionary containing discharge information for the hour.
        """
        if self.soc > 30 and hourly_power > threshold:
            print(f"Hour {hour} - Discharge conditions met. SoC is {self.soc}% and power needed is {hourly_power} kW (Threshold: {threshold} kW)")
            max_safe_discharge = (self.soc - 30) / 100 * self.capacity
            discharge = min(self.discharge_rate * self.capacity, hourly_power - threshold, max_safe_discharge)
            print(f"Hour {hour} - Calculated discharge: {discharge} kW")

            self.update_soc(-discharge * 100 / self.capacity)
            print(f"Hour {hour} - Updated SoC after discharge: {self.soc}%")
            return {'Hour': hour, 'Discharge (kW)': discharge, 'State of Charge (%)': self.soc}
        else:
            print(f"Hour {hour} - Discharge conditions not met: SoC = {self.soc}%, Power needed = {hourly_power} kW, Threshold = {threshold} kW")
            return {'Hour': hour, 'Discharge (kW)': 0, 'State of Charge (%)': self.soc}
        
    def charge_battery_with_solar(self, irradiance, in_peak_hours=False):
        """
        Charges the battery with solar energy, ensuring it does not exceed the SoC limits.

        Args:
            irradiance (float): Solar irradiance for the specific hour (kW/m^2).
            in_peak_hours (bool): Whether the charging is occurring during peak hours.
        """
        if irradiance > 0:
            solar_power_kw = irradiance * self.panel_area * self.panel_efficiency
            if in_peak_hours and self.soc < 50:  # Charge to 50% in peak hours
                charge_needed = (50 - self.soc) * self.capacity / 100.0
                charge = min(solar_power_kw, self.charge_rate * self.capacity, charge_needed)
                print(f"Charging battery with solar energy: {charge:.2f} kW")
            elif not in_peak_hours and self.soc < 80:  # Charge to 80% in non-peak hours
                charge_needed = (80 - self.soc) * self.capacity / 100.0
                charge = min(solar_power_kw, self.charge_rate * self.capacity, charge_needed)
                print(f"Charging battery with solar energy: {charge:.2f} kW")
            else:
                charge = 0
                
            self.update_soc((charge / self.capacity) * 100)  # Update SoC with charged energy percentage

    def update_soc(self, change):
        """
        Update the State of Charge (SoC) of the battery.

        Args:
            change (float): The change in SoC percentage (positive for charging, negative for discharging).
        """
        self.soc = max(0, min(100, self.soc + change))  # Ensure SoC stays between 0% and 100%

    @staticmethod
    def calculate_hourly_power(df):
        """
        Calculate the total power consumption for each hour.

        Args:
            df (DataFrame): The profile DataFrame containing appliance data.

        Returns:
            list: List of power consumption values for each hour.
        """
        hourly_power = [0] * 24
        
        for _, row in df.iterrows():
            start_time = int(row['Start'])
            end_time = int(row['End'])
            power = row['Rated Power (kW)']
            
            if start_time < end_time:
                for hour in range(start_time, end_time):
                    hourly_power[hour] += power
            else:
                for hour in range(start_time, 24):
                    hourly_power[hour] += power
                for hour in range(0, end_time):
                    hourly_power[hour] += power
        
        return hourly_power

    @staticmethod
    def update_profile(profile_df, discharge_df):
        """
        Updates the load profile by adding separate virtual appliances for battery discharge.

        Parameters:
        - profile_df: DataFrame containing the load profile of appliances.
        - discharge_df: DataFrame containing battery discharge data (hour, discharge power, and state of charge).

        Returns:
        - Updated profile DataFrame including separate battery discharge rows for each hour in discharge_df.
        """
        print("\nUpdating profile with separate battery appliances...")

        new_rows = []
        for _, row in discharge_df.iterrows():
            hour = int(row["Hour"])
            discharge = row["Discharge (kW)"]

            if discharge > 0:
                # Add a virtual appliance for this specific hour
                battery_appliance_name = f"Battery Discharge (Hour {hour})"
                print(f"  Adding virtual appliance: {battery_appliance_name} with discharge {discharge:.3f} kW")

                new_rows.append({
                    "Name": battery_appliance_name,
                    "Rated Power (kW)": -discharge,  # Negative power to represent discharge
                    "Priority Group": 0,  # Highest priority for processing
                    "Start": hour,  # Active start hour
                    "End": hour + 1  # Active for the specific hour
                })

        # Append new rows to the profile DataFrame
        if new_rows:
            profile_df = pd.concat([profile_df, pd.DataFrame(new_rows)], ignore_index=True)

        print("\nUpdated profile with separate battery discharge appliances:")
        print(profile_df)
        return profile_df