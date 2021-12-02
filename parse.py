"""
Parse a gpx file and convert it to time,distance pairs
"""

import xml.etree.ElementTree as ET
import math
import sys
from datetime import datetime
from pathlib import Path
import collections
import bisect
import heapq
import itertools as itt
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import plotly.colors as colors

plotly_colors = colors.qualitative.Plotly

def fst(t):
	return t[0]

def snd(t):
	return t[1]

def sliding_window(iterable, n=2):
    # sliding_window('ABCDEFG', 4) -> ABCD BCDE CDEF DEFG
    it = iter(iterable)
    window = collections.deque(itt.islice(it, n), maxlen=n)
    if len(window) == n:
        yield tuple(window)
    for x in it:
        window.append(x)
        yield tuple(window)

def geodist(lat1, lon1, lat2, lon2):
	"""
	Compute geodesic distance between 2 point on the WGS-84 reference ellipsoid for earth
	using Vincenty's formula.  This is accurate to within .5 mm, which is totally necessary.
	https://en.wikipedia.org/wiki/Vincenty%27s_formulae
	"""
	a = 6378137.0 # semimajor axis of earth
	b = 6356752.314245 # semiminor axis of earth
	f = 1 - b/a # "flattening" parameter of earth
	u1 = math.atan((1-f)*math.tan(lat1/180*math.pi)) # "reduced latitude" of 1st point
	u2 = math.atan((1-f)*math.tan(lat2/180*math.pi)) # "reduced latitude" of 2nd point
	L = (lon2 - lon1)/180*math.pi
	# sin and cos of u1 and u2
	su1 = math.sin(u1)
	cu1 = math.cos(u1)
	su2 = math.sin(u2)
	cu2 = math.cos(u2)
	l = L # lambda, the longitudinal difference on the reference sphere
	while True:
		# sin and cos of l(ambda) and s(igma)
		sl = math.sin(l)
		cl = math.cos(l)
		ss = math.hypot(cu2*sl, cu1*su2 - su1*cu2*cl)
		if ss < 1e-10:
			return 0
		cs = su1*su2 + cu1*cu2*cl
		s = math.atan2(ss, cs) # sigma, the angle between the points on ref. sphere
		sa = cu1*cu2*sl/ss # sin of alpha, the angle between the extended geodesic and the equator
		ca2 = 1 - sa**2 # cos squared of alpha
		c2sm = cs - 2*su1*su2/ca2 # cos of 2 sigma_m, the latitude of the midpoint of the points
		C = f/16*ca2*(4+f*(4 - 3*ca2))
		l_old = l
		l = L + (1-C)*f*sa*(s + C*sa*(c2sm + C*cs*(-1 + 2*c2sm**2)))
		if abs(l - l_old) < 6e-5:
			break
	t2 = ca2*(a**2 - b**2)/b**2
	A = 1 + t2/16384*(4096+t2*(-768 + t2*(320 - 175*t2)))
	B = t2/1024*(256 + t2*(-128 + t2*(74 - 47*t2)))
	ds = B*ss*(c2sm + B/4*(cs*(-1 + 2*c2sm**2) - B/6*c2sm*(-3 + 4*c2sm**2)))
	return b*A*(s - ds)

mile_paces = []
run_distances = []

for gpx_name in (path for path in Path(sys.argv[1]).iterdir() if path.is_file()):
	with open(gpx_name, "r") as f:
		xml = ET.parse(f)

	svg_name = xml.getroot().find("{*}metadata").find("{*}time").text
	run_start_time = datetime.strptime(svg_name, "%Y-%m-%dT%H:%M:%SZ")
	svg_name += ".svg"
	trkseg = xml.getroot().find("{*}trk").find("{*}trkseg")
	points = (
		(
			float(trkpt.attrib["lat"]),
			float(trkpt.attrib["lon"]),
			float(trkpt.find("{*}ele").text),
			datetime.strptime(trkpt.find("{*}time").text, "%Y-%m-%dT%H:%M:%SZ").timestamp()
		) for trkpt in trkseg.iterfind("{*}trkpt"))

	tot_time = None
	tot_dist = 0.0
	table = []
	for a, b in sliding_window(points):
		if tot_time is None:
			tot_time = 0.0
			table.append((0.0, 0.0))
		d_time = b[3] - a[3]
		d_dist = geodist(*a[:2], *b[:2])
		tot_time += d_time
		tot_dist += d_dist
		table.append((tot_time/60, tot_dist/1609.344))

	tot_dist /= 1609.344
	tot_time /= 60
	avg_pace = tot_time/tot_dist
	print(f"Distance: {tot_dist} mi\nAvg Pace: {int(avg_pace)}:{int(avg_pace*60)%60} /mi\nMoving Time: {int(tot_time/60)}:{int(tot_time)%60}:{int(tot_time*60)%60}")

	times, distances = zip(*table)
	"""
	fig = go.Figure()
	fig.add_trace(go.Scatter(x=times, y=distances, mode="none", fill="tozeroy"))
	fig.update_layout(title=f"Total Distance Ran (November {run_start_time.day})", xaxis_title="Time (minutes)", yaxis_title="Distance (miles)")
	fig.write_image(svg_name)
	"""

	a = 0
	mile_paces.append((run_start_time.timestamp(), []))
	for mile in range(1, int(tot_dist) + 1):
		b = bisect.bisect(distances, mile)
		mile_dist = distances[b] - distances[a]
		mile_time = times[b] - times[a]
		mile_pace = mile_time/mile_dist
		print(f"Mile {mile}: Avg Pace: {int(mile_pace)}:{int(mile_pace*60)%60}")
		mile_paces[-1][1].append(mile_pace)
	
	run_distances.append(tot_dist)

