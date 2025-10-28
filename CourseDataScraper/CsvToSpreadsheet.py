import os
import pandas as pd

if __name__ == "__main__":
    # Set base directories
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Root project directory
    DATA_DIR = os.path.join(BASE_DIR, 'data')  # Path to data folder

    COURSES_CSV_FILE = os.path.join(DATA_DIR, 'courses_ceab.csv')
    COURSES_EXCEL_FILE = os.path.join(DATA_DIR, 'courses_ceab.ods')

    df = pd.read_csv(COURSES_CSV_FILE)
    df.to_excel(COURSES_EXCEL_FILE, index=False, engine='odf')

    print(f"Courses data saved to '{COURSES_EXCEL_FILE}'.")