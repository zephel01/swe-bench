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
    再現するかどうかは seed だけでは決まらないことが実測で分かっている。

    実測 (2026-08-16 / Qwen3.8-27B Q5_K_M / seed=42 固定 / 同一 ctx・同一
    サンプリング・同一起動引数) の結果は次の2つに割れた。

    (a) **同じタスク集合を同じ順序で** 2回走らせた場合 (canary 6問 ×2)
        → 6問すべて llm_output・generated・quality まで完全一致。
          差は tok/s (106.9 → 109.9、+2.8%) と traceback 中のオブジェクト
          アドレスだけ。**再走ノイズはゼロ。**

    (b) **タスク集合を変えて** 同じ問を含めた場合 (フルL7 16問 vs canary 6問)
        → 6問中5問は一致したが、t095 だけが **63文字目から分岐**し、
          判定が NG → OK に反転した (完了トークン 23,437 → 29,271)。

    llama.cpp サーバはリクエストをまたいで KV キャッシュを保持し、前方一致
    した分を再計算しない。直前に流したタスクが違えばキャッシュの残り方が
    変わり、プロンプトの ubatch 分割が変わる。分割が変わればリダクションの
    順序が変わってビット単位では一致しない。近接した logit が1つ入れ替われば
    そこから先は全部変わる。

    運用上の帰結:

      ・**条件A/Bの比較は、タスク集合と順序を固定して行うこと。**
        固定すれば再走ノイズは 0 なので、観測された差は条件の差に帰属できる。
      ・ただし「条件の差に帰属できる」は「品質が変わった」ではない。
        起動引数を変えれば数値は必ず動くので、1問の反転は
        **サイコロを振り直した**のか**実力が変わった**のかを区別しない。
        品質を言うには seed を変えた複数ランで分布を見る必要がある。
      ・**タスク集合の違う結果同士 (canary とフルL7) を直接つなげないこと。**
      ・tok/s だけは決定的でない。実測ノイズは約 3%。
    """
    out = {k: getattr(client, k, None) for k in SAMPLING_KEYS}
    out["seed_sent"] = out.get("seed") is not None
    return out
