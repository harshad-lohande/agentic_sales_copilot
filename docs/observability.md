# ELK Observability Guide

This document provides comprehensive details on the observability and monitoring stack for Agentic Sales Co‑Pilot. It covers components, file structure, features, usage, validation, mappings, and troubleshooting.

---

## Versions and Components

- Elasticsearch: 8.19.3
- Logstash: 8.19.3
- Kibana: 8.19.3
- Filebeat
- Docker Compose orchestrates all services.

### Component Responsibilities

- Filebeat
  - Tails Docker JSON log files under `/var/lib/docker/containers/*/*.log`.
  - Adds Docker metadata and standard fields.
  - Filters to only harvest containers labeled `logging: "true"`.
  - Optionally decodes JSON application logs before forwarding.
  - For this project we use autodiscover (or a static container input) to collect per‑container logs and forward to Logstash.

- Logstash
  - Receives events from Filebeat on port 5044.
  - Parses the JSON message.
  - Enriches fields (service, correlation, prospect, email classification, Slack metadata).
  - Redacts long/sensitive content fields (stores content lengths for analytics).
  - Flags errors based on log level.
  - Routes events to daily indices in Elasticsearch:
    - `agentic-sales-copilot-YYYY.MM.DD`
    - `agentic-sales-copilot-error-YYYY.MM.DD`

- Elasticsearch
  - Stores log events in daily indices.
  - Provides REST API for search and analytics.

- Kibana
  - UI for search, dashboards, and monitoring.
  - Define data views, visualize fields, and build dashboards.

---

## File Structure

Project paths relevant to observability:

```
├── docker-compose.yml          # Main orchestration file
├── logstash/
│   ├── pipeline/
│   │   └── logstash.conf      # Logstash pipeline configuration
│   └── logstash.yml           # Logstash service configuration
├── filebeat/
    ├── Dockerfile             # Custom Filebeat image
    └── filebeat.yml           # Filebeat configuration
```

- filebeat/Dockerfile
  - Builds from `docker.elastic.co/beats/filebeat:8.11.3`
  - Copies `filebeat.yml` into the image
  - Runs as root (via compose) to read container logs

- filebeat/filebeat.yml (Autodiscover, container input)
  - Autodiscover provider: `type: docker`
  - Template applies for containers labeled `logging: "true"`
  - Input: `type: container`, `stream: all`, `paths: /var/lib/docker/containers/${data.docker.container.id}/*.log`
  - Processors: add fields, decode JSON, add docker/host metadata, drop temp fields
  - Output: Logstash at `logstash:5044`

- logstash/logstash.yml
  - Basic runtime tuning and disables X‑Pack monitoring
  - ECS compatibility: v8

- logstash/pipeline/logstash.conf (Core parsing/enrichment)
  - Input: beats on 5044
  - Filter pipeline:
    - `json` parse to `parsed`
    - Copy selected fields to top‑level and ECS structures
    - Add service metadata
    - Build `conversation.thread_id`
    - Normalize boolean fields
    - Redact content fields (`draft_reply`, `edited_text`, `body`, `conversation_history`)
    - Set error flag, convert to boolean
    - Drop health check noise
    - Add processing metadata
  - Output:
    - If `is_error == true`: `agentic-sales-copilot-error-%{+YYYY.MM.dd}`
    - Else: `agentic-sales-copilot-%{+YYYY.MM.dd}`

- docker-compose.yml
  - Brings up Elasticsearch, Logstash, Kibana, Filebeat, Postgres, Redis, Web, Worker
  - Includes health checks and necessary mounts for Filebeat:
    - `/var/run/docker.sock:/var/run/docker.sock:ro`
    - `/var/lib/docker/containers:/var/lib/docker/containers:ro`

---

## Features Implemented

- Centralized logging across all containers with per‑container filtering via label `logging: "true"`.
- Structured log parsing with JSON decoding.
- ECS‑ish field normalization:
  - `log.level`, `service.name`, `service.version`, `correlation.id`
  - `prospect.email`, `prospect.subject`
  - `email.classification`, `email.research_performed` (boolean)
  - `http.response.status_code`
  - `slack.action_id`, `slack.user`, `slack.channel_id`
- Content redaction for sensitive / long fields, while retaining `[content].[field].length`.
- Error detection and routing to error index.
- Daily indices (`YYYY.MM.DD`) for both main and error logs.
- Health checks for robust startup.

---

## Usage

### Starting the ELK Stack
```bash
# Start all services
docker compose up -d

# Start individual services
docker compose up -d elasticsearch
docker compose up -d logstash
docker compose up -d kibana
```

### Accessing Services
- **Kibana Dashboard**: http://localhost:5601
- **Elasticsearch API**: http://localhost:9200
- **Logstash Monitoring**: http://localhost:9600


### Generate Traffic

```
# Health
curl -i http://localhost:8000/health

# Inbound email webhook (simulate)
curl -X POST \
  -F 'from=Test User <test@example.com>' \
  -F 'subject=Test Subject' \
  -F 'text=Hello body test' \
  http://localhost:8000/webhook/inbound-email
```

### Validate Elasticsearch

