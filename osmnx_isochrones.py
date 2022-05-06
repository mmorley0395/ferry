import pandas as pd
import geopandas as gpd
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv
import osmnx as ox

load_dotenv()
GDRIVE_FOLDER = os.getenv("GDRIVE_PROJECT_FOLDER")
GEOJSON_FOLDER = os.getenv("GEOJSON_FOLDER")
DB_NAME = os.getenv("DB_NAME")
HOST = os.getenv("DB_HOST")
USER = os.getenv("DB_USER")
PW = os.getenv("DB_PASSWORD")
db_connection_info = os.getenv("DATABASE_URL")
engine = create_engine(db_connection_info)
dbConnection = engine.connect()
target_network = [
    "Camden County, NJ",
    "Burlington County, NJ",
    "Mercer County, NJ",
    "Gloucester County, NJ",
]
srid = 2272


def import_points(points):
    """imports target points into your postgres db, i.e. what you want isochrones around"""
    gdf = gpd.read_file(f"{GEOJSON_FOLDER}/{points}")
    print("importing target points into database...")
    gdf = gdf.to_crs(f"EPSG:{srid}")
    gdf.to_postgis("target_points", engine, schema=None, if_exists="replace")


def import_taz():
    """imports 2010 taz data into db"""
    path = "/Volumes/GoogleDrive/Shared drives/FY22 Regional Rail Fare Equity/Code/Data/Inputs/Zonal Data/2010_taz.shp"
    path = os.path.normcase(path)
    gdf = gpd.read_file(path)
    print("Importing 2010 TAZ geometries into database...")
    gdf = gdf.rename(columns=str.lower)
    gdf = gdf.to_crs(f"EPSG:{srid}")
    gdf.to_postgis("2010_taz", engine, schema=None, if_exists="replace")


def import_population():
    """imports taz population data from g drive"""
    zipfile = "/Volumes/GoogleDrive/Shared drives/Community & Economic Development /Ferry Service Feasibility_FY22/Shapefiles/CTPP2012_2016_total_pop_taz.zip"
    zipfile = os.path.normcase(zipfile)
    gdf = gpd.read_file(zipfile)
    gdf.rename(
        columns={"F0": "population", "F1": "moe", "name": "taz_name"}, inplace=True
    )
    print("Importing TAZ polygons with population data from the CTPP into database...")
    gdf = gdf.to_crs(f"EPSG:{srid}")
    gdf.to_postgis("taz_pop", engine, schema=None, if_exists="replace")


def import_hts_trip():
    """imports trip table from HTS data, creates philly and nj specific demand tables for non-work recreational trips"""
    path = "/Volumes/GoogleDrive/Shared drives/Community & Economic Development /Ferry Service Feasibility_FY22/HHTS/PublicDB_RELEASE/DVRPC HTS Database Files/4_Trip_Public.xlsx"
    path = os.path.normcase(path)
    df = pd.read_excel(path)
    print("Importing HTS trips data...")
    df = df.rename(columns=str.lower)
    df.to_sql("trips", engine, if_exists="replace")
    query = """
    drop table if exists philly_nj_rec_trips;
    create table philly_nj_rec_trips as (
        select shapes.geometry as geom, sum(compositeweight) as trips from trips 
        left join "2010_taz" as shapes
        on shapes.taz=trips.d_taz 
        where o_county = 42101
            and d_state = 34 
            and d_loc_type = 4
        group by geom
        order by geom);
        drop table if exists nj_philly_rec_trips;
        create table nj_philly_rec_trips as (
            select shapes.geometry as geom, sum(compositeweight) as trips from trips
            left join "2010_taz" as shapes
            on shapes.taz=trips.o_taz 
            where d_county = 42101
                and d_taz in (2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63,64,65,66,67,68,69,70,71,72,73,74,75,76,77,78,79,80,81,82,83,84,85,86,87,88,89,90,91,92,93,94,95,96,97,98,99,100,101,102,103,104,105,106,107,108,109,110,111,112,113,114,115,116,117,118,119,120,121,122,123,124,125,126,127,128,129,130,131,132,133,134,135,136,137,138,139,140,141,142,143)
                and d_loc_type = 4
            group by geom
            order by geom);
        """
    print(
        "Creating tables for non-work recreational demand to and from Philadelphia and NJ Counties in DVRPC Region..."
    )
    engine.execute(query)


