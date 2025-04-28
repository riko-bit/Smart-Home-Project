"""
This module provides functionality to read and process electric load data from an Excel file.
It defines the ElectricLoad class, which represents an electric load with attributes such as name, rated power, priority group, and working hours for winter and summer.

Classes:
    ElectricLoad: A class to represent an electric load and provide methods to read data from files.
Methods:
    from_excel(load_profile_file_path): Reads electric load data from an Excel file and returns a list of ElectricLoad instances.

NOTE: THIS CODE ONLY WORKS WITH SPECIFIC FILES THAT CONTAIN THE EXPECTED STRUCTURE.
"""

import pandas as pd

class ElectricLoad:

    @staticmethod
    def from_excel(load_profile_file_path: str):
        """ Reads an Excel file with electric load profiles and returns a clean DataFrame. """
        # Read Excel file and validate columns
        print(f"\nReading Excel file: {load_profile_file_path}")
        df = pd.read_excel(load_profile_file_path)
        print(f"Columns found: {df.columns.tolist()}")

        # Ensure all required columns exist in the dataframe
        required_columns = {'Name', 'Rated Power (kW)', 'Priority Group', 'Winter Hours Start', 'Winter Hours End', 'Summer Hours Start', 'Summer Hours End'}
        if not required_columns.issubset(df.columns):
            raise ValueError(f"Excel file must contain the following columns: {required_columns}")

        # Drop rows with missing essential data
        df = df.dropna(subset=['Name', 'Rated Power (kW)'])
        print(f"Dropped rows with missing 'Name' or 'Rated Power (kW)', remaining rows: {len(df)}")

        # Convert columns to numeric values and handle invalid entries
        print("Converting columns to numeric values...")
        numeric_columns = ['Rated Power (kW)', 'Priority Group', 'Winter Hours Start', 'Winter Hours End', 'Summer Hours Start', 'Summer Hours End']
        df[numeric_columns] = df[numeric_columns].apply(pd.to_numeric, errors='coerce')
        print(f"Converted columns to numeric values. Number of rows with numeric values: {len(df)}")

        # Replace invalid hour values (outside 0-24) with 0
        print("Checking for invalid hour values...")
        invalid_rows = []
        for col in ['Winter Hours Start', 'Winter Hours End', 'Summer Hours Start', 'Summer Hours End']:
            invalid_values = ~df[col].between(0, 24)
            invalid_rows.append(df[invalid_values])
        invalid_df = pd.concat(invalid_rows)
        invalid_df = invalid_df.drop_duplicates()
        if not invalid_df.empty:
            print(f"\nInvalid values found in the following rows:\n{invalid_df}")
            print(f"Replaced invalid hour values with 0. Number of rows replaced: {replaced_count}")
        else:
            print("No invalid hour values found.")
        replaced_count = 0
        for col in ['Winter Hours Start', 'Winter Hours End', 'Summer Hours Start', 'Summer Hours End']:
            invalid_values = ~df[col].between(0, 24)
            replaced_count += invalid_values.sum()
            df[col] = df[col].where(df[col].between(0, 24), 0)

        # Separate DataFrames for winter and summer loads
        winter_load = df[['Name', 'Rated Power (kW)', 'Priority Group', 'Winter Hours Start', 'Winter Hours End']].copy()
        summer_load = df[['Name', 'Rated Power (kW)', 'Priority Group', 'Summer Hours Start', 'Summer Hours End']].copy()

        # Rename columns to 'Start' and 'End'
        winter_load.rename(columns={'Winter Hours Start': 'Start', 'Winter Hours End': 'End'}, inplace=True)
        summer_load.rename(columns={'Summer Hours Start': 'Start', 'Summer Hours End': 'End'}, inplace=True)

        # Replace rows where both 'Start' and 'End' are 0 with NaN
        print("Replacing rows with 'Start' = 0 and 'End' = 0 with NaN and dropping them...")
        winter_load.loc[(winter_load['Start'] == 0) & (winter_load['End'] == 0), ['Start', 'End']] = None
        summer_load.loc[(summer_load['Start'] == 0) & (summer_load['End'] == 0), ['Start', 'End']] = None

        # Drop rows where 'Start' or 'End' is NaN
        initial_winter_count = len(winter_load)
        initial_summer_count = len(summer_load)

        winter_load = winter_load.dropna(subset=['Start', 'End'])
        summer_load = summer_load.dropna(subset=['Start', 'End'])

        dropped_winter = initial_winter_count - len(winter_load)
        dropped_summer = initial_summer_count - len(summer_load)

        print(f"Dropped {dropped_winter} rows from winter load where 'Start' and 'End' are 0.")
        print(f"Dropped {dropped_summer} rows from summer load where 'Start' and 'End' are 0.")

        print(f"\nCleaned Electric Load Data Table:\n{df}")
        print(f"\nWinter Load Data:\n{winter_load}")
        print(f"\nSummer Load Data:\n{summer_load}")

        print("\nElectric Load Data Processing Complete.")
        return winter_load, summer_load