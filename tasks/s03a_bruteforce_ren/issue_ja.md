# セキュリティレビュー課題: SSH 認証ログの分析

あなたは Linux サーバーを調査しているセキュリティアナリストです。以下は
`/var/log/auth.log` の抜粋です。このログを分析し、攻撃の痕跡が示されているかを
判定してください。示されている場合は、攻撃の種類、ログ上の箇所（攻撃元および該当する
タイムスタンプ）、および根拠を示してください。

```text
Sep 02 21:41:02 app07 sshd[20431]: Failed password for root from 198.51.100.212 port 51422 ssh2
Sep 02 21:41:03 app07 sshd[20431]: Failed password for root from 198.51.100.212 port 51424 ssh2
Sep 02 21:41:05 app07 sshd[20433]: Failed password for root from 198.51.100.212 port 51430 ssh2
Sep 02 21:41:06 app07 sshd[20433]: Failed password for operator from 198.51.100.212 port 51438 ssh2
Sep 02 21:41:08 app07 sshd[20435]: Failed password for operator from 198.51.100.212 port 51444 ssh2
Sep 02 21:41:09 app07 sshd[20435]: Failed password for invalid user mysql from 198.51.100.212 port 51450 ssh2
Sep 02 21:41:11 app07 sshd[20437]: Failed password for invalid user redis from 198.51.100.212 port 51458 ssh2
Sep 02 21:41:12 app07 sshd[20437]: Failed password for svcops from 198.51.100.212 port 51466 ssh2
Sep 02 21:41:14 app07 sshd[20439]: Failed password for svcops from 198.51.100.212 port 51472 ssh2
Sep 02 21:41:15 app07 sshd[20439]: Failed password for svcops from 198.51.100.212 port 51480 ssh2
Sep 02 21:41:17 app07 sshd[20441]: Failed password for svcops from 198.51.100.212 port 51488 ssh2
Sep 02 21:41:18 app07 sshd[20441]: Failed password for svcops from 198.51.100.212 port 51494 ssh2
Sep 02 21:41:20 app07 sshd[20443]: Failed password for svcops from 198.51.100.212 port 51502 ssh2
Sep 02 21:41:21 app07 sshd[20443]: Failed password for svcops from 198.51.100.212 port 51510 ssh2
Sep 02 21:41:23 app07 sshd[20445]: Failed password for svcops from 198.51.100.212 port 51518 ssh2
Sep 02 21:41:24 app07 sshd[20445]: Accepted password for svcops from 198.51.100.212 port 51526 ssh2
Sep 02 21:41:24 app07 sshd[20445]: pam_unix(sshd:session): session opened for user svcops by (uid=0)
Sep 02 21:42:40 app07 sshd[20460]: Received disconnect from 198.51.100.212 port 51526:11: disconnected by user
```

同一の送信元 IP が繰り返し出現しています。失敗した試行回数を数え、シーケンスの
最後で何が起きているかに注目してください。

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
