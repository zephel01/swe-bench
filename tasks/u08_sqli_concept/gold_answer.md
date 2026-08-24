{
  "vulnerability": "sql injection",
  "mechanism": "If the application concatenates untrusted input into a SQL string, an attacker can close a quoted literal and append a tautology such as 1=1, so the WHERE clause no longer filters rows the way the programmer intended.",
  "mitigation": "Send SQL through parameterized queries or prepared statements with bind variables so user data cannot change the statement structure; validate types and use the least database privilege needed."
}
