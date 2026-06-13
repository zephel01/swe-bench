"""Prefix tree (trie)."""


class _Node:
    def __init__(self):
        self.children = {}


class Trie:
    def __init__(self):
        self.root = _Node()

    def insert(self, word):
        node = self.root
        for ch in word:
            node = node.children.setdefault(ch, _Node())
        # BUG: the end of a word is never marked

    def _find(self, s):
        node = self.root
        for ch in s:
            if ch not in node.children:
                return None
            node = node.children[ch]
        return node

    def search(self, word):
        # BUG: treats any reachable node as a stored word
        return self._find(word) is not None

    def starts_with(self, prefix):
        return self._find(prefix) is not None
