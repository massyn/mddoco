# Charts

Fenced ` ```graph ` blocks hold a JSON payload and are rendered to a static SVG
chart at build time — no client-side JavaScript. Only `data` is required.

## Bare minimum

Series are inferred from the data keys; the default is a blue line chart.

```graph
{
  "data": {
    "x": ["Jan", "Feb", "Mar", "Apr"],
    "Sales": [100, 150, 120, 180]
  }
}
```

## Bar chart with a title

```graph
{
  "title": "Quarterly Revenue",
  "show_legend": false,
  "data": {
    "x": ["Q1", "Q2", "Q3", "Q4"],
    "Revenue": [42000, 58000, 51000, 73000]
  },
  "series": [
    { "label": "Revenue", "type": "bar", "colour": "#2d6cbe" }
  ]
}
```

## Bar and line combined

```graph
{
  "title": "Sales vs Target",
  "data": {
    "x": ["Jan", "Feb", "Mar", "Apr", "May"],
    "Sales":  [85, 92, 78, 96, 110],
    "Target": [90, 90, 90, 90, 90]
  },
  "series": [
    { "label": "Sales",  "type": "bar",  "colour": "#3498db" },
    { "label": "Target", "type": "line", "colour": "#e74c3c" }
  ]
}
```

## Horizontal bar chart

```graph
{
  "title": "Team Performance",
  "orientation": "horizontal",
  "show_legend": false,
  "data": {
    "x": ["Alice", "Bob", "Carol", "Dave"],
    "Score": [88, 74, 91, 67]
  },
  "series": [
    { "label": "Score", "type": "bar", "colour": "#27ae60" }
  ]
}
```
