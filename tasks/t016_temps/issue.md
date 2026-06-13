# Bug: daily temperature summary is wrong

`daily_summary([0, 100])` should return `122.0` (the average of the two
readings converted to Fahrenheit) but returns the wrong number. Two things
look off: the Celsius→Fahrenheit conversion seems incorrect, and missing
readings (`None`) are not handled the way the docstring promises. An empty
list should return `None` instead of crashing.

Files: `convert.py` (conversion) and `report.py` (aggregation).
