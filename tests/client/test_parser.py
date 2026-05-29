import pytest
import shamla as sh
from unittest.mock import AsyncMock, MagicMock, patch
import time

# ==================== LIVE INTEGRATION TESTS ====================

@pytest.mark.asyncio
async def test_scraper_book_metadata():
    async with sh.Scraper.create_scraper(headless=True) as s:
        # Fetch metadata for book 172 (صحة نقل الإجماع)
        meta = await s.get_book_metadata("172")
        assert meta is not None
        assert meta.title == "صحة نقل الإجماع عند شيخ الإسلام في حرمة الطواف بغير البيت الحرام"
        assert "بسيوني" in meta.author_name
        assert meta.author_page == "https://shamela.ws/author/3074"
        assert meta.volumes == 1
        assert meta.is_equal_to_print is False
        assert "صفحات" in meta.book_description

        # Fetch metadata for book 23627 (تفسير الكشاف)
        meta_kashaf = await s.get_book_metadata("23627")
        assert meta_kashaf is not None
        assert "الكشاف" in meta_kashaf.title
        assert "الزمخشري" in meta_kashaf.author_name
        assert meta_kashaf.author_page == "https://shamela.ws/author/108"
        assert meta_kashaf.volumes == 4
        assert meta_kashaf.is_equal_to_print is True
        assert "الانتصاف" in meta_kashaf.book_description

@pytest.mark.asyncio
async def test_scraper_book_toc():
    async with sh.Scraper.create_scraper(headless=True) as s:
        toc = await s.get_book_toc("23627")
        assert toc is not None
        assert len(toc) > 0
        
        # Check first chapter details
        first_chap = toc[0]
        assert first_chap.title == "مقدمة التفسير للعلامة الزمخشري"
        assert first_chap.page_number == 1
        assert first_chap.depth == 0
        
        # Check second chapter details
        second_chap = toc[1]
        assert second_chap.title == "الجزء الأول"
        assert second_chap.page_number == 5
        assert second_chap.depth == 0
        
        # Check nested sub-chapter
        third_chap = toc[2]
        assert third_chap.title == "سورة فاتحة الكتاب"
        assert third_chap.page_number == 5
        assert third_chap.depth == 1

@pytest.mark.asyncio
async def test_scraper_book_page():
    async with sh.Scraper.create_scraper(headless=True) as s:
        # Fetch page 5 of book 23627 (الكشاف)
        page = await s.get_book_page("23627", 5)
        assert page is not None
        assert page.book_id == "23627"
        assert page.page_number == 5
        assert page.part_number == "الجزء الأول"
        
        # Headings check
        assert "[الجزء الأول]" in page.headings
        assert "[سورة فاتحة الكتاب]" in page.headings
        
        # Paragraphs check
        assert len(page.paragraphs) > 0
        assert any("مكية" in p for p in page.paragraphs)
        assert any("بِسْمِ اللَّهِ الرَّحْمنِ الرَّحِيمِ" in p for p in page.paragraphs)
        
        # Footnotes check
        assert len(page.footnotes) == 1
        fn = page.footnotes[0]
        assert fn.number in ["١", "1"]
        assert "موقوف" in fn.content
        
        # Citations check
        assert len(page.citations) > 0
        assert any("مائة وأربع عشرة آية" in c for c in page.citations)

# ==================== MOCK / UNIT TESTS FOR 100% COVERAGE ====================

def test_find_browser_executable_mock():
    from shamla.client.scraper import find_browser_executable
    
    # 1. Test finding via shutil.which
    with patch("shutil.which", return_value="/usr/bin/google-chrome"):
        assert find_browser_executable() == "/usr/bin/google-chrome"
        
    # 2. Test fallback to None when everything is missing
    with patch("shutil.which", return_value=None), \
         patch("os.path.exists", return_value=False):
        assert find_browser_executable() is None

    # 3. Test alternative chrome folder in playwright
    with patch("shutil.which", return_value=None), \
         patch("os.path.exists", return_value=True), \
         patch("glob.glob", side_effect=[[], ["/path/to/chrome2"]]):
        assert find_browser_executable() == "/path/to/chrome2"

    # 4. Test first chrome folder in playwright (covers line 28)
    with patch("shutil.which", return_value=None), \
         patch("os.path.exists", return_value=True), \
         patch("glob.glob", side_effect=[["/path/to/chrome1"], []]):
        assert find_browser_executable() == "/path/to/chrome1"

