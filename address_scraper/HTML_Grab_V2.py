import requests
from bs4 import BeautifulSoup
import csv

from dotenv import find_dotenv, load_dotenv
import os
from pathlib import Path

load_dotenv(find_dotenv())

GDRIVE_FOLDER = Path(os.getenv("GDRIVE_FOLDER"))


def get_list_of_urls_to_scrape(county: str = "Camden") -> list:
    """
    function tests if URL with different page number (up to 10) is valid, then adds valid pages to url_list
    """
    url_list = []

    urlbase = "https://visitsouthjersey.com/page/"
    urlsuffix = f"/?post_type=member_org&member_org_categories=attractions&features%5Bcounty%5D={county}&features%5Bcity%5D"

    # could probably do a while loop here, for while response is 200, but need to work on that.
    for page in range(1, 10):
        new_url = f"{urlbase}{page}{urlsuffix}"
        if str(requests.get(new_url)) == "<Response [200]>":
            url_list.append(new_url)

    return url_list


output_filepath = GDRIVE_FOLDER / "list_of_locations2.csv"


if __name__ == "__main__":
    address_url_list = []

    url_list = get_list_of_urls_to_scrape()

    for url in url_list:
        page = requests.get(url)
        soup = BeautifulSoup(page.text, "html.parser")

        for link in soup.find_all("a"):
            link_href = str(link.get("href"))
            if link_href.startswith("https://visitsouthjersey.com/member-org/"):
                address_url_list.append(link_href)

    data_to_write = []

    for address_url in address_url_list:
        page = requests.get(address_url)
        soup = BeautifulSoup(page.text, "html.parser")
        address = soup.find(class_="col-xs-9").contents[0]
        address = str(address.string)
        address = " ".join(address.split())

        location = soup.find(class_="page-header").contents[1]
        location = str(location.contents[0].string)
        location = " ".join(location.split())

        data_to_write.append([address, location])

    with open(output_filepath, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["address", "location"])
        writer.writerows(data_to_write)
