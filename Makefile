.PHONY: up up-build restart restart-v restart-v-build recreate build down logs logs-web logs-worker ps

# Start (CPU)
up:
	docker compose up -d

# Build and start containers
up-build:
	docker compose up -d --build

restart:
	docker compose down && docker compose up -d

restart-v:
	docker compose down -v && docker compose up -d

restart-v-build:
	docker compose down -v && docker compose up -d --build

# Recreate containers (useful if Dockerfile changes)
recreate:
	docker compose up -d --force-recreate

# Build images (without starting containers)
build:
	docker compose build

down:
	docker compose down

logs:
	docker compose logs -f --tail=200

logs-web:
	docker compose logs -f web

logs-worker:
	docker compose logs -f worker

ps:
	docker compose ps
