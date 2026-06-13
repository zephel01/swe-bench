# Bug: parse_csv_line() splits inside quoted fields

`parse_csv_line('a,"b,c",d')` should return `["a", "b,c", "d"]`
but returns `["a", '"b', 'c"', "d"]`. Double quotes must group a field,
commas inside quotes are literal, and `""` inside a quoted field is an
escaped quote character.
