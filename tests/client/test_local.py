import pytest
import os
import shutil
import tempfile
import urllib.error
from unittest.mock import MagicMock, patch
import shamla as sh

# Mock HTML content for testing downloader and local scraper
MOCK_INDEX_HTML = """
<div class="nass margin-top-10">
    <h3>بطاقة الكتاب</h3>
    الكتاب: كتاب تجريبي محلي<br/>
    المؤلف: مؤلف محلي<br/>
    عدد الأجزاء: ١<br/>
    الناشر: دار النشر المحلي<br/>
    الطبعة: الأولى<br/>
    بطاقة الكتاب وفهرس الموضوعات
</div>
<div class="betaka-index">
    <ul>
        <li>
            <a href="https://shamela.ws/book/123/1">الفصل الأول</a>
        </li>
    </ul>
</div>
"""

MOCK_PAGE_1_HTML = """
<html>
    <head><title>الجزء الأول - كتاب تجريبي محلي</title></head>
    <body>
        <p><span class="anchor" id="p1"></span>نص الصفحة الأولى</p>
    </body>
</html>
"""

def make_mock_response(html: str | bytes, url: str) -> MagicMock:
    mock = MagicMock()
    mock.__enter__.return_value = mock
    mock.read.return_value = html.encode("utf-8") if isinstance(html, str) else html
    mock.geturl.return_value = url
    return mock

@pytest.mark.asyncio
async def test_book_downloader_and_local_scraper():
    # Create a temporary directory for local downloads
    temp_base_dir = tempfile.mkdtemp()
    
    try:
        # Initialize Downloader (with positive delay to cover line 60 of downloader.py)
        downloader = sh.BookDownloader(base_dir=temp_base_dir, delay=0.01)
        
        # 1. Test downloading with successful pages
        mock_resp_meta = make_mock_response(MOCK_INDEX_HTML, "https://shamela.ws/book/123")
        mock_resp_page1 = make_mock_response(MOCK_PAGE_1_HTML, "https://shamela.ws/book/123/1")
        mock_resp_page2 = make_mock_response(b"", "https://shamela.ws/book/123")

        with patch("urllib.request.urlopen", side_effect=[mock_resp_meta, mock_resp_page1, mock_resp_page2]):
            progress_calls = []
            def callback(stage, page):
                progress_calls.append((stage, page))
                
            await downloader.download_book("123", progress_callback=callback)
            
            # Assert correct progress calls
            assert ("metadata", 0) in progress_calls
            assert ("page", 1) in progress_calls
            assert ("page", 2) in progress_calls

        # Check local files are created
        assert os.path.exists(os.path.join(temp_base_dir, "123", "metadata.html"))
        assert os.path.exists(os.path.join(temp_base_dir, "123", "pages", "1.html"))
        assert not os.path.exists(os.path.join(temp_base_dir, "123", "pages", "2.html"))

        # 2. Verify LocalScraper offline reading capabilities
        async with sh.LocalScraper(base_dir=temp_base_dir) as scraper:
            # Metadata parsing (use full URL to cover line 24 of local_scraper.py)
            meta = await scraper.get_book_metadata("https://shamela.ws/book/123")
            assert meta.title == "كتاب تجريبي محلي"
            assert meta.author_name == "مؤلف محلي"
            
            # TOC parsing
            toc = await scraper.get_book_toc("https://shamela.ws/book/123")
            assert len(toc) == 1
            assert toc[0].title == "الفصل الأول"
            
            # Page parsing
            page = await scraper.get_book_page("https://shamela.ws/book/123", 1)
            assert page.page_number == 1
            assert page.book_id == "123"
            assert "نص الصفحة الأولى" in page.paragraphs

            # API Compatibility check: closing does nothing
            await scraper.close()

        # 3. Test edge case errors
        scraper = sh.LocalScraper(base_dir=temp_base_dir)
        
        # Invalid book ID/URLs
        with pytest.raises(ValueError, match="Could not extract book ID"):
            await scraper.get_book_metadata("invalid_url")
        with pytest.raises(ValueError, match="Could not extract book ID"):
            await scraper.get_book_toc("invalid_url")
        with pytest.raises(ValueError, match="Could not extract book ID"):
            await scraper.get_book_page("invalid_url", 1)

        # Missing files handling
        with pytest.raises(FileNotFoundError):
            await scraper.get_book_metadata("999")
        with pytest.raises(FileNotFoundError):
            await scraper.get_book_toc("999")
        with pytest.raises(FileNotFoundError):
            await scraper.get_book_page("123", 999)

    finally:
        shutil.rmtree(temp_base_dir)

