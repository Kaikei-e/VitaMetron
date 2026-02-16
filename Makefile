.PHONY: up down build logs ps health init-secrets migrate-diff migrate-apply

# 起動
up:
	docker compose up -d

# 停止
down:
	docker compose down

# ビルド
build:
	docker compose build

# ログ
logs:
	docker compose logs -f

# ステータス
ps:
	docker compose ps

# ヘルスチェック
health:
	@echo "--- Postgres ---"
	@docker compose exec postgres pg_isready -U vitametron || echo "FAIL"
	@echo "\n--- Redis ---"
	@docker compose exec redis redis-cli ping || echo "FAIL"

# シークレット初期化 (初回セットアップ)
init-secrets:
	./init-secrets.sh

# Atlas マイグレーション
migrate-diff:
	atlas migrate diff --env local

migrate-apply:
	atlas migrate apply --env local
