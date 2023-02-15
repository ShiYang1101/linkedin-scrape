import selenium
from bs4 import BeautifulSoup as bs


def get_title(soup):
    title_elem = soup.find_all(class_='t-24 t-bold jobs-unified-top-card__job-title')
    assert len(title_elem) == 1, "More than 1 job title found on page!"

    title = title_elem[0].contents[0]
    assert isinstance(title, str)

    return title