# バグ: is_palindrome() が大文字小文字や記号を無視しない

docstringでは大文字小文字・空白・記号を無視すると書かれていますが、
`is_palindrome("A man, a plan, a canal: Panama")` が False を返します。
すべて小文字の回文は正しく動作します。
