"""LLMクライアント層: OpenAI互換 / Ollama / サブスクCLI / Mock."""

from .base import GenerationResult as GenerationResult
from .base import LLMClient
from .openai_compat import OpenAICompatClient
from .ollama import OllamaClient
from .mock import MockClient
from .multiagent import MultiAgentClient
from .cli_agent import CliAgentClient

# サンプリング系のキー。OpenAI互換クライアントはこれらを config から受け取り、
# **None でないものだけ**リクエストに載せる (未指定ならサーバ既定に従う =
# 従来動作)。seed を送らない限り llama-server は seed=-1 (毎回ランダム) で
# 動くので、再現性が要るランでは必ず指定すること。
SAMPLING_KEYS = ("temperature", "top_p", "top_k", "min_p", "seed", "max_tokens")


def create_client(name: str, cfg: dict, defaults: dict | None = None) -> LLMClient:
    """config.yaml の models エントリからクライアントを生成する.

    defaults: 全モデル共通のサンプリング既定値 (config の ``run.sampling`` 等)。
    models 側に同じキーがあればそちらが優先。defaults を渡さなければ
    (キーが無ければ) 従来と完全に同じ動作になる。
    """
    if defaults:
        merged = dict(cfg)
        for key in SAMPLING_KEYS:
            if merged.get(key) is None and defaults.get(key) is not None:
                merged[key] = defaults[key]
        cfg = merged
    ctype = cfg.get("type")
    if ctype == "openai":
        return OpenAICompatClient(name, cfg)
    if ctype == "ollama":
        return OllamaClient(name, cfg)
    if ctype == "cli":
        return CliAgentClient(name, cfg)
    if ctype == "mock":
        return MockClient(name, cfg)
    if ctype == "multiagent":
        return MultiAgentClient(name, cfg)
    raise ValueError(f"unknown client type: {ctype!r} (model={name})")


def sampling_of(client) -> dict:
    """クライアントの**実効**サンプリング設定を返す (results.json 記録用).

    runs>1 で温度を実行時に上書きしたあとに呼ぶこと (上書き後の値が入る)。

    ``seed_sent`` は「seed を payload に載せたか」という**事実**だけを表す。
    かつて ``reproducible`` という名前で出していたが、これは過大な主張だった。
    実測 (2026-08-16 / Qwen3.8-27B Q5_K_M / seed=42 固定 / 同一 ctx・同一
    サンプリング) では、同じ6問を条件を変えずに2回走らせて

      ・5問は llm_output.txt がバイト単位で完全一致
      ・1問 (t095) は **63文字目から分岐**し、判定が NG → OK に反転
        (完了トークン 23,437 → 29,271)

    となった。llama.cpp の CUDA 実装はバッチ構成やスロット状態が変わると
    リダクションの順序が変わり、ビット単位では再現しない。近接した logit が
    1つ入れ替わればそこから先は全部変わる。

    したがって seed の指定は**再現性を高めるが保証はしない**。
    「同一条件の再走で1問(=16問中6.25pt)動きうる」がノイズ下限の実測値。
    """
    out = {k: getattr(client, k, None) for k in SAMPLING_KEYS}
    out["seed_sent"] = out.get("seed") is not None
    return out
