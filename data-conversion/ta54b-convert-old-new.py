import csv
from datetime import datetime

def standardize_datetime(dt_str):
    """
    Parses various datetime formats and converts them to 'YYYY-MM-DD HH:MM'
    """
    dt_str = dt_str.strip()
    
    # List of possible formats we expect from the source files
    formats = [
        "%m/%d/%y %H:%M",   # e.g., "1/1/25 0:00" or "01/01/25 00:00"
        "%Y-%m-%d %H:%M",   # e.g., "2026-07-14 00:00"
        "%m/%d/%Y %H:%M",   # e.g., "1/1/2025 0:00"
    ]
    
    for fmt in formats:
        try:
            dt_obj = datetime.strptime(dt_str, fmt)
            return dt_obj.strftime("%Y-%m-%d %H:%M")
        except ValueError:
            continue
            
    # If no formats match, return the original string untouched as a fallback
    return dt_str

def convert_weather_data(input_path, output_path):
    # Define the complete target schema (union of both formats minus exclusions)
    target_schema = [
        ("datetime", "yyyy-mm-dd hh:mi"),
        ("doy", "ddd"),
        ("spd1", "m/s"),
        ("spdcsat", "m/s"),
        ("spd81000", "m/s"),
        ("sdspd1", "m/s"),
        ("dir1", "deg"),
        ("dircsat", "degrees"),
        ("dir81000", "deg"),
        ("sddir1", "deg"),
        ("w1", "m/s"),
        ("wcsat", "m/s"),
        ("w81000", "m/s"),
        ("sdw1", "m/s"),
        ("sdwcsat", "m/s"),
        ("sdw81000", "m/s"),
        ("temp0", "deg-c"),
        ("temp1", "deg-c"),
        ("rh", "%"),
        ("dewp", "deg-c"),
        ("fm10hr", "%")
    ]

    target_headers = [item[0] for item in target_schema]
    target_units = [item[1] for item in target_schema]

    with open(input_path, mode='r', newline='', encoding='utf-8') as infile:
        reader = csv.reader(infile)
        
        # Read and clean the first line (headers)
        headers = [h.strip().replace('"', '').lower() for h in next(reader)]
        
        # Read and clean the second line (units)
        units = [u.strip().replace('"', '') for u in next(reader)]
        
        # Read the data rows
        data_rows = list(reader)

    output_rows = []
    for row in data_rows:
        if not row:
            continue
        
        # Strip whitespaces and quotes from raw row elements
        row = [val.strip().replace('"', '') for val in row]
        
        # Map current row's headers to its raw values
        row_dict = dict(zip(headers, row))
        
        new_row = []
        for idx, field in enumerate(target_headers):
            # Special Case: Standardize Datetime format
            if field == "datetime":
                raw_dt = row_dict.get("datetime") or row[0]
                new_row.append(standardize_datetime(raw_dt))
                continue

            val = row_dict.get(field, None)
            
            if val is None or val == "":
                # Insert asterisk for missing fields
                new_row.append("*")
            else:
                # Attempt to parse numerical values so they lose their quotes in the output CSV
                try:
                    if '.' in val:
                        new_row.append(float(val))
                    else:
                        new_row.append(int(val))
                except ValueError:
                    # Fallback to string if it cannot be converted to a number
                    new_row.append(val)
                    
        output_rows.append(new_row)

    # Write out the new file
    with open(output_path, mode='w', newline='', encoding='utf-8') as outfile:
        # csv.QUOTE_NONNUMERIC wraps strings (like datetime and "*") in quotes 
        # and leaves parsed numeric values unquoted.
        writer = csv.writer(outfile, quoting=csv.QUOTE_NONNUMERIC)
        
        # Write headers and units (both are text, so they will be quoted)
        writer.writerow(target_headers)
        writer.writerow(target_units)
        
        # Write the processed data rows
        writer.writerows(output_rows)

if __name__ == "__main__":
    input_file = "ta54b-15-20250101.csv"
    output_file = "ta54b-15-merged_output.csv"
    convert_weather_data(input_file, output_file)
