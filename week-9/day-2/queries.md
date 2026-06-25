The PromQL Mental Model
metric_name                    → all time series for this metric
metric_name{label="value"}     → filter by exact label
metric_name{label=~"regex"}    → filter by regex
rate(metric[5m])               → per-second rate over 5 minutes
sum(metric) by (label)         → aggregate across a label