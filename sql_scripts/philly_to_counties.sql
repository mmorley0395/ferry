

########### --used to add TAZ column to attractions file and pickup spatial attributes of 2010 taz file
alter table attractions 
add column TAZ integer;

UPDATE attractions AS taz
  SET  "taz" = m.taz 
FROM   "2010_TAZ" AS m
WHERE  ST_Contains(m.geom, taz.geom)
;

select shapes.geom, d_taz, sum(compositeweight) from trip 
left join "2010_TAZ" as shapes
on shapes.taz=trip.d_taz 
where o_county = 42101
	and d_state = 34
	and d_loc_type = 4
group by d_taz, shapes.geom

select shapes.geom, d_taz, sum(compositeweight) from trip 
left join "2010_TAZ" as shapes
on shapes.taz=trip.d_taz 
where o_county = 42101
	and d_state = 34
group by d_taz, shapes.geom



