"""Prefix tree (trie)."""


class _Node:
    def __init__(self):
        self.children = {}
        self.is_word = False


class Trie:
    def __init__(self):
        self.root = _Node()

    def insert(self, word):
        node = self.root
        for ch in word:
            node = node.children.setdefault(ch, _Node())
        node.is_word = True

    def _find(self, s):
        node = self.root
        for ch in s:
            if ch not in node.children:
                return None
            node = node.children[ch]
        return node

    def search(self, word):
        node = self._find(word)
        return node is not None and node.is_word

    def starts_with(self, prefix):
        return self._find(prefix) is not None
