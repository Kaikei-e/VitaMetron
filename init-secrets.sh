#!/usr/bin/env bash
set -euo pipefail

SECRETS_DIR="./secrets"
mkdir -p "$SECRETS_DIR"

generate_if_missing() {
    local file="$SECRETS_DIR/$1"
    local generator="$2"
    if [ -f "$file" ] && [ -s "$file" ]; then
        echo "SKIP: $file already exists"
    else
        eval "$generator" > "$file"
        chmod 600 "$file"
        echo "CREATED: $file"
    fi
}

# 自動生成可能なシークレット
generate_if_missing "db_password"    "openssl rand -base64 32 | tr -d '\n'"
generate_if_missing "redis_password" "openssl rand -base64 32 | tr -d '\n'"
generate_if_missing "encryption_key" "openssl rand -base64 32 | tr -d '\n'"

# 手動入力が必要なシークレット
for secret in fitbit_client_id fitbit_client_secret; do
    file="$SECRETS_DIR/$secret"
    if [ ! -f "$file" ] || [ ! -s "$file" ]; then
        echo "TODO: $file — Fitbit Developer Console から取得して手動で書き込んでください"
        touch "$file"
        chmod 600 "$file"
    fi
done

echo ""
echo "Done. secrets/ ディレクトリを確認してください。"
