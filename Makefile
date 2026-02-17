.PHONY: up down build logs ps health init-secrets migrate-up migrate-down migrate-status migrate-create

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

# goose マイグレーション (ローカル開発用)
MIGRATIONS_DIR := api/infrastructure/database/migrations
DATABASE_URL ?= postgres://vitametron:$$(cat secrets/db_password)@localhost:5432/vitametron?sslmode=disable

migrate-up:
	goose -dir $(MIGRATIONS_DIR) postgres "$(DATABASE_URL)" up

migrate-down:
	goose -dir $(MIGRATIONS_DIR) postgres "$(DATABASE_URL)" down

migrate-status:
	goose -dir $(MIGRATIONS_DIR) postgres "$(DATABASE_URL)" status

migrate-create:
	goose -dir $(MIGRATIONS_DIR) -s create $(name) sql
