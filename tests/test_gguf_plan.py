"""gguf_plan の単位換算・ctx逆算・生成コマンドのテスト.

このスクリプトは2回間違えている:

  * **GB (÷10^9) と GiB (÷2^30) を混ぜた。**GGUF の size_gb はバイト÷10^9、
    GPU の「24GB」は GiB。混ぜると 24GiB カードに載るものを「溢れる」と誤判定する
  * **継続行 (\\) の途中に # コメントを書いた。**そこから行末までがコメントになり、
    \\ ごと消えて起動コマンドが途中で切れる

どちらも「出力が一見それらしい」ので気づきにくい。ここで固定する。
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "gguf_plan", Path(__file__).resolve().parent.parent / "gguf_plan.py")
gguf_plan = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(gguf_plan)

GIB = 1024 ** 3

#: 実測で確定した Qwen3.8-27B-Q5_K_M の gguf_probe 出力（必要な部分だけ）
Q5_K_M = {
    "file": "Qwen3.8-27B-Q5_K_M.gguf",
    "size_gb": 19.83,
    "context_length": 262144,
    "is_language_model": True,
    "chat_template_has_think": True,
    "mtp_tensor_count": 4,
    "is_hybrid_attention": True,
    "kv_layers": list(range(17)),
    "kv_cache": {"bytes_per_token_f16": 69632, "total_layers": 65},
}
NO_MTP = {**Q5_K_M, "mtp_tensor_count": 0, "mtp_tensors": []}
NO_THINK = {**Q5_K_M, "chat_template_has_think": False}


# --- 単位換算 ------------------------------------------------------------

def test_file_size_converted_from_gb_to_gib():
    """size_gb はバイト÷10^9。GPU の GiB と混ぜてはいけない.

    19.83 GB = 18.47 GiB。この 1.36 の差が「24GBに載るか」の判定を反転させる。
    """
    assert gguf_plan.file_gib(Q5_K_M) == pytest.approx(18.47, abs=0.01)
    assert gguf_plan.file_gib(Q5_K_M) < Q5_K_M["size_gb"]


def test_kv_size_in_gib_matches_hand_calculation():
    """68 KB/token x 65,536 = 4.25 GiB（4.56 GB ではない）."""
    assert gguf_plan.kv_gib(Q5_K_M, 65536, "f16") == pytest.approx(4.25, abs=0.01)
    assert gguf_plan.kv_gib(Q5_K_M, 65536, "f16") == pytest.approx(
        69632 * 65536 / GIB, abs=1e-6)


def test_q8_kv_is_about_half_of_f16():
    f16 = gguf_plan.kv_gib(Q5_K_M, 65536, "f16")
    q8 = gguf_plan.kv_gib(Q5_K_M, 65536, "q8_0")
    assert q8 == pytest.approx(f16 * gguf_plan.Q8_FACTOR, abs=1e-9)
    assert 0.5 < q8 / f16 < 0.6


def test_q5_k_m_fits_24gib_card_at_64k_f16():
    """実測の反例。GB/GiB を混ぜると「溢れる」と誤判定していたケース."""
    used = (gguf_plan.file_gib(Q5_K_M)
            + gguf_plan.kv_gib(Q5_K_M, 65536, "f16")
            + gguf_plan.DEFAULT_OVERHEAD_GIB)
    assert used < 24.0
    assert used == pytest.approx(23.72, abs=0.02)


def test_overhead_matches_the_single_measurement():
    """較正点: ファイル+KV = 22.72 GiB に対し llama-server の実測が 23.5 GiB.

    既定のオーバーヘッドは安全側なので、実測差 0.78 以上であること。
    """
    bare = gguf_plan.file_gib(Q5_K_M) + gguf_plan.kv_gib(Q5_K_M, 65536, "f16")
    assert bare == pytest.approx(22.72, abs=0.02)
    assert gguf_plan.DEFAULT_OVERHEAD_GIB >= 23.5 - bare


# --- ctx の逆算 ----------------------------------------------------------

def test_max_ctx_is_capped_by_native_context_length():
    """予算が余っていても native ctx を超えてはいけない（外挿は品質が壊れる）."""
    assert gguf_plan.max_ctx(Q5_K_M, vram_gib=100.0, kv_mode="f16",
                             overhead=1.0) == Q5_K_M["context_length"]


def test_max_ctx_is_floored_to_step():
    n = gguf_plan.max_ctx(Q5_K_M, vram_gib=24.0, kv_mode="f16", overhead=1.0)
    assert n % gguf_plan.CTX_STEP == 0
    assert n >= 65536       # 24GiB カードで 64k は確保できる


def test_q8_roughly_doubles_max_ctx():
    f16 = gguf_plan.max_ctx(Q5_K_M, 24.0, "f16", 1.0)
    q8 = gguf_plan.max_ctx(Q5_K_M, 24.0, "q8_0", 1.0)
    assert q8 > f16
    assert 1.7 < q8 / f16 < 2.1


def test_max_ctx_zero_when_model_alone_exceeds_budget():
    assert gguf_plan.max_ctx(Q5_K_M, vram_gib=8.0, kv_mode="f16", overhead=1.0) == 0
    assert gguf_plan.max_ctx(Q5_K_M, vram_gib=8.0, kv_mode="q8_0", overhead=1.0) == 0


def test_max_ctx_zero_without_kv_metadata():
    assert gguf_plan.max_ctx({"size_gb": 1.0}, 24.0, "f16", 1.0) == 0


# --- 勧める ctx は「きりのいい値」に丸める ------------------------------

def test_recommended_ctx_rounds_down_to_a_standard_value():
    """予算いっぱいの 69,632 をそのまま勧めてはいけない.

    余りが 0.02 GiB しか残らず、オーバーヘッドの見積り誤差 (較正点は1つ)
    で起動に失敗する。65,536 に対して context 6% 増しか得ていない。
    """
    cap = gguf_plan.max_ctx(Q5_K_M, 24.0, "f16", 1.0)
    rec = gguf_plan.recommended_ctx(Q5_K_M, 24.0, "f16", 1.0)
    assert cap == 69632
    assert rec == 65536
    assert rec in gguf_plan.STANDARD_CTX
    assert rec <= cap


def test_recommended_ctx_leaves_usable_headroom():
    ctx = gguf_plan.recommended_ctx(Q5_K_M, 24.0, "f16", 1.0)
    assert gguf_plan.headroom_gib(Q5_K_M, ctx, "f16", 24.0, 1.0) >= 0.2


def test_recommended_ctx_zero_when_nothing_fits():
    assert gguf_plan.recommended_ctx(Q5_K_M, 8.0, "f16", 1.0) == 0


def test_recommended_ctx_capped_by_native_even_with_huge_budget():
    assert gguf_plan.recommended_ctx(Q5_K_M, 500.0, "f16", 1.0) == 262144


def test_headroom_is_negative_when_it_does_not_fit():
    assert gguf_plan.headroom_gib(Q5_K_M, 262144, "f16", 24.0, 1.0) < 0


def test_thin_headroom_is_warned_in_the_output():
    """ぎりぎりの設定は、そうと書かないと事故になる."""
    out = gguf_plan.emit_config(Q5_K_M, 69632, "f16", vram=24.0, overhead=1.0,
                                model_path="/m/x.gguf", port=8085, device="CUDA0")
    assert "⚠️" in out
    assert "余り" in out
    assert "q8_0 にする" in out          # f16 なら q8_0 を勧める


def test_thin_headroom_does_not_suggest_q8_when_already_q8():
    out = gguf_plan.emit_config(Q5_K_M, 131072, "q8_0", vram=24.0, overhead=1.0,
                                model_path="/m/x.gguf", port=8085, device="CUDA0")
    assert "⚠️" in out
    assert "q8_0 にする" not in out      # 既に q8_0 なのに勧めては意味がない
    assert "ctx を1段下げる" in out


def test_comfortable_headroom_is_reported_plainly():
    out = gguf_plan.emit_config(Q5_K_M, 32768, "f16", vram=24.0, overhead=1.0,
                                model_path="/m/x.gguf", port=8085, device="CUDA0")
    assert "⚠️" not in out
    assert "余り" in out


# --- -m に書くパス ------------------------------------------------------

def test_model_path_uses_the_recorded_absolute_path():
    rec = {**Q5_K_M, "path": "/mnt/data/models/X/Qwen3.8-27B-Q5_K_M.gguf"}
    assert gguf_plan.model_path_of(rec, None) == rec["path"]


def test_model_path_override_wins():
    rec = {**Q5_K_M, "path": "/recorded/x.gguf"}
    assert gguf_plan.model_path_of(rec, "/override/y.gguf") == "/override/y.gguf"


def test_model_path_falls_back_for_old_json_without_path():
    """path キーが無い古い gguf.json でも壊れず、プレースホルダになる."""
    assert gguf_plan.model_path_of(Q5_K_M, None).endswith(Q5_K_M["file"])


# --- 生成される起動コマンド ----------------------------------------------

def emit(rec, ctx=65536, kv="f16"):
    return gguf_plan.emit_config(rec, ctx, kv, vram=24.0, overhead=1.0,
                                 model_path="/m/x.gguf", port=8085, device="CUDA0")


def test_continued_lines_never_contain_a_comment():
    """継続行の途中に # があるとコマンドが壊れる（初版の実バグ）."""
    for line in emit(Q5_K_M, kv="q8_0").splitlines():
        stripped = line.rstrip()
        if stripped.endswith("\\"):
            assert "#" not in stripped, f"継続行にコメントがある: {line!r}"


