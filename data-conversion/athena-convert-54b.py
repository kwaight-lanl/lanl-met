import argparse
import csv
import sys


def convert_format(input_file_path, output_file_path):
    # Define the exact columns for the new format
    new_headers = [
        "TA54B_15_ID",
        "DTS",
        "DOY",
        "SPD1",
        "DIR1",
        "SDDIR1",
        "SDSPD1",
        "W1",
        "SDW1",
        "TEMP0",
        "TEMP1",
        "CREATED_ON",
        "CREATED_BY",
        "UPD_ON",
        "UPD_BY",
        "PLACEHOLDER_FLAG",
        "MXGSTTODAY",
        "RH",
        "DEWP",
        "FM10HR",
        "MNTEMPTODAY",
        "MXTEMPTODAY",
    ]

    # Specific mappings requested: { old_column: new_column }
    custom_mappings = {
        "HWDIR1_STDDEV": "SDDIR1",
        "HWSPD1_MS_STDDEV": "SDSPD1",
    }

    try:
        with open(
            input_file_path, mode="r", newline="", encoding="utf-8"
        ) as infile:
            # Read the old file format
            reader = csv.DictReader(infile)
            old_headers = reader.fieldnames

            if not old_headers:
                print(
                    f"Error: Input file '{input_file_path}' is empty or does not have headers."
                )
                sys.exit(1)

            # Verify that our expected mapping source columns exist
            for old_col in custom_mappings:
                if old_col not in old_headers:
                    print(
                        f"Warning: Expected column '{old_col}' not found in the old format file."
                    )

            output_rows = []
            for row in reader:
                new_row = {}
                for col in new_headers:
                    if col in row:
                        # Case 1: Column has the exact same name in both files
                        new_row[col] = row[col]
                    elif col in custom_mappings.values():
                        # Case 2: Column is mapped specifically from a differently named column
                        source_col = [
                            old
                            for old, new in custom_mappings.items()
                            if new == col
                        ][0]
                        new_row[col] = row.get(source_col, "")
                    else:
                        # Case 3: Column is new and doesn't exist in the old format (set to blank)
                        new_row[col] = ""

                output_rows.append(new_row)

        # Write the mapped dataset to the new file format
        with open(
            output_file_path, mode="w", newline="", encoding="utf-8"
        ) as outfile:
            writer = csv.DictWriter(outfile, fieldnames=new_headers)
            writer.writeheader()
            writer.writerows(output_rows)

        print(f"Successfully converted {len(output_rows)} rows.")
        print(f"Output saved to: {output_file_path}")

    except FileNotFoundError:
        print(f"Error: The input file '{input_file_path}' was not found.")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)


def main():
    # Set up the argument parser
    parser = argparse.ArgumentParser(
        description="Convert weather data files from the old format to the new format."
    )

    # Add required positional arguments
    parser.add_argument(
        "input_file",
        help="Path to the input file in the old format (e.g., ta54b_15_athena_01012026.txt)",
    )
    parser.add_argument(
        "output_file",
        help="Path where the converted file should be saved (e.g., ta54b_15_athena_07222026.txt)",
    )

    # Parse arguments from the command line
    args = parser.parse_args()

    # Call the conversion logic
    convert_format(args.input_file, args.output_file)


if __name__ == "__main__":
    main()
