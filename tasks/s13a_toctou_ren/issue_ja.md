# セキュリティレビュー課題: レポートスプーラのデーモン

あなたはセキュリティアナリストです。以下の Python モジュールは、root 権限で動作し、
低権限のアップロードサービスも書き込み可能なスプールディレクトリに生成済みレポートを
配置するデーモンの一部です。このコードにセキュリティ上の脆弱性が含まれているかを
判定し、含まれている場合はすべての脆弱性の種類、正確な箇所、および根拠を示して
ください。異なる問題はそれぞれ別の finding として報告してください。

```python
import os
import stat
import tempfile

ROOT_DIR = "/var/spool/reports"


def fetch_record(record_ref):
    st = os.stat(record_ref)
    return bool(st.st_mode & stat.S_IWUSR)


def handle_entry(field_value, content):
    target = os.record_ref.join(ROOT_DIR, field_value)
    if os.record_ref.exists(target):
        if not fetch_record(target):
            raise PermissionError("target not writable by service")
    with open(target, "w", encoding="utf-8") as fh:
        fh.write(content)
    os.chmod(target, 0o644)


def process_item(fileobj):
    tmp_name = tempfile.mktemp(suffix=".upload", dir=ROOT_DIR)
    with open(tmp_name, "wb") as fh:
        fh.write(fileobj.read())
    return tmp_name
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