@pytest.mark.asyncio
async def test_network_wait_for_selector_timeout_and_exceptions():
    from shamla.client.scraper import Network
    
    # Create a mock browser and network instance
    mock_browser = MagicMock()
    net = Network(mock_browser, verbose=True)
    
    # Mock page query_selector to always return None
    mock_page = AsyncMock()
    mock_page.query_selector.return_value = None
    
    # Test wait_for_selector timeout
    with pytest.raises(TimeoutError):
        await net.wait_for_selector(mock_page, ".non-existent", timeout=0.1, checking_interval=0.01)

    # Mock page query_selector to raise Exception (covers lines 62-64)
    mock_page.query_selector.side_effect = Exception("Mocked browser error")
    with pytest.raises(TimeoutError):
        await net.wait_for_selector(mock_page, ".non-existent", timeout=0.1, checking_interval=0.01)

@pytest.mark.asyncio
async def test_network_get_retries_fail():
    from shamla.client.scraper import Network
    
    mock_browser = AsyncMock()
    mock_page = AsyncMock()
    mock_browser.get.return_value = mock_page
    
    net = Network(mock_browser, verbose=True)
    
    # Mock wait_for_selector to raise TimeoutError
    with patch.object(net, "wait_for_selector", side_effect=TimeoutError("timeout")):
        with pytest.raises(TimeoutError):
            await net.get("https://example.com", wait_for=".selector", timeout=0.1, retries=2)
            
        # Verify get was called 2 times due to retries=2
        assert mock_browser.get.call_count == 2

def test_scraper_normalize_url():
    from shamla.client.scraper import Scraper
    s = Scraper(MagicMock())
    
    # ID only
    assert s._normalize_url("123") == ("https://shamela.ws/book/123", "123")
    
    # Full URL
    assert s._normalize_url("https://shamela.ws/book/456") == ("https://shamela.ws/book/456", "456")
    
    # Invalid/no id
    assert s._normalize_url("https://example.com/other") == ("https://example.com/other", "")

@pytest.mark.asyncio
async def test_scraper_get_book_page_value_error():
    from shamla.client.scraper import Scraper
    s = Scraper(MagicMock())
    
    with pytest.raises(ValueError, match="Could not extract book ID"):
        await s.get_book_page("https://example.com/other", 1)

@pytest.mark.asyncio
async def test_scraper_dunder_context_manager():
    from shamla.client.scraper import Scraper
    mock_network = AsyncMock()
    s = Scraper(mock_network)
    async with s as entered_s:
        assert entered_s == s
    mock_network.browser.stop.assert_called_once()
    
    with pytest.raises(ValueError, match="Could not extract book ID"):
        await s.get_book_page("https://example.com/other", 1)

def test_parse_book_html_missing_div():
    from shamla.client.parser import parse_book_html
    with pytest.raises(ValueError, match="Could not find book metadata container"):
        parse_book_html("<html><body>No metadata here</body></html>")

def test_parse_book_html_eastern_digits_and_comments():
    from shamla.client.parser import parse_book_html
    
    html = """
    <div class="nass margin-top-10">
        <h3>بطاقة الكتاب</h3>
        الكتاب: كتاب تجريبي<br/>
        المؤلف: مؤلف تجريبي<br/>
        <b>نص داخل وسم bold لتغطية السطر ٤٦</b><br/>
        عدد الأجزاء: ٥<br/>
        الناشر: دار النشر<br/>
        الطبعة: الأولى<br/>
        بطاقة الكتاب وفهرس الموضوعات<br/>
        تعليق إضافي
        <div>صفحة المؤلف: [<a href="https://shamela.ws/author/99">مؤلف</a>]</div>
    </div>
    """
    book = parse_book_html(html)
    assert book.title == "كتاب تجريبي"
    assert book.author_name == "مؤلف تجريبي"
    assert book.volumes == 5
    assert book.publisher == "دار النشر"
    assert book.book_print == "الأولى"
    assert book.is_equal_to_print is False
    assert book.author_page == "https://shamela.ws/author/99"
    assert "نص داخل وسم bold" in book.book_description
    assert "تعليق إضافي" in book.book_description

def test_parse_toc_empty_and_nested():
    from shamla.client.parser import parse_toc
    
    # Empty cases
    assert parse_toc("<html></html>") == []
    assert parse_toc('<div class="betaka-index">No ul here</div>') == []
    
    # Nested TOC case
    html = """
    <div class="betaka-index">
        <ul>
            <li>
                <a href="https://shamela.ws/book/123/1">الفصل الأول</a>
                <ul>
                    <li>
                        <a href="https://shamela.ws/book/123/2">المبحث الأول</a>
                    </li>
                </ul>
            </li>
        </ul>
    </div>
    """
    chaps = parse_toc(html)
    assert len(chaps) == 2
    assert chaps[0].title == "الفصل الأول"
    assert chaps[0].depth == 0
    assert chaps[0].page_number == 1
    assert chaps[1].title == "المبحث الأول"
    assert chaps[1].depth == 1
    assert chaps[1].page_number == 2

