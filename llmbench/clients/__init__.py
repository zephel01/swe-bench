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
    seed が None のランは毎回サンプリングが変わるので reproducible=False。
    """
    out = {k: getattr(client, k, None) for k in SAMPLING_KEYS}
    out["reproducible"] = out.get("seed") is not None
    return out
