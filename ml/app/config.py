import os
from pathlib import Path


def read_secret(name: str, fallback: str = "") -> str:
    """Docker Secret をファイルから読み取る。存在しない場合は環境変数にフォールバック。"""
    secret_path = Path(f"/run/secrets/{name}")
    if secret_path.exists():
        return secret_path.read_text().strip()
    return os.environ.get(name.upper(), fallback)
