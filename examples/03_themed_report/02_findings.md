# Findings

Each finding uses a level-2 heading so it appears in the table of contents.
Sub-points use level-3 headings; with `--toc-depth 2` they would be left out.

## Finding 1: Response times regressed after the June release

Median API latency rose from 180 ms to 240 ms.

### Impact

Checkout completion dropped by roughly 2% during peak hours.

### Recommendation

> Roll back the connection-pool change and re-test under load before
> re-deploying.

## Finding 2: Error budget is healthy

The service stayed within its 99.9% availability target for the quarter.

### Evidence

```graph
{
  "title": "Monthly Availability (%)",
  "show_legend": false,
  "min": 99.0,
  "max": 100.0,
  "data": {
    "x": ["Jul", "Aug", "Sep"],
    "Availability": [99.95, 99.92, 99.97]
  },
  "series": [
    { "label": "Availability", "type": "bar", "colour": "#2d6cbe" }
  ]
}
```
