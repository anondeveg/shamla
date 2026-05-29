import re
from typing import Callable, Union
from bs4 import BeautifulSoup
from shamla.models.book import Book_data
from shamla.models.chapter import Chapter
from shamla.models.page import Footnote, Page_data

def to_western_digits(text: str) -> str:
    """Normalize Arabic-Indic numerals to standard western digits."""
    eastern_to_western = {
        '٠': '0', '١': '1', '٢': '2', '٣': '3', '٤': '4',
        '٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9'
    }
    return "".join(eastern_to_western.get(c, c) for c in text)

DIACRITICS_PATTERN = re.compile(r'[\u064B-\u0652\u0670]')

def remove_diacritics(text: str) -> str:
    """Remove Arabic diacritics (tashkeel/harakat) from text."""
    return DIACRITICS_PATTERN.sub('', text)

def parse_book_html(html: str) -> Book_data:
    """Parse book metadata from the book details HTML page."""
    soup = BeautifulSoup(html, "html.parser")
    div = soup.find("div", class_="nass margin-top-10")
    if not div:
        raise ValueError("Could not find book metadata container")
    
    # 1. Extract author link page URL
    author_page = ""
    author_link = div.find("a", href=lambda h: h and "/author/" in h)
    if author_link:
        author_page = author_link["href"]

    # 2. Extract raw lines from description block, filtering UI elements and sub-sections
    lines = []
    current_line = []
    for child in div.children:
        if child.name == "div":
            # stop when we reach the nested div for author page / search buttons
            break
        if child.name == "br":
            line_str = "".join(current_line).strip()
            if line_str:
                lines.append(line_str)
            current_line = []
        elif isinstance(child, str):
            current_line.append(child)
        elif child.name == "h3":
            # Skip the main header of the betaka card
            pass
        else:
            current_line.append(child.text)
    
    line_str = "".join(current_line).strip()
    if line_str:
        lines.append(line_str)

    # 3. Parse known keys from lines
    title = ""
    author_name = ""
    publisher = ""
    book_print = ""
    volumes = 1
    is_equal_to_print = False
    description_lines = []

    for line in lines:
        if line.startswith("الكتاب:"):
            title = line[len("الكتاب:"):].strip()
        elif line.startswith("المؤلف:"):
            author_name = line[len("المؤلف:"):].strip()
        elif line.startswith("الناشر:"):
            publisher = line[len("الناشر:"):].strip()
        elif line.startswith("الطبعة:"):
            book_print = line[len("الطبعة:"):].strip()
        elif line.startswith("عدد الأجزاء:"):
            vol_str = line[len("عدد الأجزاء:"):].strip()
            vol_str = to_western_digits(vol_str)
            match = re.search(r'\d+', vol_str)
            if match:
                volumes = int(match.group())
        elif "[ترقيم الكتاب موافق للمطبوع]" in line:
            is_equal_to_print = True
        elif line == "بطاقة الكتاب وفهرس الموضوعات":
            pass
        else:
            description_lines.append(line)
    
    book_description = "\n".join(description_lines).strip()

    return Book_data(
        author_name=author_name,
        author_page=author_page,
        title=title,
        book_description=book_description,
        publisher=publisher,
        book_print=book_print,
        volumes=volumes,
        is_equal_to_print=is_equal_to_print
    )