def import_dvrpc_munis():
    """imports dvrpc municipalities"""
    url = "https://arcgis.dvrpc.org/portal/rest/services/Boundaries/MunicipalBoundaries/FeatureServer/0/query?where=dvrpc_reg%20%3D%20'Yes'&outFields=*&outSR=4326&f=json"
    gdf = gpd.read_file(url)
    print("Importing dvrpc municipal boundaries into database...")
    gdf = gdf.to_crs(f"EPSG:{srid}")
    gdf.to_postgis("dvrpc_munis", engine, schema=None, if_exists="replace")


def import_attractions():
    """imports attraction data"""
    print("Importing attractions points into database...")
    gdf = gpd.read_file(f"{GEOJSON_FOLDER}/attractions.geojson")
    gdf = gdf.to_crs(f"EPSG:{srid}")
    gdf.to_postgis("attractions", engine, schema=None, if_exists="replace")


def import_osmnx(target_network):
    """imports toplogically sound osmnx network for target_network, defined above"""
    G = ox.graph_from_place(target_network, network_type="drive")
    ox.io.save_graph_geopackage(
        G, filepath=f"{GEOJSON_FOLDER} /graph.gpkg", encoding="utf-8", directed=False
    )
    gdf = gpd.read_file(f"{GEOJSON_FOLDER}/graph.gpkg", layer="edges")
    gdf.to_postgis(
        "edges", engine, schema=None, if_exists="replace", index=True, index_label="fid"
    )

    gdf = gpd.read_file(f"{GEOJSON_FOLDER}/graph.gpkg", layer="nodes")
    gdf.to_postgis(
        "nodes", engine, schema=None, if_exists="replace", index=True, index_label="fid"
    )


def osmnx_to_pg_routing():
    """creates a new table based on the OSMNX exports that is compatable with the pgRouting extension of PostGIS"""
    query = f"""
        drop table if exists osmnx;
        create table osmnx as(
        select
            fid as id,
            "from"::bigint as "source",
            "to"::bigint as target,
            "name",
            st_length(st_transform(geometry,{srid})) * 3.28084 as len_feet,
            st_length(st_transform(geometry,{srid})) as real_length,
            1000000000 as reverse_cost,
            st_transform(geometry, {srid}) as geom
        from edges
        where geometry is not null
    ); 
    SELECT UpdateGeometrySRID('osmnx','geom',{srid});
     """
    engine.execute(query)


# todo: cleanup nearest neighbor so it's more modular
def nearest_node():
    """finds the nearest node on the network to target point"""
    query = f"""
       drop table if exists nearest_node;
        create table nearest_node as (
            select target_points.id as id, 
            (select osmnx."source" from osmnx order by st_distance(st_transform(target_points.geometry, {srid}),osmnx.geom) 
            limit 1) as osmnx_id, st_transform(target_points.geometry, {srid}) as geom from target_points);
            select UpdateGeometrySRID('nearest_node','geom',{srid});
            """

    engine.execute(query)
    df = pd.read_sql('select osmnx_id from "nearest_node"', dbConnection)
    neighbors = df.values.tolist()
    df2 = pd.read_sql('select id from "nearest_node"', dbConnection)
    list_of_ids = df2.values.tolist()
    return neighbors, list_of_ids


