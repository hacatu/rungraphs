The python script parse.py takes one argument, the path to a folder with a bunch of gpx files in it.
E.g. `python parse.py ~/Downloads/strava_export/activities`.

Five graphs will be created:

- nth mile pace over time: Shows several line plots over all runs.
  Each line plot is the pace (in minutes/mile) of the nth mile you ran on a particular run.
  Runs where you ran 3.3 miles for example will have points on the first 3 lines but not the lines
  for the pace of miles 4+.  Lines are only created up to the most miles you ran more than once.
  For example, if you ran 3-4 miles most of the time but 5.1 miles once and 8.4 miles once, there will
  be lines only up to 5 miles because you ran 5 miles more than once but never 6+ so there is
  no trend for your mile 6+ paces.
  
- nth mile pace distribution: Similar to nth mile pace over time, except instead of showing how pace
  progressed over all runs, this graph shows the distribution of paces for each of the nth miles in a
  histogram and violin plot.  This more clearly shows how much you slow down over long runs, how much
  variation your paces have at each mile, and your average paces, but contains no information about
  how your pace progressed over time.
  
- all mile pace distribution:  Similar to nth mile pace distribution, except there is only one histogram
  and one violin plot and they contain information about all miles aggregated together.  Note that only full
  miles are counted, so if you ran 3.9 miles for 10 days in a row, you will have a total of 30 data points
  in the histogram, not 39.
  
- run distance over time: Shows the distance of each run over all runs.

- run distance distribution: Shows the distribution for the distance you ran across all runs.  For instance,
  if you usually ran about 3.3 miles but often went up to 4.5 and sometimes 5.1 or 8.4, you will see a cluster
  around 3.3 and a tail up to 8.4.

NB: There are a couple things hardcoded in this script that you will probably need to change if you want to use it:

- nth mile graphs and the run distance over time graph have their independant labels set to go from 2 to 29 (cf
  line 147 and 170).  This should be fixed by also exporting the run days (see line 118) when parsing the files
  and using them instead of a range.

- Related to the first problem, if you have multiple runs in a day or skip days, the nth mile pace over time
  and run distance over time graphs will be messed up.  To fix this, we would have to aggregate runs that occured
  on the same day.  The best way would be to have a dict from `date`s to `(distance, [pace])` instead of `table`,
  and then runs on the same day could be combined by stitching them end to end, taking the first, taking the longest,
  or taking the fastest.

- `pace_bins`, `distance_bins`, and the associated tick marks were chosen based on my data.  If you ever run faster
  than a 5 minute mile, have extremely regular paces so 15 second demarcation is too coarse, ever run less than 2.4 miles,
  have extremely regular distances so .2 mile demarcation is too coarse, or have an extremely wide range of paces or distances,
  you will need to adjust these.  This could be done automatically by finding the min and max pace and distance and
  picking start/size values accordingly.

- The script simply takes all runs in the folder, so you will need to create a new folder and copy only the runs in the time range
  you care about into it.  Accepting start and stop dates would be nice.

- Finally, the 5 graphs could automatically be assembled into the combined graph.

Feel free to open an issue or pull request if you wish to use this tool and encounter one of these problems.

