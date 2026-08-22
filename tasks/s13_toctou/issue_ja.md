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

SPOOL_DIR = "/var/spool/reports"


def is_writable_by_service(path):
    st = os.stat(path)
    return bool(st.st_mode & stat.S_IWUSR)


def publish_report(name, content):
    target = os.path.join(SPOOL_DIR, name)
    if os.path.exists(target):
        if not is_writable_by_service(target):
            raise PermissionError("target not writable by service")
    with open(target, "w", encoding="utf-8") as fh:
        fh.write(content)
    os.chmod(target, 0o644)


def stage_upload(fileobj):
    tmp_name = tempfile.mktemp(suffix=".upload", dir=SPOOL_DIR)
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
