import argparse
import pandas as pd
from rapidfuzz import fuzz, process
import os

def load_dataset(file_path):
    data = pd.read_excel(file_path, engine='odf')
    return data

# Search courses by keyword
def find_courses_by_keyword(data, keyword, top_n=5):
    name_and_descriptions = data['Course Name'] + ' ' + data['Description']
    results = process.extract(keyword, name_and_descriptions, scorer=fuzz.partial_ratio, limit=top_n)
    return [(data.loc[i[2]]['Course Code'], data.loc[i[2]]['Course Name'], i[1]) for i in results]

# Filter courses by CEAB attribute
def filter_courses_by_attribute(data, attribute, threshold):
    return data[data[attribute] > threshold][['Course Code', 'Course Name', attribute]]

# Get course details
def get_course_details(data, course_code):
    course = data[data['Course Code'] == course_code]
    if not course.empty:
        return course.iloc[0].to_dict()
    return None

# Filter courses by term
def filter_courses_by_term(data, term):
    return data[data['Term'] == term][['Course Code', 'Course Name', 'Term']]

# Handle CLI
def handleCLI():
    parser = argparse.ArgumentParser(description="Course Search and Filtering System")
    subparsers = parser.add_subparsers(dest='command')

    # Subcommand for searching courses by keyword
    keyword_parser = subparsers.add_parser('search', help="Search courses by keyword")
    keyword_parser.add_argument('keyword', type=str, help="The keyword to search for")
    keyword_parser.add_argument('--top_n', type=int, default=5, help="Number of top results to return")

    # Subcommand for filtering courses by attribute
    attribute_parser = subparsers.add_parser('filter_attribute', help="Filter courses by CEAB attribute")
    attribute_parser.add_argument('attribute', type=str, help="The CEAB attribute to filter by")
    attribute_parser.add_argument('threshold', type=float, help="The threshold value for the attribute")

    # Subcommand for getting course details
    details_parser = subparsers.add_parser('details', help="Get details of a course by its code")
    details_parser.add_argument('course_code', type=str, help="The course code to retrieve details for")

    # Subcommand for filtering courses by term
    term_parser = subparsers.add_parser('filter_term', help="Filter courses by term")
    term_parser.add_argument('term', type=str, help="The term (e.g., 'F' for Fall) to filter courses by")

    args = parser.parse_args()

    # Set base directories
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Root project directory
    DATA_DIR = os.path.join(BASE_DIR, 'data')  # Path to data folder
    file_path = os.path.join(DATA_DIR, 'courses.ods')
    dataset = load_dataset(file_path)
    no_duplicates_dataset = dataset.drop_duplicates(subset='Course Code')

    # Execute the corresponding function based on the user's command
    if args.command == 'search':
        results = find_courses_by_keyword(no_duplicates_dataset, args.keyword, args.top_n)
        for result in results:
            print(f"Course Code: {result[0]}, Course Name: {result[1]}, Score: {result[2]}")

    elif args.command == 'filter_attribute':
        filtered_courses = filter_courses_by_attribute(no_duplicates_dataset, args.attribute, args.threshold)
        print(filtered_courses)

    elif args.command == 'details':
        course_details = get_course_details(dataset, args.course_code)
        if course_details:
            print(course_details)
        else:
            print(f"No details found for course code {args.course_code}")

    elif args.command == 'filter_term':
        filtered_courses = filter_courses_by_term(dataset, args.term)
        print(filtered_courses)

    else:
        parser.print_help()

if __name__ == "__main__":
    handleCLI()
