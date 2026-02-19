from __future__ import annotations

def _calendar_prefixes_for_code(course_code: str) -> list[str]:
    code = course_code.upper()
    artsci_url = "https://artsci.calendar.utoronto.ca/course"
    eng_url = "https://engineering.calendar.utoronto.ca/course"
    utm_url = "https://utm.calendar.utoronto.ca/course"
    utsc_url = "https://utsc.calendar.utoronto.ca/course"
    sgs_url = "https://sgs.calendar.utoronto.ca/course"

    if "H1" in code or "Y1" in code:
        return [eng_url, artsci_url]
    if "H3" in code:
        return [utsc_url]
    if "H5" in code:
        return [utm_url]
    return [sgs_url]


def _scrape_from_prefix(course_code: str, prefix_url: str) -> tuple[str | None, str | None]:
    try:
        import requests
        from bs4 import BeautifulSoup  # type: ignore[import-not-found]
    except Exception:
        return None, None

    url = f"{prefix_url}/{course_code.lower()}"
    try:
        response = requests.get(url, timeout=15)
    except Exception:
        return None, None
    if response.status_code != 200:
        return None, None

    soup = BeautifulSoup(response.text, "html.parser")
    main_content = soup.find("div", class_="w3-threequarter main-box w3css-content")
    if not main_content:
        return None, None

    course_name_tag = main_content.find("h1", class_="page-title")
    if not course_name_tag:
        return None, None

    raw_name = course_name_tag.get_text(strip=True)
    # UofT pages generally render "ECE318H1: Name", strip the prefix if present.
    course_name = raw_name[10:] if len(raw_name) > 10 else raw_name

    url_keys = ["engineering", "utm"]
    parent_div_class = (
        "w3-row field field--name-field-desc field--type-text-long field--label-visually_hidden"
        if any(url_key in prefix_url for url_key in url_keys)
        else "w3-row node__content"
    )
    parent_div = main_content.find("div", class_=parent_div_class)
    if not parent_div:
        return course_name, None

    description_class = (
        "w3-bar-item field__item"
        if any(url_key in prefix_url for url_key in url_keys)
        else "w3-row field field--name-body field--type-text-with-summary field--label-hidden w3-bar-item field__item"
    )
    description_div = parent_div.find("div", class_=description_class)
    if not description_div:
        return course_name, None

    description_p = description_div.find("p")
    if not description_p:
        return course_name, None

    description = description_p.get_text(separator="\n").strip()
    return course_name, description


def scrape_course_name_and_description(course_code: str) -> tuple[str | None, str | None]:
    for prefix in _calendar_prefixes_for_code(course_code):
        name, description = _scrape_from_prefix(course_code, prefix)
        if name or description:
            return name, description
    return None, None