mile_paces.sort(key=fst)
mile_paces = [snd(t) for t in mile_paces]

pace_bins = {
	"start": 5,
	"size": 0.25
}

if len(run_distances) >= 2:
	second_longest_distance = heapq.nlargest(2, run_distances)[-1]
	fig_scatter = go.Figure()
	fig_hist = make_subplots(rows=1, cols=2, shared_yaxes=True)
	for mile in range(1, int(second_longest_distance) + 1):
		table = ((day, paces[mile - 1]) for (day, paces) in enumerate(mile_paces, 2) if len(paces) >= mile)
		days, paces = zip(*table)
		name = f"Mile {mile}"
		fig_scatter.add_trace(go.Scatter(x=days, y=paces, name=name))
		fig_hist.add_trace(go.Histogram(y=paces, ybins=pace_bins, name=name, marker={"color": plotly_colors[mile - 1]}), row=1, col=1)
		fig_hist.add_trace(go.Violin(y=paces, name=name, showlegend=False, line={"color": plotly_colors[mile - 1]}), row=1, col=2)
	fig_scatter.update_layout(title="Pace of nth Mile over Time", xaxis_title="Day (11/2-11/29)", yaxis_title="Pace (minutes/mile)")
	fig_scatter.update_xaxes(tick0=2, dtick=1)
	fig_scatter.write_image("nth_mile_progress.svg")
	fig_hist.update_layout(title="Pace Distribution of nth Mile", xaxis_title="Frequency", yaxis_title="Pace (minutes/mile)", barmode="overlay")
	fig_hist.update_traces(opacity=0.6)
	fig_hist.update_yaxes(tick0=pace_bins["start"], dtick=2*pace_bins["size"], ticks="inside", col=1)
	fig_hist.write_image("nth_mile_dist.svg")

fig = make_subplots(rows=1, cols=2, shared_yaxes=True)
flat_paces = list(itt.chain.from_iterable(mile_paces))
fig.add_trace(go.Histogram(y=flat_paces, ybins=pace_bins, showlegend=False, marker={"color": plotly_colors[0]}), row=1, col=1)
fig.add_trace(go.Violin(y=flat_paces, name="All Miles", showlegend=False, marker={"color": plotly_colors[0]}), row=1, col=2)
fig.update_layout(title="Pace Distribution of all Miles", xaxis_title="Frequency", yaxis_title="Pace (minutes/mile)")
fig.update_yaxes(tick0=pace_bins["start"], dtick=2*pace_bins["size"], ticks="inside", col=1)
fig.write_image("all_miles_dist.svg")

fig = go.Figure()
fig.add_trace(go.Scatter(x=list(range(2, 30)), y=run_distances))
fig.update_layout(title="Distance Run each Day (106.8 total)", xaxis_title="Day (11/2-11/29)", yaxis_title="Distance (miles)")
fig.update_xaxes(tick0=2, dtick=1)
fig.write_image("daily_distance.svg")

distance_bins = {
	"start": 2.4,
	"size": 0.2
}

fig = make_subplots(rows=1, cols=2, shared_yaxes=True)
fig.add_trace(go.Histogram(y=run_distances, ybins=distance_bins, showlegend=False, marker={"color": plotly_colors[0]}), row=1, col=1)
fig.add_trace(go.Violin(y=run_distances, name="Run Distances", showlegend=False, marker={"color": plotly_colors[0]}), row=1, col=2)
fig.update_layout(title="Distance Distribution of all Runs", xaxis_title="Frequency", yaxis_title="Distance (miles)")
fig.update_yaxes(tick0=distance_bins["start"], dtick=2*distance_bins["size"], ticks="inside", col=1)
fig.write_image("distance_dist.svg")

