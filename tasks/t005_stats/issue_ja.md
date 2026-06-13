# バグ: average() が空リストで ZeroDivisionError を送出する

`average([])` はdocstring通り 0.0 を返すべきですが、ZeroDivisionError になります。