def make_isochrones(neighbors, list_of_ids, minutes, speed_mph):
    miles = (minutes / 60) * speed_mph  # represents distance of isochrone
    distance_threshold = (
        miles * 5280
    )  # the distance, in the units of above SRID, of the isochrone using the network
    """generates isochrones using pgrouting query"""
    drop_query = f"""drop table if exists isochrones{minutes};"""
    engine.execute(drop_query)
    count = 0
    for value, id in zip(neighbors, list_of_ids):
        isochrone_query = f"""        
        SELECT * FROM pgr_drivingDistance(
                'SELECT id, source, target, real_length as cost, reverse_cost FROM osmnx',
                {value[0]}, {distance_threshold}, false
            ) as a
        JOIN osmnx AS b ON (a.edge = b.id) ORDER BY seq;
        """

        tempgdf = gpd.GeoDataFrame.from_postgis(isochrone_query, engine)
        tempgdf["iso_id"] = id[0]
        tempgdf = tempgdf.set_crs(f"EPSG:{srid}")
        print(f"Creating {minutes}-minute isochrone # {count}...")
        count += 1
        tempgdf.to_postgis(f"isochrones{minutes}_minutes", engine, if_exists="append")


def make_hulls(minutes):
    hull_query = f"""
    drop table if exists isochrone_hull{minutes}_minutes;
    create table isochrone_hull{minutes}_minutes as(
        select iso_id, ST_ConcaveHull(ST_Union(geom), 0.80) as geom from isochrones{minutes}_minutes
        group by iso_id
        );
    select UpdateGeometrySRID('isochrone_hull{minutes}_minutes','geom',{srid});
    """
    print(f"Creating convex hulls around {minutes}-minute isochrones, just a moment...")
    engine.execute(hull_query)
    print("Isochrones and hulls created, see database for results.")


def calculate_taz_demand(minutes):
    """uses drive time isochrones to calculate taz demand for an isochrone of a given timeframe"""
    query = f"""drop table if exists to_from{minutes};
    create table to_from{minutes} as
    with nj_philly as(
        SELECT
        isochrone_hull{minutes}_minutes.iso_id
        , coalesce(sum(nj_philly_rec_trips.trips),0) AS nj_philly_trips_in_driveshed
        FROM isochrone_hull{minutes}_minutes 
            LEFT JOIN nj_philly_rec_trips 
            ON ST_Intersects(isochrone_hull{minutes}_minutes.geom, st_transform(nj_philly_rec_trips.geom, 2272)) 
        GROUP BY isochrone_hull{minutes}_minutes.iso_id
    ),
    philly_nj as(
    SELECT
        isochrone_hull{minutes}_minutes.iso_id
        , coalesce(sum(philly_nj_rec_trips.trips),0) AS philly_nj_trips_in_driveshed
        FROM isochrone_hull{minutes}_minutes 
            LEFT JOIN philly_nj_rec_trips 
            ON ST_Intersects(isochrone_hull{minutes}_minutes.geom, st_transform(philly_nj_rec_trips.geom, 2272)) 
        GROUP BY isochrone_hull{minutes}_minutes.iso_id)
    select philly_nj.iso_id, philly_nj_trips_in_driveshed, nj_philly.nj_philly_trips_in_driveshed from philly_nj
    inner join nj_philly 
    on philly_nj.iso_id=nj_philly.iso_id
    """
    engine.execute(query)
    print(f"{minutes}-minute demand table created, check database for table")


def aggregate_demand(iso_minutes_A, iso_minutes_B):
    """Builds a table that aggregates to and from demand for two sets of isochrones, e.g. 15 and 30 minute isochrones"""
    query = f"""
    drop table if exists aggregated_results;
    create table aggregated_results as(
        select 
            tf{iso_minutes_A}.iso_id,
            tf{iso_minutes_A}.philly_nj_trips_in_driveshed + tf{iso_minutes_A}.nj_philly_trips_in_driveshed as total_trips{iso_minutes_A},
            tf{iso_minutes_B}.philly_nj_trips_in_driveshed + tf{iso_minutes_B}.nj_philly_trips_in_driveshed as total_trips{iso_minutes_B}
        from to_from{iso_minutes_A} tf{iso_minutes_A}
        inner join to_from{iso_minutes_B} tf{iso_minutes_B}
        on tf{iso_minutes_A}.iso_id = tf{iso_minutes_B}.iso_id)"""
    engine.execute(query)
    print(f"To and from demand columns combined...")