def test_emitted_command_is_valid_shell():
    import subprocess
    text = emit(Q5_K_M, kv="q8_0")
    start = next(i for i, ln in enumerate(text.splitlines())
                 if ln.startswith("llama-server"))
    cmd = []
    for line in text.splitlines()[start:]:
        cmd.append(line)
        if not line.rstrip().endswith("\\"):
            break
    r = subprocess.run(["bash", "-n"], input="\n".join(cmd),
                       text=True, capture_output=True)
    assert r.returncode == 0, r.stderr
    joined = " ".join(x.rstrip("\\").strip() for x in cmd)
    assert "--ctx-size 65536" in joined
    assert "-ctk q8_0 -ctv q8_0" in joined


def test_quantized_kv_always_ships_with_flash_attention():
    """-ctk/-ctv の量子化には -fa on が必須."""
    out = emit(Q5_K_M, kv="q8_0")
    assert "-ctk q8_0 -ctv q8_0" in out
    assert "-fa on" in out


def test_f16_does_not_emit_ctk_flags():
    """コマンドの**引数として** -ctk が出ないこと.

    余裕不足の注記の中で「KV を q8_0 にする (-ctk ...)」と提案することは
    あるので、本文全体の in 判定では区別できない。
    """
    out = emit(Q5_K_M, kv="f16")
    assert not any(ln.strip().startswith("-ctk") for ln in out.splitlines())


