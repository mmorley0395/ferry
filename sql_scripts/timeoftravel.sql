with timestamped as (
select sum(compositeweight) trips, count(arrive) count_of_arrivals, to_timestamp(arrive, 'HH24:MI')::time tstamp from trip 
	where d_loc_type = 4
		and arrive not like '9999'
		and arrive not like '9998'
		and arrive not like '98'
		-- omitting outliers that aren't a proper timestamp
	group by trip.arrive 
	order by trip.arrive
	)
select sum(trips), sum(count_of_arrivals), date_trunc('hour',tstamp) 
from timestamped
group by date_trunc('hour', tstamp)
order by date_trunc('hour', tstamp)