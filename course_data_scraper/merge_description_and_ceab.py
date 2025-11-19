import pandas as pd
import os
import sys

def load_ods(file_path):
    return pd.read_excel(file_path, engine='odf')

def safe_merge_ods(file1, file2, output_file):
    df1 = load_ods(file1)
    df2 = load_ods(file2)

    codes1 = set(df1['Course Code'])
    codes2 = set(df2['Course Code'])

    missing_in_file1 = codes2 - codes1
    missing_in_file2 = codes1 - codes2

    if missing_in_file1 or missing_in_file2:
        print("Merge failed: Course Codes mismatch between files.")
        if missing_in_file1:
            print("These codes are in file2 but missing in file1:", missing_in_file1)
        if missing_in_file2:
            print("These codes are in file1 but missing in file2:", missing_in_file2)
        print('Please run "python3 ScrapeAndStore.py --fix" before running this file again.')
        sys.exit(1)

    # Check Course Name consistency for common Course Codes
    merged_check = pd.merge(df1[['Course Code', 'Course Name']],
                            df2[['Course Code', 'Course Name']],
                            on='Course Code',
                            suffixes=('_1', '_2'))

    inconsistent_names = merged_check[merged_check['Course Name_1'] != merged_check['Course Name_2']]
    if not inconsistent_names.empty:
        print("Merge failed: Course Name mismatch for some Course Codes.")
        print(inconsistent_names[['Course Code', 'Course Name_1', 'Course Name_2']])
        print('Please run "python3 ScrapeAndStore.py --fix" before running this file again.')
        sys.exit(1)

    merged_df = pd.merge(df1, df2.drop(columns='Course Name'), on='Course Code', how='inner')

    merged_df.to_excel(output_file, index=False, engine='odf')
    print(f"Merged file saved to {output_file}")

if __name__ == "__main__":
    # Set base directories
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Root project directory
    DATA_DIR = os.path.join(BASE_DIR, 'data')  # Path to data folder

    FILE1 = os.path.join(DATA_DIR, 'courses_ceab.ods')
    FILE2 = os.path.join(DATA_DIR, 'courses_description.ods')
    OUTPUT_FILE = os.path.join(DATA_DIR, 'courses.ods')

    safe_merge_ods(FILE1, FILE2, OUTPUT_FILE)