def calculate_attractions_and_demand_in_isos(minutes):
    """calculates the HHTS demand and the number of attractions for each isochrone_id"""
    query = f"""
    ALTER table aggregated_results
        DROP column if exists attractions{minutes};
    ALTER table aggregated_results
        ADD column attractions{minutes} varchar(50);
    UPDATE aggregated_results 
    SET attractions{minutes}= subquery.attractions_{minutes}_min
    FROM (SELECT iso_id, count(attractions) as attractions_{minutes}_min
        FROM isochrone_hull{minutes}_minutes 
            LEFT JOIN attractions 
            ON st_within(attractions.geometry, isochrone_hull{minutes}_minutes.geom) 
            GROUP BY isochrone_hull{minutes}_minutes.iso_id
            ORDER by iso_id) AS subquery
    WHERE aggregated_results.iso_id=subquery.iso_id;
    """
    print(
        f"calculating number of attractions in each isochrone for the {minutes}-minute shed..."
    )
    engine.execute(query)


def calculate_population_in_isos(minutes):
    """calculates population for isochrone distance (in minutes) and adds new column to master table"""
    query = f"""
    alter table aggregated_results 
        DROP column if exists pop{minutes};
    ALTER table aggregated_results
        ADD column pop{minutes} varchar(50);
    UPDATE aggregated_results 
    SET pop{minutes}=subquery.population
    FROM (SELECT ih.iso_id, sum(population) as population 
        FROM taz_pop tp 
            INNER join isochrone_hull{minutes}_minutes ih 
            ON st_intersects(ih.geom,tp.geometry)
            GROUP by ih.iso_id
            ORDER by ih.iso_id) AS subquery
    WHERE aggregated_results.iso_id=subquery.iso_id;"""
    print(f"calculating total population in the {minutes}-minute shed...")
    engine.execute(query)


def pickup_munis():
    """joins the master table with dvprc municipalities for better identification of points"""
    query = """
    alter table aggregated_results 
    drop column if exists muni;
    alter table aggregated_results
    add column muni varchar(50);
    UPDATE aggregated_results 
    SET muni=subquery.mun_name
    FROM (select 
        id, dvrpc_munis.mun_name
        from target_points tp
        inner join dvrpc_munis
        on st_intersects(tp.geometry, dvrpc_munis.geometry)
        group by id, dvrpc_munis.mun_name
        order by id) AS subquery
    WHERE aggregated_results.iso_id=subquery.id;"""
    print(f"joining main table to DVRPC municipalities...")
    engine.execute(query)


def import_all():
    import_points("dock_no_freight.geojson")
    import_osmnx(target_network)
    import_population()
    import_taz()
    import_hts_trip()
    import_attractions()
    import_dvrpc_munis()


def build_network_and_isochrones(isochrone_minutes_1, isochrone_minutes_2, speed):
    osmnx_to_pg_routing()
    neighbor_obj = nearest_node()
    make_isochrones(neighbor_obj[0], neighbor_obj[1], isochrone_minutes_1, speed)
    make_isochrones(neighbor_obj[0], neighbor_obj[1], isochrone_minutes_2, speed)
    make_hulls(isochrone_minutes_1)
    make_hulls(isochrone_minutes_2)


def perform_analysis(isochrone1, isochrone2):
    """Runs all calculations to calculate HTS travel demand, # of attractions in iso-shed, and picks up municipalities from DVRPC layer"""
    calculate_taz_demand(isochrone1)
    calculate_taz_demand(isochrone2)
    aggregate_demand(isochrone1, isochrone2)
    calculate_attractions_and_demand_in_isos(isochrone1)
    calculate_attractions_and_demand_in_isos(isochrone2)
    calculate_population_in_isos(isochrone1)
    calculate_population_in_isos(isochrone2)
    pickup_munis()


if __name__ == "__main__":
    import_all()
    build_network_and_isochrones(15, 30, 35)
    perform_analysis(15, 30)
