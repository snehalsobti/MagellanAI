import argparse
from bs4 import BeautifulSoup
import os
import pandas as pd
import requests

def load_excluded_courses(file_path):
    df = pd.read_csv(file_path)
    return df['Course Code'].tolist()

def load_dataframe_from_ods(file_path):
    return pd.read_excel(file_path, engine="odf")

# Scrape course description from the UofT website
def scrape_course_description(course_code, prefix_url):
    # Form the URL based on course code
    url = f"{prefix_url}/{course_code.lower()}"
    
    # Send a GET request to fetch the webpage content
    response = requests.get(url)
    
    if response.status_code != 200:
        print(f"Failed to retrieve page for {course_code}")
        return None

    # Parse the HTML content using BeautifulSoup
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find the main content section by looking for the div with the class 'w3-threequarter main-box w3css-content'
    main_content = soup.find('div', class_='w3-threequarter main-box w3css-content')
    if not main_content:
        return None
    
    # Extract course name from the h1 tag with class 'page-title' inside the main content section
    course_name_tag = main_content.find('h1', class_='page-title')
    if course_name_tag:
        course_name = course_name_tag.get_text(strip=True)
    else:
        return None

    url_keys = ['engineering', 'utm']

    # Extract course description from the p tag inside the div with the class 'field--name-body field--type-text-with-summary'
    parent_div_class = ('w3-row field field--name-field-desc field--type-text-long field--label-visually_hidden'
                        if any(url_key in prefix_url for url_key in url_keys) else 'w3-row node__content')
    parent_div = main_content.find('div', class_=parent_div_class)
    if not parent_div:
        return None
    
    description_class = ('w3-bar-item field__item' if any(url_key in prefix_url for url_key in url_keys) else
                        'w3-row field field--name-body field--type-text-with-summary ' +
                        'field--label-hidden w3-bar-item field__item')
    description_div = parent_div.find('div', class_=description_class)
    if description_div:
        description_p = description_div.find('p')
        if description_p:
            description = description_p.get_text(separator="\n").strip()
            return course_name, description
        else:
            return None
    else:
        return None

# Scrape course descriptions and save to .ods
def scrape_and_save_descriptions(input_file, output_file, excluded_courses_file, fix_input_discrepancies=False):
    # Load the course data from the .ods file
    df = load_dataframe_from_ods(input_file)
    
    # Create a list to store the course code, course name, and description
    course_data = []
    course_codes_already_processed = set()

    artsci_url = 'https://artsci.calendar.utoronto.ca/course'
    eng_url = 'https://engineering.calendar.utoronto.ca/course'
    utm_url = 'https://utm.calendar.utoronto.ca/course'
    utsc_url = 'https://utsc.calendar.utoronto.ca/course'
    sgs_url = 'https://sgs.calendar.utoronto.ca/course'

    # There are some old course codes or these courses are not offered
    # And could not find some of the courses in any of the above urls
    # TODO: find if these courses are discontinued at uoft or is there some other reason
    # TODO: we might want to add the new course codes (that replaced old course codes) later
    excluded_course_codes = load_excluded_courses(excluded_courses_file)

    # NOTE: BME412H1 had an inconsistency in its HTML source code
    # So, we manually insert the description in courses_description.ods
    bme412_code = 'BME412H1'
    bme412_name = 'Introduction to Biomolecular Engineering'
    bme412_description = ('Introduces the mechanics and dynamics of the ' +
                        'operation of life at the molecular level by ' + 
                        'teaching how to design new proteins, DNA, and RNA. ' + 
                        'Introduces the fundamentals of biomolecular structure, ' +
                        'function, thermodynamics, and kinetics. ' + 
                        'Covers a broad range of computational and experimental techniques, ' +
                        'including atomistic simulations, bioinformatics, machine learning, ' + 
                        'high-throughput screening, and gene editing.')
    bme412_data_row = {
                "Course Code": bme412_code,
                "Course Name": bme412_name,
                "Description": bme412_description
            }
    
    # Collect indices to drop from df
    rows_to_drop = []
    if fix_input_discrepancies:
        print(f"If any discrepancies are found in {input_file}, they will be fixed in-place")

    for idx, row in df.iterrows():
        course_code = row['Course Code']
        if course_code in course_codes_already_processed:
            continue
        course_codes_already_processed.add(course_code)

        if course_code in excluded_course_codes:
            print(f"Skipping {course_code} (part of excluded course codes)")
            if fix_input_discrepancies:
                rows_to_drop.append(idx)
            continue
        elif course_code == 'BME412H1':
            course_data.append(bme412_data_row)
            continue
        
        if 'H1' in course_code or 'Y1' in course_code:
            course_info = scrape_course_description(course_code, eng_url)
            if not course_info:
                course_info = scrape_course_description(course_code, artsci_url)
        elif 'H3' in course_code:
            course_info = scrape_course_description(course_code, utsc_url)
        elif 'H5' in course_code:
            course_info = scrape_course_description(course_code, utm_url)
        else:
            course_info = scrape_course_description(course_code, sgs_url)

        if course_info:
            course_name, description = course_info
            # course_name has course_code as prefix followed by a non-alphanumeric character and space (8+1+1 = 10 chars)
            course_name = course_name[10:]
            try:
                assert(row['Course Name'] == course_name)
            except:
                print("Discrepancy found:", course_code, row['Course Name'], "----------", course_name)
                if fix_input_discrepancies:
                    df.at[row.name, 'Course Name'] = course_name
            # Append course code, name, and description to the list
            course_data.append({
                "Course Code": course_code,
                "Course Name": course_name,
                "Description": description
            })
        else:
            print(f"Skipping {course_code} (description not found)")
            if fix_input_discrepancies:
                rows_to_drop.append(idx)

    description_df = pd.DataFrame(course_data)

    # Save the descriptions DataFrame to an ODS file using the ODF engine
    description_df.to_excel(output_file, index=False, engine='odf')

    # Modify the input_file if the flag fix_input_discrepancies is True
    if rows_to_drop:
        df.drop(index=rows_to_drop, inplace=True)
    if fix_input_discrepancies:
        df.to_excel(input_file, index=False, engine='odf')
        print(f"Discrepancies fixed in {input_file}")
    print(f"Course descriptions saved to {output_file}")

if __name__ == "__main__":
    # Set base directories
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Root project directory
    DATA_DIR = os.path.join(BASE_DIR, 'data')  # Path to data folder

    INPUT_FILE = os.path.join(DATA_DIR, 'courses_ceab.ods')
    OUTPUT_FILE = os.path.join(DATA_DIR, 'courses_description.ods')
    EXCLUDED_COURSES_FILE = os.path.join(DATA_DIR, 'excluded_course_codes.csv')

    parser = argparse.ArgumentParser(description="Scrape UofT course descriptions.")
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Fix discrepancies in input file and remove missing/excluded courses"
    )
    args = parser.parse_args()
    fix_input_discrepancies = args.fix

    scrape_and_save_descriptions(INPUT_FILE, OUTPUT_FILE, EXCLUDED_COURSES_FILE, fix_input_discrepancies)