# バグ: log_sum_exp が大きい/非常に小さい入力でクラッシュ・異常値を返す

`log_sum_exp(xs)` は `log(sum(exp(x) for x in xs))` を返す必要がある。小さな入力
では動くが、絶対値が大きくなると破綻する。

失敗例:

    log_sum_exp([1000.0, 1000.0])     # OverflowError（期待値 1000 + log(2)）
    log_sum_exp([-1000.0, -1000.0])   # "math domain error"（期待値 -1000 + log(2)）
    log_sum_exp([710.0])              # OverflowError（期待値 710.0）

数学的にはこれら3つの答えはすべて有限の普通の数である。`log_sum_exp([0.0, 0.0])
== log(2)` のような小さな入力は既に正しく動作している。