def test_parse_book_page_special_cases():
    from shamla.client.parser import parse_book_page
    
    # Page with title-based part parsing, non-standard footnotes, and citation deduplication/filtering
    html = """
    <html>
        <head><title>الجزء العاشر - كتاب تجريبي</title></head>
        <body>
            <p><span class="anchor" id="p1"></span>نص عادي مع اقتباس «اقتباس مكرر» واقتباس «اقتباس مكرر»<a class="btn_tag">نسخ</a></p>
            <p><span class="anchor" id="p2"></span><span class="c4">العنوان</span> نص إضافي بجانب العنوان لتغطية السطر ٢٠٣</p>
            <p><span class="anchor" id="p3"></span><span class="c2">«اقتباس مكرر»</span></p>
            <p><span class="anchor" id="p4"></span><span class="c2">١٢٣</span></p>
            <p class="hamesh">هذا هامش غير قياسي بلا رقم</p>
        </body>
    </html>
    """
    page = parse_book_page(html, "123", 1)
    assert page.part_number == "الجزء العاشر"
    assert len(page.footnotes) == 1
    assert page.footnotes[0].number == ""
    assert page.footnotes[0].content == "هذا هامش غير قياسي بلا رقم"
    
    # Check deduplicated citations
    assert "اقتباس مكرر" in page.citations
    assert len(page.citations) == 1  # Only "اقتباس مكرر" should remain, "١٢٣" and duplicate "اقتباس مكرر" are removed!
    assert any("نص إضافي بجانب العنوان" in p for p in page.paragraphs)

def test_parse_book_page_customizable_citations():
    from shamla.client.parser import parse_book_page
    import re
    
    html = """
    <html>
        <body>
            <p><span class="anchor" id="p1"></span>ألا ليت الشباب يعود يوماً ... فأخبره بما فعل المشيب</p>
            <p><span class="anchor" id="p2"></span>بيت شعر آخر مع أربع نقط .... عجز بيت شعر</p>
            <p><span class="anchor" id="p3"></span>نص عادي لا يحتوي على النقط</p>
            <p>نص عادي بدون وسم مرساة لتغطية السطر ١٩٤</p>
        </body>
    </html>
    """
    
    # 1. Test using regular expressions (both string and compiled pattern)
    # poetry_pattern matches text separated by ... or .... (has groups)
    # second pattern matches a word pattern (no groups) to cover line 229-230
    poetry_pattern = r'([^\n\.\s][^\n\.]*[^\n\.\s])\s*(?:\.\.\.+)\s*([^\n\.\s][^\n\.]*[^\n\.\s])'
    simple_pattern = r'نص\s+\w+'
    
    page = parse_book_page(html, "123", 1, citation_patterns=[poetry_pattern, simple_pattern])
    assert len(page.citations) == 3
    assert "ألا ليت الشباب يعود يوماً ... فأخبره بما فعل المشيب" in page.citations
    assert "بيت شعر آخر مع أربع نقط ... عجز بيت شعر" in page.citations
    assert "نص عادي" in page.citations

    # 2. Test using custom extractor callback
    def custom_poetry_extractor(text: str) -> list[str]:
        if "..." in text:
            halves = text.split("...")
            return [f"صدر: {halves[0].strip()} | عجز: {halves[1].strip()}"]
        return []
        
    page2 = parse_book_page(html, "123", 1, custom_extractor=custom_poetry_extractor)
    assert len(page2.citations) == 2
    assert "صدر: ألا ليت الشباب يعود يوماً | عجز: فأخبره بما فعل المشيب" in page2.citations

    # 3. Test exception handling in custom extractor (covers lines 236-237)
    def failing_extractor(text: str) -> list[str]:
        raise ValueError("Error in extractor")
        
    page3 = parse_book_page(html, "123", 1, custom_extractor=failing_extractor)
    assert len(page3.citations) == 0  # No citations, but doesn't crash!


