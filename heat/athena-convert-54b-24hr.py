#!/usr/bin/env python3
"""
athena-convert-54b-24hr.py
Read an old historical csv file of 24 hr data for TA54B and run
  the conversion program to read it and rewrite the data in a
  new historical format.
To run: python3 athena-convert-54b-24hr.py old-hist-file new-hist-file
Joulix and Ken Waight/ July 2026
"""

import csv
import argparse

def convert_weather_format(input_path, output_path):
    # Define the exact headers for the new format
    new_headers = [
        "TA54B_24_ID", "DTS", "DOY", "MXGST1", "DIRGST1", "MX1GST", "MXTEMP", 
        "TMXTEMP", "MNTEMP", "TMNTEMP", "CREATED_ON", "CREATED_BY", "UPD_ON", 
        "UPD_BY", "PLACEHOLDER_FLAG", "AVGSPD1", "TGST1", "DIR1GST", "T1GST", 
        "AVGRH", "MXRH", "MNRH", "AVGDEWP", "MXDEWP", "MNDEWP"
    ]

    try:
        with open(input_path, mode='r', newline='', encoding='utf-8') as infile:
            reader = csv.DictReader(infile)
            
            # Check if input file is empty or missing headers
            if not reader.fieldnames:
                raise ValueError("Input file is empty or has invalid headers.")

            # Identify overlapping headers between old and new format
            overlapping_headers = [header for header in new_headers if header in reader.fieldnames]

            rows_to_write = []
            for row in reader:
                new_row = {}
                for header in new_headers:
                    if header in overlapping_headers:
                        # Copy the value if the column exists in the old format
                        new_row[header] = row[header]
                    else:
                        # Leave blank if it's a new column not present in the old format
                        new_row[header] = ""
                rows_to_write.append(new_row)

        with open(output_path, mode='w', newline='', encoding='utf-8') as outfile:
            writer = csv.DictWriter(outfile, fieldnames=new_headers)
            writer.writeheader()
            writer.writerows(rows_to_write)

        print(f"Successfully converted data and wrote to: {output_path}")

    except FileNotFoundError:
        print(f"Error: The input file '{input_path}' was not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert historical TA54B 24-hour weather data from the old format to the new format."
    )
    
    # Positional arguments (no flags like -i or -o required)
    parser.add_argument(
        "input_file_path", 
        help="Path to the input file in the old format (e.g., ta54b_24_athena_01012026.txt)"
    )
    parser.add_argument(
        "output_file_path", 
        help="Path where the converted file should be saved (e.g., ta54b_24_athena_07222026.txt)"
    )

    args = parser.parse_args()
    convert_weather_format(args.input_file_path, args.output_file_path)
