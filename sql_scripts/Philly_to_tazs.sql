

########### --used to add TAZ column to attractions file and pickup spatial attributes of 2010 taz file
alter table attractions 
add column TAZ integer;

UPDATE attractions AS taz
  SET  "taz" = m.taz 
FROM   "2010_TAZ" AS m
WHERE  ST_Contains(m.geom, taz.geom);


select shapes.geom, d_taz, sum(compositeweight) from trip 
left join "2010_TAZ" as shapes
on shapes.taz=trip.d_taz 
where o_county = 42101
	and d_state = 34
group by d_taz, shapes.geom;


select geom, sum(compositeweight),mode_agg from trip 
left join "2010_TAZ" as shapes
on shapes.taz=trip.d_taz 
where o_county = 42101
	and d_state = 34
	and d_loc_type = 4
group by mode_agg , geom
order by geom 

-----------------------------------------------------run below as block--------

drop table if exists rec_trips;
create table rec_trips as (
	select geom, sum(compositeweight), mode_agg from trip 
	left join "2010_TAZ" as shapes
	on shapes.taz=trip.d_taz 
	where o_county = 42101
		and d_state = 34
		and d_loc_type = 4
	group by mode_agg , geom
	order by geom 
);

drop table if exists geom_index;
create table geom_index as(
	select distinct geom from rec_trips rt );
ALTER TABLE geom_index ADD COLUMN id SERIAL PRIMARY KEY;

alter table rec_trips 
add column walk_trips int,
add column car_trips int, 
add column bike_trips int,
add column private_transit int,
add column public_transit int;

update rec_trips 
set walk_trips = "sum" where mode_agg = 1;
update rec_trips
set bike_trips = "sum" where mode_agg = 2;
update rec_trips 
set car_trips = "sum" where mode_agg = 3;
update rec_trips 
set private_transit = "sum" where mode_agg = 4;
update rec_trips 
set public_transit = "sum" where mode_agg = 5;

--end result is a table showing all recreational trips from philly to these tazs in NJ by mode
select distinct geom, sum(walk_trips) as walk_trips , sum(bike_trips) as bike_trips, sum(car_trips) car_trips , sum(private_transit) private_transit, sum(public_transit) as public_transit 
from rec_trips rt 
group by geom
order by geom
