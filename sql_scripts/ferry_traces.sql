
--in terminal, cd to /Volumes/GoogleDrive/Shared drives/Community & Economic Development /Ferry Service Feasibility_FY22/Shapefiles/
--import navigable waterways file with "psql [dbname] < dissolved_nav_waterway.sql"

alter table dissolved_nav_waterway 
drop column "length",
drop column "width";

drop table if exists cleaned_points;
create table cleaned_points as (
	SELECT translate(gps.basedatetime ,'T',' ') as datetime, gps.vesselname, gps.vesseltype, gps.status, gps."length", gps."width", gps.draft, gps.cargo, gps.geom
	from ais_2018 as gps
	join dissolved_nav_waterway dnw  
	on st_within(gps.geom, dnw.wkb_geometry)
	where status = 0);
	
CREATE INDEX "point_index" ON "cleaned_points" USING gist (geom);

drop table if exists traces_raw;
create table traces_raw as (
	select vesselname, ST_MakeLine(geom ORDER BY datetime) AS geom
	FROM    (
		SELECT *,
		       SUM(__isl) OVER(ORDER BY datetime) AS _mkl
		    FROM   (
		        SELECT cp.*,
		               COALESCE((cp.datetime::time - LAG(cp.datetime::time) OVER(ORDER BY cp.datetime) > '00:03:00')::INT, 0) AS __isl
		        FROM   cleaned_points AS cp) sq)  q
	GROUP BY
	        _mkl, vesselname)
	;

CREATE INDEX "trace_index" ON "traces_raw" USING gist (geom);

create table traces_cleaned as(
	select t.vesselname, t.geom
	from traces t
	join dissolved_nav_waterway dnw 
	on st_contains(dnw.wkb_geometry, t.geom)
	GROUP BY t.vesselname, t.geom);
	