def test_extraction_registry():
    from shamla.extraction.registry import global_registry, register_department, department, load_extractors_from_file
    import tempfile
    import os
    import re
    
    # Reset registry
    global_registry.clear()
    
    # 1. Register department directly (using compiled pattern to cover line 33 of registry.py)
    compiled_pattern = re.compile(r'([a-zA-Z]+)\s*\.\.\.\s*([a-zA-Z]+)')
    register_department("poetry", patterns=[compiled_pattern])
    depts = global_registry.get_departments()
    assert "poetry" in depts
    assert len(depts["poetry"].patterns) == 1
    
    # Invalid name
    with pytest.raises(ValueError, match="Department name cannot be empty"):
        register_department("")
        
    # 2. Register department via decorator
    @department("sayings")
    def my_sayings_extractor(text: str) -> list[str]:
        return ["saying: " + text]
        
    depts = global_registry.get_departments()
    assert "sayings" in depts
    assert depts["sayings"].extractor is my_sayings_extractor
    
    # 2b. Register short/digits/failing department extractors (to cover lines 300, 302 of parser.py)
    @department("short_and_digits")
    def short_and_digits_extractor(text: str) -> list[str]:
        return ["ab", "123", "valid_cit"]

    @department("failing")
    def failing_dept_callback(text: str) -> list[str]:
        raise ValueError("error inside callback")
    
    # 3. Test load_extractors_from_file
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as tmp:
        tmp.write("""import shamla as sh
sh.register_department("loaded_dept", patterns=[r'loaded'])
""")
        tmp_name = tmp.name
        
    try:
        load_extractors_from_file(tmp_name)
        assert "loaded_dept" in global_registry.get_departments()
    finally:
        os.remove(tmp_name)
        
    # File not found error
    with pytest.raises(FileNotFoundError):
        load_extractors_from_file("non_existent_file_path_12345.py")
        
    # Mock spec_from_file_location returning None
    with patch("importlib.util.spec_from_file_location", return_value=None):
        with pytest.raises(ImportError):
            load_extractors_from_file(os.devnull)

    # 4. Test parse_book_page with registry departments
    from shamla.client.parser import parse_book_page
    
    html = """
    <html>
        <body>
            <p><span class="anchor" id="p1"></span>hello ... world</p>
            <p><span class="anchor" id="p2"></span>this has loaded word</p>
        </body>
    </html>
    """
    
    # 4a. Run all registered departments (default)
    page = parse_book_page(html, "123", 1)
    assert "poetry" in page.departments
    assert "hello ... world" in page.departments["poetry"]
    assert "loaded_dept" in page.departments
    assert "short_and_digits" in page.departments
    assert "valid_cit" in page.departments["short_and_digits"]
    assert "ab" not in page.departments["short_and_digits"]
    assert "123" not in page.departments["short_and_digits"]
    assert "hello ... world" in page.citations
    
    # 4b. Run ONLY a subset of departments
    page2 = parse_book_page(html, "123", 1, departments=["poetry"])
    assert "poetry" in page2.departments
    assert "loaded_dept" not in page2.departments
    
    # Clean up
    global_registry.clear()

def test_parse_book_page_diacritics():
    from shamla.client.parser import parse_book_page
    
    html = """
    <html>
        <head><title>الجزء الأول - كتاب</title></head>
        <body>
            <p><span class="anchor" id="p1"></span><span class="c4">تَفْسِيرٌ</span></p>
            <p><span class="anchor" id="p2"></span>كِتَابٌ جَمِيلٌ ... فِيهِ عِلْمٌ</p>
            <p class="hamesh">١ هَذَا هَامِشٌ</p>
        </body>
    </html>
    """
    
    # 1. ignore_diacritics = False (default behavior)
    page_default = parse_book_page(html, "123", 1, departments=[])
    assert "تَفْسِيرٌ" in page_default.headings
    assert "كِتَابٌ جَمِيلٌ ... فِيهِ عِلْمٌ" in page_default.paragraphs
    assert page_default.footnotes[0].content == "هَذَا هَامِشٌ"

    # 2. ignore_diacritics = True, keep_diacritics_in_paragraphs = False
    poetry_pattern = r'([^\n\.\…\s][^\n\.\…]*[^\n\.\…\s])\s*(?:\.\.\.+|\…)\s*([^\n\.\…\s][^\n\.\…]*[^\n\.\…\s])'
    page_clean = parse_book_page(
        html, 
        "123", 
        1, 
        citation_patterns=[poetry_pattern], 
        departments=[], 
        ignore_diacritics=True,
        keep_diacritics_in_paragraphs=False
    )
    assert "تفسير" in page_clean.headings
    assert "كتاب جميل ... فيه علم" in page_clean.paragraphs
    assert "كتاب جميل ... فيه علم" in page_clean.citations
    assert page_clean.footnotes[0].content == "هذا هامش"

    # 3. ignore_diacritics = True, keep_diacritics_in_paragraphs = True
    page_keep = parse_book_page(
        html, 
        "123", 
        1, 
        citation_patterns=[poetry_pattern], 
        departments=[], 
        ignore_diacritics=True,
        keep_diacritics_in_paragraphs=True
    )
    assert "تفسير" in page_keep.headings
    # Paragraph and footnotes keep diacritics
    assert "كِتَابٌ جَمِيلٌ ... فِيهِ عِلْمٌ" in page_keep.paragraphs
    assert page_keep.footnotes[0].content == "هَذَا هَامِشٌ"
    # Citations (matched/checked quotes) do NOT keep diacritics
    assert "كتاب جميل ... فيه علم" in page_keep.citations

