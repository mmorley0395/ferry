"""
Assumptions: 'all_locations.csv' already exists

"""

import requests
import pandas as pd
from dotenv import find_dotenv, load_dotenv
import os
from pathlib import Path

load_dotenv(find_dotenv())

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

GDRIVE_FOLDER = Path(os.getenv("GDRIVE_FOLDER"))

# your csv, which at minimum should have an address column.
input_path = GDRIVE_FOLDER / "all_locations.csv"
output_path = GDRIVE_FOLDER / "all_locations_with_xy.csv"


def extract_lat_long_via_address(address_or_zipcode):
    """
    function that returns lat & long using google's api.
    passes in your address list created above.
    """
    print(f"Getting XY for: {address_or_zipcode}")
    lat, lng = None, None
    base_url = "https://maps.googleapis.com/maps/api/geocode/json"
    endpoint = f"{base_url}?address={address_or_zipcode}&key={GOOGLE_API_KEY}"

    # see how our endpoint includes our API key? Yes this is yet another reason to restrict the key
    r = requests.get(endpoint)
    if r.status_code not in range(200, 299):
        return None, None

    try:
        results = r.json()["results"][0]
        lat = results["geometry"]["location"]["lat"]
        lng = results["geometry"]["location"]["lng"]
    except IndexError:
        print("ERROR!")
        print(address_or_zipcode)
        print(r.json())

    return lat, lng


if __name__ == "__main__":
    df = pd.read_csv(input_path)
    df["lat"] = 0.0
    df["lng"] = 0.0

    for idx, row in df.iterrows():
        address = row.Address
        lat, lng = extract_lat_long_via_address(address)

        df.at[idx, "lat"] = lat
        df.at[idx, "lng"] = lng

    df.to_csv(output_path)