def parse_toc(html: str) -> list[Chapter]:
    """Parse nested TOC list structure from the book details page HTML."""
    soup = BeautifulSoup(html, "html.parser")
    betaka = soup.find("div", class_="betaka-index")
    if not betaka:
        return []
    
    root_ul = betaka.find("ul")
    if not root_ul:
        return []
        
    chapters = []
    
    def parse_ul(ul, depth=0):
        for li in ul.find_all("li", recursive=False):
            # Find the first valid link with non-toggle text inside this list item
            a_tag = None
            for a in li.find_all("a", href=True):
                href = a["href"]
                text = a.text.strip()
                if "/book/" in href and text and text not in ["+", "-", "[+]", "[-]"]:
                    a_tag = a
                    break
            
            if a_tag:
                title = a_tag.text.strip()
                href = a_tag["href"]
                # Extract page number: e.g. /book/23627/5 or /book/23627/5#p1
                match = re.search(r'/book/\d+/(\d+)', href)
                page_number = int(match.group(1)) if match else 0
                
                chapters.append(Chapter(
                    title=title,
                    url=href,
                    page_number=page_number,
                    depth=depth
                ))
            
            # Recurse into nested lists
            nested_ul = li.find("ul", recursive=False)
            if nested_ul:
                parse_ul(nested_ul, depth + 1)
                
    parse_ul(root_ul, depth=0)
    return chapters

