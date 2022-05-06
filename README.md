# Ferry Analysis

a collection of functions used in a FY22 Ferry Feasibility Study

## Basics

This repo is still under development. Right now it can

- Scrape a website (specifically visitsouthjersey.com) for addresses and reverse geocode them to Lat/Lon points using google's API
- Calculate the distance and directions between two or more points
- Create travel time isochrones around docks using PG routing.

## Prerequisites

- Conda installed on your system (to install the included .yml file)
- Postgres with the PostGIS extension and PGrouting installed on your DB of choice
- A Google API Key and a developer account (only necessary if you intend to use the distance_direction or google_lat_lon scripts)
- A configured .env file. See example below and plug in with your credentials.

### Nice to have

- QGIS or another mapping platform to view your isochrones

## Sample .env text

### (Create a file called ".env" in your working folder and store your credentials in it as seen below)

```
google_api = 12345678910

GDRIVE_FOLDER = /Volumes/GoogleDrive/Shared drives/Community & Economic Development /Ferry Service Feasibility_FY22/Shapefiles/For_Modeling

GEOJSON_FOLDER = /Volumes/GoogleDrive/Shared drives/Community & Economic Development /Ferry Service Feasibility_FY22/Shapefiles/geojson

DB_NAME=pg_routing_ferry
DB_HOST=localhost
DB_USER=postgres
DB_PASSWORD=your_password
DATABASE_URL=postgresql://postgres:your_password@localhost:5432/pg_routing_ferry
```

## Isochrone Analysis

### Environment Creation

Run the following commands in a terminal:

` conda env create -f environment.yml`

`conda activate ferry`

### Primary Analysis

Run `python osmnx_isochrones.py`. This uses 15 and 30 minutes as the default isochrones but change those values as you see fit in the file.
