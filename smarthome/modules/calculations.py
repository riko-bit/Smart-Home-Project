"""
This module provides utility methods for managing and optimizing energy usage 
in a load profile system for residential or commercial settings. It includes 
functions to update the load profile based on battery discharge, shift loads 
from peak to off-peak hours to reduce energy costs, and calculate total energy 
costs based on different tariff rates for peak, mid-peak, and off-peak periods.

Classes:
    - Calculations: A class containing static methods for updating load profiles,
      shifting loads, and calculating energy costs.
Methods:
    - update_profile(profile_df, battery_discharge_profile): Updates the load profile
    - shift_loads(profile_df, threshold, peak_hours): Shifts loads within peak hours
    - calculate_energy_cost(profile_df, peak_hours): Calculates the energy cost

Constants:
    - PEAK_START: The start hour for peak pricing (17:00).
    - PEAK_END: The end hour for peak pricing (22:00).
    - OFF_PEAK_TARIFF: The tariff rate for off-peak hours.
    - MID_PEAK_TARIFF: The tariff rate for mid-peak hours (6:00 - 17:00).
    - PEAK_TARIFF: The tariff rate for peak hours (17:00 - 22:00).
"""

import pandas as pd


class Calculations:
    
    @staticmethod
    def shift_loads(profile_df, threshold, peak_hours):
        """
        Shifts loads to reduce errors in each peak hour, starting with the highest-priority loads
        that are contributing to excess load during each peak hour.

        Parameters:
        - profile_df: DataFrame containing the load profile of appliances.
        - threshold: Maximum allowable load in any hour to prevent overloading the grid.
        - peak_hours: List of hours considered as peak hours.

        Returns:
        - Updated profile DataFrame with adjusted load timings.
        """
        print("\nShifting Loads...")

        PEAK_START = 17
        PEAK_END = 22

        # Initialize a dictionary to track the summed load for each peak hour
        peak_hour_loads = {hour: 0 for hour in peak_hours}
        
        # Dictionary to track which appliances have been shifted
        shifted_appliances = {}

        # Function to calculate the total load for a specific peak hour
        def calculate_total_load_for_hour(hour, load_profile):
            total_load = sum(load['Rated Power (kW)'] for load in load_profile if load['Start'] <= hour < load['End'])
            total_load = round(total_load, 3)
            print(f"Summed load for hour {hour}: {total_load} kW")
            return total_load

        # Sort appliances by their priority group (highest priority first)
        sorted_profile = profile_df.sort_values(by="Priority Group", ascending=False)
        print(sorted_profile)

        # Iterate over each peak hour to check the load and shift appliances if necessary
        for hour in peak_hours:
            print(f"\nProcessing peak hour: {hour}")

            # Calculate the total load for the current peak hour
            peak_hour_loads[hour] = calculate_total_load_for_hour(hour, profile_df.to_dict(orient='records'))

            # If the load exceeds the threshold, we need to shift some appliances
            excess_load = peak_hour_loads[hour] - threshold
            if excess_load <= 0:
                print(f"No excess load detected: {excess_load} kW. Skipping appliances...")
                continue  # Skip the shifting for this hour, as the load is within limits
            else:
                print(f"Excess load detected: {excess_load} kW. Shifting appliances...")

                # Identify appliances that are contributing to the excess load
                appliances_to_shift = []
                for index, row in sorted_profile.iterrows():
                    name = row["Name"]
                    start, end = row["Start"], row["End"]
                    rated_power = row["Rated Power (kW)"]
                    priority = row["Priority Group"]
                    
                    # Skip appliances with priority 1
                    if priority in [1]: 
                        continue

                    # Skip zero-power loads, battery discharges, or appliances that run all day
                    if rated_power == 0 or "Battery Discharge" in name or (start == 0 and end == 24):
                        continue

                    # Only consider appliances that are running during the current peak hour
                    if start <= hour < end: 
                        appliances_to_shift.append((index, name, rated_power))

                # Sort appliances by their contribution to the excess load (highest first)
                appliances_to_shift = sorted(appliances_to_shift, key=lambda x: x[2], reverse=True)

                # Shift appliances that contribute most to the excess load
                for index, name, rated_power in appliances_to_shift:
                    # Skip if this appliance has already been shifted
                    if name in shifted_appliances:
                        continue

                    # Calculate new times for shifting the appliance
                    shift_start = (PEAK_END + 1) % 24  # Move to the next hour after the peak
                    shift_end = (shift_start + (int(profile_df.at[index, "End"]) - int(profile_df.at[index, "Start"]))) % 24

                    # Update the profile with the new start and end times
                    print(f"  Shifting appliance '{name}' from ({profile_df.at[index, 'Start']}, {profile_df.at[index, 'End']}) to ({shift_start}, {shift_end})")
                    profile_df.at[index, "Start"] = shift_start
                    profile_df.at[index, "End"] = shift_end

                    # Mark this appliance as shifted
                    shifted_appliances[name] = True

                    # Recalculate peak hour loads after shifting the appliance
                    peak_hour_loads[hour] = calculate_total_load_for_hour(hour, profile_df.to_dict(orient='records'))

                    # Break if the load is now below threshold after shifting
                    if peak_hour_loads[hour] <= threshold:
                        print(f"Load for hour {hour} is now within the threshold: {peak_hour_loads[hour]} kW. Stopping further shifts.")
                        break

        print(f"\nShifted Load Profile:\n{profile_df}")
        print("Load shifting completed.")
        return profile_df

    @staticmethod
    def calculate_energy_cost(hourly_df, peak_hours):
        """
        Calculate the energy cost based on consumption during peak, mid-peak, and off-peak hours.
        
        Parameters:
        - profile_df: DataFrame containing the hourly load profile of appliances.
        - peak_hours: List of hours considered peak hours (e.g., 17:00 to 22:00).
        
        Returns:
        - Total energy cost calculated based on consumption during peak, mid-peak, and off-peak hours.
        """
        print(f"\nCalculating energy cost...")

        OFF_PEAK_TARIFF = 0.1
        MID_PEAK_TARIFF = 0.2
        PEAK_TARIFF = 0.3

        # Initialize the total cost
        total_cost = 0

        # Loop through each hour to calculate the cost based on the tariff
        for hour in range(24):
            consumption = hourly_df.loc[hour, "Power (kW)"]
            if hour in peak_hours:
                cost = consumption * PEAK_TARIFF
                print(f"Hour {hour}: Peak rate {PEAK_TARIFF} -> Cost: {round(cost, 2)}")
                total_cost += cost
            elif 6 <= hour < 17:
                cost = consumption * MID_PEAK_TARIFF
                print(f"Hour {hour}: Mid-peak rate {MID_PEAK_TARIFF} -> Cost: {round(cost, 2)}")
                total_cost += cost
            else:
                cost = consumption * OFF_PEAK_TARIFF
                print(f"Hour {hour}: Off-peak rate {OFF_PEAK_TARIFF} -> Cost: {round(cost, 2)}")
                total_cost += cost

        # Round total cost for better readability
        total_cost = round(total_cost, 2)
        print(f"\nTotal Energy Cost: {total_cost}")

        print("Energy cost calculation completed.")
        return total_cost