def parse_book_page(
    html: str,
    book_id: str,
    page_number: int,
    citation_patterns: list[Union[str, re.Pattern]] | None = None,
    custom_extractor: Callable[[str], list[str]] | None = None,
    departments: list[str] | None = None,
    ignore_diacritics: bool = False,
    keep_diacritics_in_paragraphs: bool = False
) -> Page_data:
    """Parse page headings, paragraphs, footnotes, and citations from book page HTML."""
    soup = BeautifulSoup(html, "html.parser")
    
    # 1. Parse part number (الجزء)
    part_number = ""
    path_heading = soup.find(string=lambda t: t and "مسار الصفحة الحالية" in t)
    if path_heading:
        parent = path_heading.parent
        links = parent.find_all_next("a", href=True)
        for a in links:
            txt = a.text.strip()
            if "الجزء" in txt:
                part_number = txt
                break
    
    if not part_number:
        title_text = soup.title.text if soup.title else ""
        match = re.search(r'الجزء\s+[\u0621-\u064A]+', title_text)
        if match:
            part_number = match.group()

    # 2. Extract contents
    headings = []
    paragraphs = []
    footnotes = []
    raw_citations = []

    # Get active departments from the global registry
    from shamla.extraction.registry import global_registry
    registered_depts = global_registry.get_departments()
    active_depts = {}
    if departments is not None:
        for dept_name in departments:
            if dept_name in registered_depts:
                active_depts[dept_name] = registered_depts[dept_name]
    else:
        # Default to running all registered departments
        active_depts = registered_depts.copy()

    # Track department-specific raw citations
    raw_dept_citations = {name: [] for name in active_depts}

    p_tags = soup.find_all("p")
    for p in p_tags:
        # Check if footnote
        if p.get("class") and "hamesh" in p.get("class"):
            txt = p.text.strip()
            # Split footnote number and description
            match = re.match(r'^\(?([0-9\u0660-\u0669a-zA-Z]+)\)?\s*[\-\.]?\s*(.*)', txt)
            if match:
                num = match.group(1)
                content = match.group(2)
                if ignore_diacritics and not keep_diacritics_in_paragraphs:
                    content = remove_diacritics(content)
                footnotes.append(Footnote(number=num, content=content))
            else:
                if ignore_diacritics and not keep_diacritics_in_paragraphs:
                    txt = remove_diacritics(txt)
                footnotes.append(Footnote(number="", content=txt))
            continue
        
        # Paragraph must have anchor to be part of the page content
        if not p.find("span", class_="anchor"):
            continue

        # Clean copy buttons and anchors
        for btn in p.find_all("a", class_="btn_tag"):
            btn.decompose()
        for span in p.find_all("span", class_="anchor"):
            span.decompose()

        p_text_raw = p.text.strip()
        p_text_clean = remove_diacritics(p_text_raw) if ignore_diacritics else p_text_raw
        p_text_to_check = p_text_clean
        p_text_to_save = p_text_raw if (ignore_diacritics and keep_diacritics_in_paragraphs) else p_text_clean

        # Check for headings (class c4)
        c4_spans = p.find_all("span", class_="c4")
        if c4_spans:
            for span in c4_spans:
                h_text = span.text.strip()
                if ignore_diacritics:
                    h_text = remove_diacritics(h_text)
                headings.append(h_text)
            
            # If paragraph contains other text outside of the headings, keep it
            if p_text_to_check and p_text_to_check not in [f"[{h}]" for h in headings] and p_text_to_check not in headings:
                paragraphs.append(p_text_to_save)
        else:
            if p_text_to_check:
                paragraphs.append(p_text_to_save)

        # Custom or default extraction
        if citation_patterns or custom_extractor:
            if citation_patterns:
                for pattern in citation_patterns:
                    pat = re.compile(pattern) if isinstance(pattern, str) else pattern
                    matches = pat.findall(p_text_to_check)
                    for m in matches:
                        if isinstance(m, tuple):
                            joined = " ... ".join(x.strip() for x in m if x.strip())
                            if joined:
                                raw_citations.append(joined)
                        else:
                            if m.strip():
                                raw_citations.append(m.strip())
            if custom_extractor:
                try:
                    custom_cits = custom_extractor(p_text_to_check)
                    if custom_cits:
                        raw_citations.extend(custom_cits)
                except Exception:
                    pass
        else:
            # Collect citations/quotes (class c2)
            c2_spans = p.find_all("span", class_="c2")
            for span in c2_spans:
                c_text = span.text.strip()
                if ignore_diacritics:
                    c_text = remove_diacritics(c_text)
                # Clean up quote brackets if present in span
                c_text = re.sub(r'^[«»\(\)\[\]]+|[«»\(\)\[\]]+$', '', c_text).strip()
                if c_text:
                    raw_citations.append(c_text)
            
            # Also extract quoted phrases «...» in text
            quotes = re.findall(r'«([^»]+)»', p_text_to_check)
            for quote in quotes:
                q_text = quote.strip()
                if q_text:
                    raw_citations.append(q_text)

        # Process registered departments on paragraph text
        for dept_name, dept in active_depts.items():
            if dept.patterns:
                for pattern in dept.patterns:
                    matches = pattern.findall(p_text_to_check)
                    for m in matches:
                        if isinstance(m, tuple):
                            joined = " ... ".join(x.strip() for x in m if x.strip())
                            if joined:
                                raw_dept_citations[dept_name].append(joined)
                        else:
                            if m.strip():
                                raw_dept_citations[dept_name].append(m.strip())
            if dept.extractor:
                try:
                    custom_cits = dept.extractor(p_text_to_check)
                    if custom_cits:
                        raw_dept_citations[dept_name].extend(custom_cits)
                except Exception:
                    pass

    # Clean and deduplicate department-specific citations, and add them to main flat list
    departments_data = {}
    for dept_name, raw_cits in raw_dept_citations.items():
        cleaned_cits = []
        seen_dept = set()
        for cit in raw_cits:
            if len(cit) <= 2:
                continue
            if re.match(r'^[0-9\u0660-\u0669\s\-\.\,\:\(\)\[\]]+$', cit):
                continue
            if cit not in seen_dept:
                seen_dept.add(cit)
                cleaned_cits.append(cit)
        departments_data[dept_name] = cleaned_cits
        raw_citations.extend(cleaned_cits)

    # 3. Clean and deduplicate flat citations
    citations = []
    seen = set()
    for cit in raw_citations:
        # Ignore very short citations, or those consisting only of punctuation/digits/numbers
        if len(cit) <= 2:
            continue
        if re.match(r'^[0-9\u0660-\u0669\s\-\.\,\:\(\)\[\]]+$', cit):
            continue
        if cit not in seen:
            seen.add(cit)
            citations.append(cit)

    return Page_data(
        book_id=book_id,
        page_number=page_number,
        part_number=part_number,
        headings=headings,
        paragraphs=paragraphs,
        footnotes=footnotes,
        citations=citations,
        departments=departments_data
    )
