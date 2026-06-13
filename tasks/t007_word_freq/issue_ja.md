# バグ: word_frequencies() が大文字小文字を区別し記号も残す

docstringでは大文字小文字を無視し記号を除去して数えるとありますが、
`word_frequencies("Dog dog DOG.")` は `{"dog": 3}` ではなく
`Dog`, `dog`, `DOG.` の3つの別キーを返します。
