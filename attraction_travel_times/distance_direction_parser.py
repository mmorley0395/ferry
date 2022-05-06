import googlemaps
from datetime import datetime
import os
from dotenv import load_dotenv
from pathlib import Path
import pandas as pd
from shapely.geometry import MultiLineString
import polyline
import geopandas as gpd

load_dotenv()
api_key = os.getenv("google_api")
gmaps = googlemaps.Client(key=api_key)
GDRIVE_FOLDER = Path(os.getenv("GDRIVE_FOLDER"))
origins = GDRIVE_FOLDER / "origin.csv"
destinations = GDRIVE_FOLDER / "attractions.csv"
origin_df = pd.read_csv(origins)
destinations_df = pd.read_csv(destinations)
now = datetime.now()


origin = (
    39.946196,
    -75.139832,
)  # hardcoded here since my origin doesn't change, but if yours does you can tweak the function to accept origins.


def distance_duration_iteration(mode):
    """returns a list of origin/destination dicts for driving or transit, respectively"""
    driving_list = []
    transit_list = []

    def distance_duration(destination):
        output = gmaps.directions(
            origin,
            destination,
            mode,
            units="imperial",
            departure_time=now,
        )
        names = {"name": name}
        output.insert(0, names)

        if mode == "driving":
            driving_list.append(output)

        if mode == "transit":
            transit_list.append(output)

    """loops through the destinations file and runs the distance duration function"""
    for idx, row in destinations_df.iterrows():
        lat = row["Latitude"]
        lon = row["Longitude"]
        name = row["Name"]
        destination = (lat, lon)
        distance_duration(destination)

    if mode == "driving":
        print("returning driving list")
        return driving_list
    if mode == "transit":
        print("returning transit list")
        return transit_list

def unpack_dicts(driving_list, transit_list):
    """function to crack into the nested dictionary structure that the google api returns"""
    df = pd.DataFrame()
    transit_list_of_dicts = []
    driving_list_of_dicts = []

    for item in driving_list:
        destination_lat = item[1]["legs"][0]["end_location"]["lat"]
        destination_lng = item[1]["legs"][0]["end_location"]["lng"]
        distance = item[1]["legs"][0]["distance"]["text"]
        duration = item[1]["legs"][0]["duration"]["text"]
        name = item[0]["name"]
        d = {
            "name": name,
            "lat": destination_lat,
            "lng": destination_lng,
            "d_distance": distance,
            "d_duration": duration,
        }
        driving_list_of_dicts.append(d)

    for item in transit_list:
        if len(item) == 2:
            destination_lat = item[1]["legs"][0]["end_location"]["lat"]
            destination_lng = item[1]["legs"][0]["end_location"]["lng"]
            distance = item[1]["legs"][0]["distance"]["text"]
            duration = item[1]["legs"][0]["duration"]["text"]
            name = item[0]["name"]
            d = {
                "t_distance": distance,
                "t_duration": duration,
            }
            transit_list_of_dicts.append(d)
        else:
            d = {
                "t_distance": 0,
                "t_duration": 0,
            }
            transit_list_of_dicts.append(d)

    df1 = pd.DataFrame(driving_list_of_dicts)
    df2 = pd.DataFrame(transit_list_of_dicts)
    frames = [df1, df2]
    df = pd.concat(frames, axis=1)
    return df


def df_to_csv(df):
    df.to_csv(GDRIVE_FOLDER / "attraction_travel_times.csv", sep=",")


def unpack_geometries(driving_list, transit_list):
    """accepts either the transit list or the driving list from the distance_duration_iteration function and parses accordingly"""
    driving_polylines = []
    transit_polylines = []

    for item in driving_list:
        if len(item) == 2:
            overview_line = [
                polyline.decode(item[1]["overview_polyline"]["points"], geojson=True)
            ]
        line = MultiLineString(overview_line)
        driving_polylines.append(line)

    else:
        pass
    df = pd.DataFrame(driving_polylines)
    df.columns = ["strings"]
    gdf = gpd.GeoDataFrame(df, crs="epsg:4326", geometry="strings")
    gdf.to_file(GDRIVE_FOLDER / "driving_polylines.geojson", driver="GeoJSON")
    

    for item in transit_list:
        if len(item) == 2:
            overview_line = [
                polyline.decode(item[1]["overview_polyline"]["points"], geojson=True)
            ]
        line = MultiLineString(overview_line)
        transit_polylines.append(line)

    else:
        pass
    del df
    df = pd.DataFrame(transit_polylines)
    df.columns = ["strings"]
    gdf = gpd.GeoDataFrame(df, crs="epsg:4326", geometry="strings")
    gdf.to_file(GDRIVE_FOLDER / "transit_polylines.geojson", driver="GeoJSON")

def csv_cleanup():
    exported_csv = GDRIVE_FOLDER / "attraction_travel_times.csv"
    df = pd.read_csv(exported_csv)
    df['d_distance'] = df["d_distance"].str.replace("[ mi]","")
    df['t_distance'] =df["t_distance"].str.replace("[ mi]","")
    df['d_duration'] = df["d_duration"].str.replace("mins","min")
    df['t_duration'] =df["t_duration"].str.replace("mins","min")
    df['d_duration'] = pd.to_timedelta(df['d_duration'])
    df['t_duration'] = pd.to_timedelta(df['t_duration'])
    df['d_faster_t'] = df['t_duration'] - df['d_duration'] 
    df_to_csv(df)


if __name__ == "__main__":
    # holds lists in memory so api isn't repeatedly called  (more useful for jupyter notebook than this script)
    driving_list = distance_duration_iteration("driving")
    transit_list = distance_duration_iteration("transit")

    # unpacks dictionaries returned by API
    unpacked_dictionaries = unpack_dicts(driving_list, transit_list)

    # creates csv of distances and durations for points
    df_to_csv(unpacked_dictionaries)

    # unpacks geometries as geojson
    unpack_geometries(driving_list, transit_list)
    
    #cleans up csv
    csv_cleanup()

    #todo:
    # create function to unpack details of trip rather than just overview line
