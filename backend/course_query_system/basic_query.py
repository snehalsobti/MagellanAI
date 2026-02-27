# backend/course_query_system/basic_query.py

import argparse
from backend.data_bridge.factory import get_catalog_bridge
from backend.data_bridge.interfaces import CatalogBridge


def find_courses_by_keyword(bridge: CatalogBridge, keyword: str, top_n: int = 5):
    rows = bridge.search_courses(keyword, limit=top_n)
    return [(r.course_code, r.name or "", 100.0) for r in rows]


def filter_courses_by_attribute(bridge: CatalogBridge, attribute: str, threshold: float):
    attr_map = {
        "Math": {"min_math": threshold},
        "NS": {"min_ns": threshold},
        "CS": {"min_cs": threshold},
        "ES": {"min_es": threshold},
        "ED": {"min_ed": threshold},
    }
    if attribute not in attr_map:
        raise ValueError(f"Unsupported CEAB attribute: {attribute}")
    return bridge.filter_courses(**attr_map[attribute], limit=500)


def get_course_details(bridge: CatalogBridge, course_code: str, term: str | None = None):
    if term:
        return bridge.get_course_offering(course_code, term)
    # Fall back to first matching offering.
    rows = bridge.search_courses(course_code, limit=50)
    for row in rows:
        if row.course_code == course_code:
            return bridge.get_course_offering(course_code, row.term)
    return None


def filter_courses_by_term(bridge: CatalogBridge, term: str):
    return bridge.filter_courses(term=term.upper(), limit=500)


def load_course_details_index(data_path: str | None = None, bridge: CatalogBridge | None = None):
    del data_path  # no longer used; retained for backward compatibility
    if bridge is None:
        bridge = get_catalog_bridge()
    return bridge.get_course_name_index()

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
    bridge = get_catalog_bridge()

    # Execute the corresponding function based on the user's command
    if args.command == 'search':
        results = find_courses_by_keyword(bridge, args.keyword, args.top_n)
        for result in results:
            print(f"Course Code: {result[0]}, Course Name: {result[1]}, Score: {result[2]}")

    elif args.command == 'filter_attribute':
        filtered_courses = filter_courses_by_attribute(bridge, args.attribute, args.threshold)
        print(filtered_courses)

    elif args.command == 'details':
        course_details = get_course_details(bridge, args.course_code)
        if course_details:
            print(course_details)
        else:
            print(f"No details found for course code {args.course_code}")

    elif args.command == 'filter_term':
        filtered_courses = filter_courses_by_term(bridge, args.term)
        print(filtered_courses)

    else:
        parser.print_help()

if __name__ == "__main__":
    handleCLI()
