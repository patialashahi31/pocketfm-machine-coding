.PHONY: up down build logs ps restart load-test

up:
	docker compose up --build

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f

ps:
	docker compose ps

restart:
	docker compose down
	docker compose up --build

load-test:
	docker compose exec -T k6 k6 run /scripts/rate_limit.js