# --- MTP / サンプリングの出し分け ---------------------------------------

def _has_spec_type_arg(text: str) -> bool:
    """コマンドの**引数として** --spec-type が出ているか.

    注記コメントにも同じ文字列が現れるので、単純な in 判定では区別できない。
    """
    return any(ln.strip().startswith("--spec-type") for ln in text.splitlines())


def test_draft_mtp_emitted_when_mtp_tensors_exist():
    assert _has_spec_type_arg(emit(Q5_K_M))


def test_draft_mtp_omitted_when_no_mtp_tensors():
    out = emit(NO_MTP)
    assert not _has_spec_type_arg(out)
    assert "付けない" in out          # 理由は注記として残す


def test_thinking_template_gets_official_thinking_sampling():
    out = emit(Q5_K_M)
    assert "temperature: 1.0" in out
    assert "top_p: 0.95" in out
    assert "min_p: 0.0" in out


def test_non_thinking_template_gets_different_sampling():
    out = emit(NO_THINK)
    assert "temperature: 0.7" in out
    assert "top_p: 0.8" in out


def test_max_tokens_leaves_room_for_the_prompt():
    for ctx in (32768, 65536, 131072):
        out = emit(Q5_K_M, ctx=ctx)
        mt = int(next(ln for ln in out.splitlines()
                      if ln.strip().startswith("max_tokens:")
                      ).split(":")[1].split("#")[0].strip())
        assert mt < ctx, "max_tokens が ctx 以上だと実効上限は n_ctx - プロンプト長になる"
