# バグ: 相対的な日付表現が誤って解釈される

`parse(text, base)` は絶対 ISO 日付と `today`/`tomorrow`/`yesterday` は扱えるが、
相対表現が誤りか未対応。`base = 2026-06-26`（金曜）での例:

- `parse("next friday", base)` は `2026-07-03`（今日ではなく *翌週* の金曜）。
- `parse("next monday", base)` は `2026-06-29`。
- `parse("in 3 days", base)` は `2026-06-29`。
- 大文字小文字を区別しない（`"Next Monday"` も動く）。

これらの表現の妥当な意味論を考えること。絶対日付と today/tomorrow/yesterday は
既に動く。
