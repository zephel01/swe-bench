# Security Review Task: Documentation Site Access Log

You are a security analyst reviewing traffic to a public documentation site.
The site serves static pages and a read-only full-text search over its own
articles. Analyze the nginx access log below and decide whether it shows
evidence of a real attack or compromise. Only report genuine, demonstrable
security events — do not flag ordinary traffic.

```text
203.0.113.44 - - [16/Aug/2026:11:02:03 +0000] "GET /docs/search?q=SELECT%20*%20FROM%20orders HTTP/1.1" 200 7314 "https://docs.example.com/sql/guide" "Mozilla/5.0 (X11; Linux x86_64) Firefox/129.0"
203.0.113.44 - - [16/Aug/2026:11:02:19 +0000] "GET /docs/sql/joins HTTP/1.1" 200 21044 "https://docs.example.com/docs/search?q=SELECT" "Mozilla/5.0 (X11; Linux x86_64) Firefox/129.0"
10.0.2.15 - - [16/Aug/2026:11:02:20 +0000] "GET /healthz HTTP/1.1" 200 2 "-" "kube-probe/1.29"
198.51.100.9 - - [16/Aug/2026:11:02:41 +0000] "GET /docs/search?q=UNION%20ALL%20vs%20UNION HTTP/1.1" 200 6890 "https://www.google.com/" "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605.1.15"
198.51.100.9 - - [16/Aug/2026:11:02:58 +0000] "GET /docs/sql/set-operations HTTP/1.1" 200 18337 "https://docs.example.com/docs/search?q=UNION" "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605.1.15"
66.249.66.1 - - [16/Aug/2026:11:03:10 +0000] "GET /docs/sql/joins HTTP/1.1" 200 21044 "-" "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
203.0.113.71 - - [16/Aug/2026:11:03:33 +0000] "GET /docs/search?q=DROP%20TABLE%20recovery HTTP/1.1" 200 5120 "https://docs.example.com/docs/ddl" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/128.0.0.0"
203.0.113.71 - - [16/Aug/2026:11:03:52 +0000] "GET /docs/ddl/drop-table HTTP/1.1" 200 12908 "https://docs.example.com/docs/search?q=DROP" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/128.0.0.0"
10.0.2.15 - - [16/Aug/2026:11:03:59 +0000] "GET /healthz HTTP/1.1" 200 2 "-" "kube-probe/1.29"
203.0.113.44 - - [16/Aug/2026:11:04:12 +0000] "GET /docs/search?q=why%20is%201%3D1%20always%20true HTTP/1.1" 200 4402 "https://docs.example.com/docs/search" "Mozilla/5.0 (X11; Linux x86_64) Firefox/129.0"
198.51.100.9 - - [16/Aug/2026:11:04:30 +0000] "GET /docs/img/er-diagram-v2.png HTTP/1.1" 404 153 "https://docs.example.com/docs/sql/joins" "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605.1.15"
203.0.113.71 - - [16/Aug/2026:11:05:01 +0000] "GET /docs/search?q=OR%201%3D1%20injection%20cheatsheet HTTP/1.1" 200 5533 "https://docs.example.com/docs/security" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/128.0.0.0"
203.0.113.71 - - [16/Aug/2026:11:05:14 +0000] "GET /docs/security/sql-injection HTTP/1.1" 200 26611 "https://docs.example.com/docs/search?q=OR%201%3D1" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/128.0.0.0"
10.0.2.15 - - [16/Aug/2026:11:05:20 +0000] "GET /healthz HTTP/1.1" 200 2 "-" "kube-probe/1.29"
```

## Output contract

After your analysis, output a line containing exactly:

```
--- FINDINGS ---
```

Then output a JSON array. Each element must be an object of the form:

```json
{"type": "...", "location": "...", "evidence": "..."}
```

If you find no security issues, output an empty array `[]`.
