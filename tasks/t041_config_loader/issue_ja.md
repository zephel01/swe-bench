# バグ: config のレイヤリングが2点で誤り

`load_config(env, file_config)` は3ソースを統合する。誤りは2つ:

- **優先順位**: キーが file と env の両方にあると file が勝つ。正しくは
  **env > file > defaults**。
- **型変換**: *file* レイヤ由来の値が生の文字列のまま。env 値しか変換されない。
  型付き既定を持つキーの値は、どのレイヤ由来でも `int`/`bool`/`float` に変換すべき。

defaults のみ・env のみの override は既に動く。
