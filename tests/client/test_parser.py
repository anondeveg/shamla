import shamla.client.scraper as S
import pytest


@pytest.mark.asyncio
async def test_get_book():
    async with S.Scraper.create_scraper() as s:
        page = await s.get_book("https://shamela.ws/book/23627")
        assert "الكشاف"


