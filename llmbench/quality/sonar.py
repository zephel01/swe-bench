"""SonarQube連携 (任意・v1は最小実装).

SonarQubeサーバ + sonar-scanner CLI が必要。enabled: false が既定。
スコア = 100 - (BLOCKER*20 + CRITICAL*10 + MAJOR*5 + MINOR*2 + INFO*0.5)
"""

from __future__ import annotations

import shutil
import subprocess
import time
import uuid
from pathlib import Path

import requests

SEVERITY_PENALTY = {
    "BLOCKER": 20, "CRITICAL": 10, "MAJOR": 5, "MINOR": 2, "INFO": 0.5,
}


def sonar_score(workspace: Path, cfg: dict) -> tuple[float | None, dict]:
    host = cfg.get("host_url", "http://localhost:9000")
    token = cfg.get("token", "")
    if not token:
        return None, {"reason": "sonarqube token not set"}
    if shutil.which("sonar-scanner") is None:
        return None, {"reason": "sonar-scanner not found in PATH"}

    project_key = f"llmbench_{uuid.uuid4().hex[:8]}"
    proc = subprocess.run(
        ["sonar-scanner",
         f"-Dsonar.projectKey={project_key}",
         f"-Dsonar.sources={workspace}",
         f"-Dsonar.host.url={host}",
         f"-Dsonar.token={token}",
         "-Dsonar.scm.disabled=true"],
        capture_output=True, text=True, timeout=300,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"sonar-scanner failed: {proc.stderr[-300:]}")

    # 解析完了待ち (簡易ポーリング)
    issues = _poll_issues(host, token, project_key)
    penalty = sum(
        SEVERITY_PENALTY.get(i.get("severity", "INFO"), 0.5) for i in issues
    )
    score = max(0.0, 100.0 - penalty)
    by_sev: dict[str, int] = {}
    for i in issues:
        by_sev[i.get("severity", "INFO")] = by_sev.get(i.get("severity"), 0) + 1
    return score, {"issues": len(issues), "by_severity": by_sev,
                   "project_key": project_key}


def _poll_issues(host: str, token: str, project_key: str,
                 retries: int = 10, wait: float = 3.0) -> list[dict]:
    for _ in range(retries):
        time.sleep(wait)
        resp = requests.get(
            f"{host}/api/issues/search",
            params={"componentKeys": project_key, "ps": 500},
            auth=(token, ""), timeout=30,
        )
        if resp.ok:
            data = resp.json()
            if data.get("issues") is not None:
                return data["issues"]
    return []
