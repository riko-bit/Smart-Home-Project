"""
This module provides functionality to read and process meteorological data from Excel and CSV files.
It calculates solar irradiance per hour and average solar irradiation for winter and summer months.

Classes:
    MeteorologicalData: A class to represent meteorological data and provide methods to read data from files.
Methods:
    from_excel(meteorological_file_path): Reads meteorological data from an Excel file and returns a list of MeteorologicalData instances.
    from_csv(meteorological_file_path): Reads meteorological data from a CSV file and returns a list of MeteorologicalData instances.

NOTE: THIS CODE ONLY WORKS WITH SPECICIF FILES. ITS COMPATIBLE WITH CSV METEOROLOGY FILES FROM: https://re.jrc.ec.europa.eu/pvg_tools/en/#TMY
"""

import pandas as pd

class MeteorologicalData:

    def from_csv(meteorological_file_path: str):
        """ Reads a CSV file with meteorological data and returns a DataFrame with hourly average solar irradiance for both winter and summer seasons. """
        # Read CSV file and validate columns
        print(f"\nReading CSV file: {meteorological_file_path}")
        df = pd.read_csv(meteorological_file_path, skiprows=10, low_memory=False, on_bad_lines='warn')  
        print(f"Columns found in the CSV file: {df.columns.tolist()}")

        # Ensure all required columns exist in the dataframe
        required_columns = {'time', 'H_sun'}  
        if not required_columns.issubset(df.columns):
            raise ValueError(f"CSV file must contain the following columns: {required_columns}")

        # Drop rows with invalid 'time' values
        df = df.dropna(subset=['time'])  
        print(f"Dropped rows with invalid 'time', remaining rows: {len(df)}")
        
        # Convert 'time' column to datetime for easier manipulation
        print("Converting 'time' column to datetime format...")
        df['time'] = pd.to_datetime(df['time'], format='%Y%m%d:%H%M', errors='coerce')  
        print(f"Time conversion complete. Number of rows with 'time': {df['time'].notna().sum()}")

        # Extract hour, day, month
        df['hour'] = df['time'].dt.hour
        df['day'] = df['time'].dt.day
        df['month'] = df['time'].dt.month
        print("Extracted hour, day, and month from 'time' column.")

        # Define winter and summer months
        winter_months = [12, 1, 2]
        summer_months = [6, 7, 8]

        # Filter data for winter and summer months
        winter_data = df[df['month'].isin(winter_months)]
        summer_data = df[df['month'].isin(summer_months)]
        print(f"Filtered winter data: {len(winter_data)} rows, summer data: {len(summer_data)} rows.")

        # Convert 'H_sun' to numeric
        df['H_sun'] = pd.to_numeric(df['H_sun'], errors='coerce')
        print("Converted 'H_sun' to numeric.")

        # Calculate average solar irradiation per hour for winter and summer months
        winter_irradiation_avg = winter_data.groupby('hour')['H_sun'].mean().to_dict()
        summer_irradiation_avg = summer_data.groupby('hour')['H_sun'].mean().to_dict()

        # Create DataFrames for both winter and summer irradiation averages
        winter_df = pd.DataFrame(list(winter_irradiation_avg.items()), columns=['Hour', 'Irradiation (kW/m^2)'])
        summer_df = pd.DataFrame(list(summer_irradiation_avg.items()), columns=['Hour', 'Irradiation (kW/m^2)'])

        print(f"\nWinter Profile:\n{winter_df.head(24)}")
        print(f"\nSummer Profile:\n{summer_df.head(24)}")
        
        print("\nMeteorological Data Processing Complete.")
        return winter_df, summer_df