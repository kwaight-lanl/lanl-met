import argparse
import csv

def convert_format(input_file_path, output_file_path):
    # Mapping for old format columns to new format columns
    # 'New Column Name': 'Old Column Name'
    column_mapping = {
        'TA54B_24_ID': 'TA54B_24_ID',
        'DTS': 'DTS',
        'DOY': 'DOY',
        'MXGST1': 'MXGST1',
        'DIRGST1': 'DIRGST1',
        'MX1GST': 'MX1GST',
        'MXTEMP': 'MXTEMP',
        'TMXTEMP': 'TMXTEMP',
        'MNTEMP': 'MNTEMP',
        'TMNTEMP': 'TMNTEMP',
        'CREATED_ON': 'CREATED_ON',
        'CREATED_BY': 'CREATED_BY',
        'UPD_ON': 'UPD_ON',
        'UPD_BY': 'UPD_BY',
        'PLACEHOLDER_FLAG': 'PLACEHOLDER_FLAG',
        'DIR1GST': 'MX1DIR'  # Explicitly mapped from old format MX1DIR
    }

    # Desired header structure and column order for the new format
    new_headers = [
        'TA54B_24_ID', 'DTS', 'DOY', 'MXGST1', 'DIRGST1', 'MX1GST', 
        'MXTEMP', 'TMXTEMP', 'MNTEMP', 'TMNTEMP', 'CREATED_ON', 
        'CREATED_BY', 'UPD_ON', 'UPD_BY', 'PLACEHOLDER_FLAG', 
        'AVGSPD1', 'TGST1', 'DIR1GST', 'T1GST', 'AVGRH', 'MXRH', 
        'MNRH', 'AVGDEWP', 'MXDEWP', 'MNDEWP'
    ]

    with open(input_file_path, mode='r', newline='', encoding='utf-8') as infile:
        reader = csv.DictReader(infile)
        
        with open(output_file_path, mode='w', newline='', encoding='utf-8') as outfile:
            writer = csv.DictWriter(outfile, fieldnames=new_headers)
            writer.writeheader()

            for row in reader:
                new_row = {}
                for new_header in new_headers:
                    # Check if the field maps to an existing old field
                    if new_header in column_mapping:
                        old_field = column_mapping[new_header]
                        new_row[new_header] = row.get(old_field, '')
                    else:
                        # Fields in the new format but not in the old format are left blank
                        new_row[new_header] = ''
                
                writer.writerow(new_row)

def main():
    parser = argparse.ArgumentParser(
        description="Convert LANL TA54B 24hr weather data from old format to new format."
    )
    parser.add_argument("input_file_path", help="Path to the input file in old format.")
    parser.add_argument("output_file_path", help="Path to the output file in new format.")

    args = parser.parse_args()
    convert_format(args.input_file_path, args.output_file_path)

if __name__ == "__main__":
    main()
