# セキュリティレビュー課題: Web アクセスログの解析

あなたは EC アプリケーションを調査しているセキュリティアナリストです。以下は
nginx のアクセスログの抜粋です。ログを解析し、攻撃の痕跡があるかを判定して
ください。ある場合は、攻撃の種類、ログ上の該当箇所 (攻撃元および該当リクエスト)、
および根拠を示してください。

```text
203.0.113.10 - - [14/Aug/2026:02:13:41 +0000] "GET /api/items?id=7 HTTP/1.1" 200 511 "-" "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605.1.15"
198.51.100.23 - - [14/Aug/2026:02:14:07 +0000] "GET /api/items?id=1 HTTP/1.1" 200 512 "-" "python-requests/2.31.0"
10.0.2.15 - - [14/Aug/2026:02:15:00 +0000] "GET /healthz HTTP/1.1" 200 2 "-" "kube-probe/1.29"
198.51.100.23 - - [14/Aug/2026:02:14:08 +0000] "GET /api/items?id=1%27 HTTP/1.1" 500 217 "-" "python-requests/2.31.0"
198.51.100.23 - - [14/Aug/2026:02:14:09 +0000] "GET /api/items?id=1%20AND%201=1 HTTP/1.1" 200 512 "-" "python-requests/2.31.0"
66.249.66.1 - - [14/Aug/2026:02:15:03 +0000] "GET /sitemap.xml HTTP/1.1" 200 4821 "-" "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
198.51.100.23 - - [14/Aug/2026:02:14:10 +0000] "GET /api/items?id=1%20AND%201=2 HTTP/1.1" 200 31 "-" "python-requests/2.31.0"
10.0.2.15 - - [14/Aug/2026:02:14:10 +0000] "GET /healthz HTTP/1.1" 200 2 "-" "kube-probe/1.29"
203.0.113.10 - - [14/Aug/2026:02:15:11 +0000] "GET /static/app.9f2c.css HTTP/1.1" 304 0 "https://shop.example.com/" "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605.1.15"
198.51.100.23 - - [14/Aug/2026:02:14:12 +0000] "GET /api/items?id=1%20UNION%20SELECT%20NULL HTTP/1.1" 500 217 "-" "python-requests/2.31.0"
198.51.100.23 - - [14/Aug/2026:02:14:13 +0000] "GET /api/items?id=1%20UNION%20SELECT%20NULL,NULL HTTP/1.1" 500 217 "-" "python-requests/2.31.0"
203.0.113.10 - - [14/Aug/2026:02:15:12 +0000] "GET /static/legacy-print.css HTTP/1.1" 404 153 "https://shop.example.com/" "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605.1.15"
198.51.100.23 - - [14/Aug/2026:02:14:14 +0000] "GET /api/items?id=1%20UNION%20SELECT%20NULL,NULL,NULL HTTP/1.1" 200 540 "-" "python-requests/2.31.0"
203.0.113.10 - - [14/Aug/2026:02:14:15 +0000] "POST /cart/add HTTP/1.1" 302 0 "https://shop.example.com/items/7" "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605.1.15"
198.51.100.23 - - [14/Aug/2026:02:14:16 +0000] "GET /api/items?id=1%20UNION%20SELECT%20table_name,NULL,NULL%20FROM%20information_schema.tables HTTP/1.1" 200 8241 "-" "python-requests/2.31.0"
198.51.100.23 - - [14/Aug/2026:02:14:21 +0000] "GET /api/items?id=1%20UNION%20SELECT%20username,password_hash,NULL%20FROM%20users HTTP/1.1" 200 264913 "-" "python-requests/2.31.0"
10.0.2.15 - - [14/Aug/2026:02:14:20 +0000] "GET /healthz HTTP/1.1" 200 2 "-" "kube-probe/1.29"
203.0.113.10 - - [14/Aug/2026:02:14:33 +0000] "GET /orders HTTP/1.1" 200 4187 "-" "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605.1.15"
```

## 出力仕様

分析の後、次の行を正確に 1 行出力してください:

```
--- FINDINGS ---
```

続けて JSON 配列を出力してください。各要素は次の形式のオブジェクトです:

```json
{"type": "...", "location": "...", "evidence": "..."}
```

セキュリティ上の問題が見つからない場合は、空配列 `[]` を出力してください。