@pytest.mark.asyncio
async def test_downloader_http_errors_and_invalid_id():
    temp_base_dir = tempfile.mkdtemp()
    try:
        downloader = sh.BookDownloader(base_dir=temp_base_dir, delay=0.0)

        # Case 1: Invalid Book ID (redirects on metadata page download)
        mock_resp_meta = make_mock_response(b"", "https://shamela.ws/book/redirected_invalid")
        with patch("urllib.request.urlopen", return_value=mock_resp_meta):
            with pytest.raises(RuntimeError, match="Invalid book ID"):
                await downloader.download_book("invalid_id")

        # Case 2: Metadata page fetch returns error
        with patch("urllib.request.urlopen", side_effect=urllib.error.HTTPError("url", 500, "Internal Error", {}, None)):
            with pytest.raises(RuntimeError, match="Failed to download book index page"):
                await downloader.download_book("invalid_id")

        # Case 3: Page loop HTTP 404
        mock_resp_meta2 = make_mock_response(MOCK_INDEX_HTML, "https://shamela.ws/book/123")
        http_404_err = urllib.error.HTTPError("url", 404, "Not Found", {}, None)
        
        with patch("urllib.request.urlopen", side_effect=[mock_resp_meta2, http_404_err]):
            # Should exit page loop cleanly without error on 404
            await downloader.download_book("123")

        # Case 4: Page loop HTTP 500 triggers max failure count limit
        mock_resp_meta3 = make_mock_response(MOCK_INDEX_HTML, "https://shamela.ws/book/123")
        http_500_err = urllib.error.HTTPError("url", 500, "Error", {}, None)
        
        with patch("urllib.request.urlopen", side_effect=[mock_resp_meta3, http_500_err, http_500_err, http_500_err]):
            # Should exit page loop after 3 consecutive failures
            await downloader.download_book("123")

        # Case 5: Max pages limit
        mock_resp_meta4 = make_mock_response(MOCK_INDEX_HTML, "https://shamela.ws/book/123")
        mock_resp_page = make_mock_response(MOCK_PAGE_1_HTML, "https://shamela.ws/book/123/1")

        with patch("urllib.request.urlopen", side_effect=[mock_resp_meta4, mock_resp_page]):
            # Download only 1 page max
            await downloader.download_book("123", max_pages=1)

        # Case 6: Page content without anchor (triggers break on line 76 of downloader.py)
        mock_resp_meta5 = make_mock_response(MOCK_INDEX_HTML, "https://shamela.ws/book/123")
        mock_resp_page_no_anchor = make_mock_response("<html><body>No anchor here</body></html>", "https://shamela.ws/book/123/1")
        with patch("urllib.request.urlopen", side_effect=[mock_resp_meta5, mock_resp_page_no_anchor]):
            await downloader.download_book("123")

        # Case 7: Non-HTTPError exception in page loop (triggers lines 89-92 of downloader.py)
        mock_resp_meta6 = make_mock_response(MOCK_INDEX_HTML, "https://shamela.ws/book/123")
        with patch("urllib.request.urlopen", side_effect=[mock_resp_meta6, RuntimeError("generic error"), RuntimeError("generic error"), RuntimeError("generic error")]):
            await downloader.download_book("123")

    finally:
        shutil.rmtree(temp_base_dir)

@pytest.mark.asyncio
async def test_downloader_concurrency():
    temp_base_dir = tempfile.mkdtemp()
    try:
        downloader = sh.BookDownloader(base_dir=temp_base_dir, concurrency=3, delay=0.01)

        # Success case: metadata + page 1, 2, 3 + page 4 returns 404 (end of book)
        mock_resp_meta = make_mock_response(MOCK_INDEX_HTML, "https://shamela.ws/book/123")
        mock_resp_page1 = make_mock_response(MOCK_PAGE_1_HTML, "https://shamela.ws/book/123/1")
        mock_resp_page2 = make_mock_response(MOCK_PAGE_1_HTML, "https://shamela.ws/book/123/2")
        mock_resp_page3 = make_mock_response(MOCK_PAGE_1_HTML, "https://shamela.ws/book/123/3")
        mock_resp_page4 = urllib.error.HTTPError("url", 404, "Not Found", {}, None)

        with patch("urllib.request.urlopen", side_effect=[
            mock_resp_meta,
            mock_resp_page1, mock_resp_page2, mock_resp_page3,
            mock_resp_page4, mock_resp_page4, mock_resp_page4
        ]):
            await downloader.download_book("123", max_pages=10)

        # Verify pages 1, 2, 3 are downloaded
        assert os.path.exists(os.path.join(temp_base_dir, "123", "pages", "1.html"))
        assert os.path.exists(os.path.join(temp_base_dir, "123", "pages", "2.html"))
        assert os.path.exists(os.path.join(temp_base_dir, "123", "pages", "3.html"))
        assert not os.path.exists(os.path.join(temp_base_dir, "123", "pages", "4.html"))

    finally:
        shutil.rmtree(temp_base_dir)