```
# Indices
curl -s http://localhost:9200/_cat/indices/agentic-sales-copilot*?v

# Counts
curl -s http://localhost:9200/agentic-sales-copilot-*/_count
curl -s http://localhost:9200/agentic-sales-copilot-error-*/_count

# Sample document
curl -s http://localhost:9200/agentic-sales-copilot-*/_search?size=1 | jq .
```

### Kibana

- URL: http://localhost:5601
- Create Data Views:
  - Name: Main Logs; Pattern: `agentic-sales-copilot-*`; Time field: `@timestamp`
  - Name: Error Logs; Pattern: `agentic-sales-copilot-error-*`; Time field: `@timestamp`
- Suggested columns:
  - `@timestamp`, `log.level`, `service.name`, `correlation.id`,
  - `prospect.email`, `prospect.subject`,
  - `email.classification`, `email.research_performed`,
  - `http.response.status_code`,
  - `content.body.length`

---

## Index Patterns

- Main: `agentic-sales-copilot-*`
- Errors: `agentic-sales-copilot-error-*`

Daily index naming (examples):
- `agentic-sales-copilot-2025.09.12`
- `agentic-sales-copilot-error-2025.09.12`

---

## Field Mapping (Representative)

While we rely on dynamic mapping, the following fields are commonly present:

- `@timestamp` (date)
- `log.level` (keyword)
- `service.name` (keyword)
- `service.version` (keyword)
- `correlation.id` (keyword)
- `prospect.email` (keyword)
- `prospect.subject` (text/keyword)
- `email.classification` (keyword)
- `email.research_performed` (boolean)
- `http.response.status_code` (long)
- `slack.action_id` (keyword)
- `slack.user` (keyword)
- `slack.channel_id` (keyword)
- `content.body.length` (long)
- `content.draft_reply.length` (long)
- `event.ingested` (date)
- `event.timezone_offset` (keyword)
- `is_error` (boolean)
- Docker metadata (under `container.*`, `docker.*`, `host.*`, etc.)

---

## Monitoring

- Logstash node API:
  ```
  curl -s http://localhost:9600/_node/pipelines/main?pretty
  ```
- Elasticsearch health:
  ```
  curl -s http://localhost:9200/_cluster/health?pretty
  ```
- Compose logs:
  ```
  docker compose logs -f filebeat
  docker compose logs -f logstash
  docker compose logs -f elasticsearch
  ```

---

## Troubleshooting

1) Filebeat has 0 harvesters
- Ensure mounts exist inside Filebeat:
  ```
  docker exec -it filebeat ls /var/lib/docker/containers | head
  ```
- Confirm running as root:
  ```
  docker exec -it filebeat id
  ```
- Check label on app containers:
  ```
  docker inspect fastapi_webhook_server | grep -i '"logging"'
  ```
- Increase Filebeat logging:
  ```
  logging.level: debug
  ```

2) Logstash won’t start
- Validate config:
  ```
  docker exec -it logstash /usr/share/logstash/bin/logstash -t
  ```
- Review logs:
  ```
  docker compose logs -f logstash
  ```

3) Indices not created / counts stay zero
- Generate fresh events (webhook).
- Check Filebeat → Logstash connectivity (Filebeat output status).
  ```
  docker exec -it filebeat filebeat test output
  ```
- Temporarily enable stdout in Logstash output:
  ```
  # stdout { codec => rubydebug }
  ```

4) Docker Desktop (macOS/Windows)
- The host path `/var/lib/docker/containers` is not available natively.
- Prefer running on Linux or tailor inputs to bind‑mounted app logs.
- If using macOS/Windows, consider Elastic Agent or an alternate approach.

---

## Sample Queries

Recent events (main index):
```
GET agentic-sales-copilot-*/_search
{
  "size": 10,
  "sort": [{"@timestamp": "desc"}]
}
```

Errors only:
```
GET agentic-sales-copilot-error-*/_search
{
  "query": { "match_all": {} },
  "size": 10,
  "sort": [{"@timestamp": "desc"}]
}
```

Filter by correlation ID:
```
GET agentic-sales-copilot-*/_search
{
  "query": {
    "term": { "correlation.id.keyword": "3b890da2-f30d-43dc-976a-ace43eca3e99" }
  },
  "size": 10
}
```

---

## Security Notes

- xpack.security is disabled in development for convenience.
- For production:
  - Enable TLS and auth for Elasticsearch, Logstash, Kibana, and Beats.
  - Restrict network exposure.
  - Consider ILM, explicit index templates, and RBAC.
- Add monitoring and alerting for production environments

---

## Maintenance

### Log Rotation
- Implement ILM policies for automatic log rotation
- Monitor disk usage and set appropriate retention policies

### Performance Tuning
- Adjust JVM heap sizes based on log volume
- Configure appropriate shard and replica settings
- Monitor resource usage and scale as needed

---

## Appendix: Quick Reference Commands

```
# Indices
curl -s http://localhost:9200/_cat/indices/agentic-sales-copilot*?v

# Counts
curl -s http://localhost:9200/agentic-sales-copilot-*/_count
curl -s http://localhost:9200/agentic-sales-copilot-error-*/_count

# Sample doc
curl -s http://localhost:9200/agentic-sales-copilot-*/_search?size=1 | jq .

# Logstash pipeline state
curl -s http://localhost:9600/_node/pipelines/main?pretty
```

---