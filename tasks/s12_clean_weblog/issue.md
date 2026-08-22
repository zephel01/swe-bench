# Security Review Task: Web Access Log Review

You are a security analyst reviewing a routine log excerpt from an e-commerce
application. Analyze the nginx access log below and decide whether it shows
evidence of a real attack or compromise. Only report genuine, demonstrable
security events — do not flag ordinary operational traffic.

```text
10.0.2.15 - - [15/Aug/2026:09:00:00 +0000] "GET /healthz HTTP/1.1" 200 2 "-" "kube-probe/1.29"
10.0.2.15 - - [15/Aug/2026:09:00:10 +0000] "GET /healthz HTTP/1.1" 200 2 "-" "kube-probe/1.29"
203.0.113.10 - - [15/Aug/2026:09:00:14 +0000] "GET /favicon.ico HTTP/1.1" 404 153 "https://shop.example.com/" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/128.0.0.0"
203.0.113.10 - - [15/Aug/2026:09:00:14 +0000] "GET /static/legacy-theme.css HTTP/1.1" 404 153 "https://shop.example.com/" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/128.0.0.0"
203.0.113.10 - - [15/Aug/2026:09:00:31 +0000] "POST /login HTTP/1.1" 401 78 "https://shop.example.com/login" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/128.0.0.0"
203.0.113.10 - - [15/Aug/2026:09:00:48 +0000] "POST /login HTTP/1.1" 200 512 "https://shop.example.com/login" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/128.0.0.0"
66.249.66.1 - - [15/Aug/2026:09:01:02 +0000] "GET /blog/spring-sale HTTP/1.1" 200 18422 "-" "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
66.249.66.1 - - [15/Aug/2026:09:01:09 +0000] "GET /blog/care-guide HTTP/1.1" 200 15330 "-" "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
10.0.2.15 - - [15/Aug/2026:09:01:20 +0000] "GET /healthz HTTP/1.1" 200 2 "-" "kube-probe/1.29"
203.0.113.10 - - [15/Aug/2026:09:01:44 +0000] "GET /orders?page=2 HTTP/1.1" 200 4187 "https://shop.example.com/orders" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/128.0.0.0"
198.51.100.77 - - [15/Aug/2026:09:02:03 +0000] "GET /api/report/daily HTTP/1.1" 500 217 "-" "internal-reporting/1.4"
198.51.100.77 - - [15/Aug/2026:09:02:35 +0000] "GET /api/report/daily HTTP/1.1" 200 91204 "-" "internal-reporting/1.4"
10.0.2.15 - - [15/Aug/2026:09:02:40 +0000] "GET /healthz HTTP/1.1" 200 2 "-" "kube-probe/1.29"
203.0.113.10 - - [15/Aug/2026:09:03:11 +0000] "POST /logout HTTP/1.1" 302 0 "https://shop.example.com/orders" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/128.0.0.0"
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
