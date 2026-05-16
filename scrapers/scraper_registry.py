from typing import List

from scrapers.base_scraper import BaseScraper
from scrapers.kaufland_scraper import KauflandScraper
from scrapers.linella_scraper import LinellaScraper
from scrapers.magazine_scraper import MagazineScraper


def get_scrapers(settings) -> List[BaseScraper]:
    scrapers: List[BaseScraper] = [KauflandScraper(settings)]
    if settings.enable_linella:
        scrapers.append(LinellaScraper(settings))
    if settings.enable_magazine:
        scrapers.append(MagazineScraper(settings))
    return scrapers
