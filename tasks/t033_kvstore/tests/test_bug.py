from store import KVStore


def test_commit_inner_then_outer_rollback_undoes_all():
    # 内側で書いてcommitしても、外側をrollbackすれば巻き戻るべき
    s = KVStore()
    s.begin()                 # 外側
    s.begin()                 # 内側
    s.set("a", 5)
    s.commit()                # 内側を解放 (変更は外側に属する)
    s.rollback()              # 外側を巻き戻す
    assert s.get("a") is None
