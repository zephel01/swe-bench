"""_ledgers() の台帳選択ロジックの単体テスト (ネットワーク不要)."""

from __future__ import annotations

from types import SimpleNamespace

from llmbench.cli import _ledgers


def _args(**kw):
    """SimpleNamespace で args を模擬。only_*/with_* は既定 False。"""
    base = {
        "only_l6": False,
        "only_l7": False,
        "with_l6": False,
        "with_l7": False,
        "l6_ledger": "tasks_l6.jsonl",
        "l7_ledger": "tasks_l7.jsonl",
    }
    base.update(kw)
    return SimpleNamespace(**base)


def test_ledgers_default():
    assert _ledgers(_args()) == ["tasks.jsonl"]


def test_ledgers_with_l6():
    assert _ledgers(_args(with_l6=True)) == ["tasks.jsonl", "tasks_l6.jsonl"]


def test_ledgers_with_l7():
    assert _ledgers(_args(with_l7=True)) == ["tasks.jsonl", "tasks_l7.jsonl"]


def test_ledgers_with_both():
    assert _ledgers(_args(with_l6=True, with_l7=True)) == [
        "tasks.jsonl", "tasks_l6.jsonl", "tasks_l7.jsonl",
    ]


def test_ledgers_only_l6():
    assert _ledgers(_args(only_l6=True)) == ["tasks_l6.jsonl"]


def test_ledgers_only_l7():
    assert _ledgers(_args(only_l7=True)) == ["tasks_l7.jsonl"]


def test_ledgers_only_both():
    assert _ledgers(_args(only_l6=True, only_l7=True)) == [
        "tasks_l6.jsonl", "tasks_l7.jsonl",
    ]


def test_ledgers_only_l6_with_l7():
    assert _ledgers(_args(only_l6=True, with_l7=True)) == [
        "tasks_l6.jsonl", "tasks_l7.jsonl",
    ]


def test_ledgers_only_l6_with_l6_no_dup():
    # --only-l6 と --with-l6 は同義。二重追加しない。
    assert _ledgers(_args(only_l6=True, with_l6=True)) == ["tasks_l6.jsonl"]


def test_ledgers_custom_ledger_name():
    # 台帳名を変更したら選択結果に反映される。
    args = _args(with_l6=True, with_l7=True,
                 l6_ledger="custom_l6.jsonl", l7_ledger="custom_l7.jsonl")
    assert _ledgers(args) == [
        "tasks.jsonl", "custom_l6.jsonl", "custom_l7.jsonl",
    ]
