.PHONY: up up-build restart restart-v restart-v-build recreate build down logs logs-web logs-worker logs-elasticsearch logs-logstash logs-kibana logs-filebeat ps validate-elk test-log test-error-log

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

logs-elasticsearch:
	docker compose logs -f elasticsearch

logs-logstash:
	docker compose logs -f logstash

logs-kibana:
	docker compose logs -f kibana

logs-filebeat:
	docker compose logs -f filebeat

ps:
	docker compose ps

# Command to validate the ELK stack
validate-elk:
	@echo "--- Waiting 10 seconds for logs to be processed... ---"
	@sleep 10
	@echo "\n--- Checking for index creation... ---"
	@curl -s 'http://localhost:9200/_cat/indices?v' | grep "agentic-sales-copilot" || echo "No 'agentic-sales-copilot' indices found yet."
	@echo "\n--- Counting documents in indices... ---"
	@curl -s -X GET "http://localhost:9200/agentic-sales-copilot*/_count?pretty" -H 'Content-Type: application/json'
	@echo "\n--- Fetching the latest log entry... ---"
	@curl -s -X GET "http://localhost:9200/agentic-sales-copilot*/_search" -H 'Content-Type: application/json' -d '{"sort":[{"@timestamp":{"order":"desc"}}],"size":1}' | jq .

# Command to insert a test log (for development/testing purposes)
test-log:
	@echo "--- Inserting a custom INFO log via the test endpoint... ---"
	@curl -s -X GET http://localhost:8000/test/generate-log
	@echo "\n--- Log inserted. Run 'make validate-elk' to verify. ---"

# Command to insert a test error log (for development/testing purposes)
test-error-log:
	@echo "--- Inserting a custom ERROR log via the test endpoint... ---"
	@curl -s -X GET "http://localhost:8000/test/generate-log?level=error"
	@echo "\n--- Error log inserted. Run 'make validate-elk' to verify. You should now see an error index. ---"