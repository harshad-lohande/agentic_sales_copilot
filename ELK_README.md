# ELK Stack Configuration for Agentic Sales Copilot

This directory contains the configuration for the Elasticsearch, Logstash, and Kibana (ELK) stack that provides centralized logging and observability for the Agentic Sales Copilot application.

## Components

### 1. Elasticsearch
- **Port**: 9200
- **Purpose**: Data storage and search engine for logs
- **Configuration**: Single-node setup with basic security disabled for development
- **Volume**: Persistent data storage in `elasticsearch_data`

### 2. Logstash
- **Port**: 5044 (Beats input), 9600 (Monitoring API)
- **Purpose**: Log processing and enrichment pipeline
- **Configuration**: Enhanced pipeline with ECS compliance and content redaction
- **Features**:
  - JSON log parsing
  - ECS-compliant field mapping
  - Content redaction for sensitive data
  - Error classification
  - Enhanced filtering and enrichment

### 3. Kibana
- **Port**: 5601
- **Purpose**: Log visualization and dashboards
- **Configuration**: Connected to Elasticsearch for data exploration

### 4. Filebeat
- **Purpose**: Log shipping from Docker containers
- **Configuration**: Auto-discovery of containers with `logging: "true"` label
- **Features**:
  - Docker metadata enrichment
  - JSON log processing
  - Structured log forwarding to Logstash

## File Structure

```
├── docker-compose.yml          # Main orchestration file
├── logstash/
│   ├── pipeline/
│   │   └── logstash.conf      # Logstash pipeline configuration
│   └── logstash.yml           # Logstash service configuration
├── filebeat/
│   ├── Dockerfile             # Custom Filebeat image
│   └── filebeat.yml           # Filebeat configuration
└── elasticsearch/
    └── index-template.json    # Elasticsearch index template
```

## Features Implemented

### 1. Enhanced Logstash Pipeline
- **ECS Compliance**: Fields mapped to Elastic Common Schema
- **Content Redaction**: Sensitive content automatically redacted
- **Error Classification**: Automatic error detection and routing
- **Correlation ID Tracking**: Request tracing across services
- **Structured Field Mapping**: Application-specific fields properly structured

### 2. Network Configuration
- **Custom Network**: All services on dedicated `elk-network`
- **Service Discovery**: Container-to-container communication via hostnames
- **Health Checks**: Proper startup ordering and health monitoring

### 3. Performance Optimizations
- **Connection Pooling**: Optimized Elasticsearch output settings
- **Retry Logic**: Robust error handling and connection recovery
- **Batch Processing**: Efficient log processing with proper batching

### 4. Security & Privacy
- **Content Masking**: Automatic redaction of sensitive fields
- **Health Check Filtering**: Noise reduction by filtering health checks
- **Structured Logging**: Enhanced security through proper field structuring

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

### Viewing Logs
```bash
# Check service logs
docker compose logs elasticsearch
docker compose logs logstash
docker compose logs kibana

# Follow logs in real-time
docker compose logs -f logstash
```

## Index Patterns

The system creates two main indices:
- `agentic-sales-copilot`: Regular application logs
- `agentic-sales-copilot-error`: Error logs for enhanced monitoring

## Field Mapping

Key fields are mapped to ECS-compliant structure:
- `@timestamp`: Event timestamp
- `log.level`: Log level (INFO, ERROR, etc.)
- `service.name`: Service identifier
- `correlation.id`: Request correlation ID
- `prospect.email`: Customer email (when applicable)
- `email.classification`: Email classification result
- `slack.*`: Slack integration fields
- `http.response.status_code`: HTTP response codes

## Troubleshooting

### Common Issues

1. **Logstash Connection Issues**
   - Check if Elasticsearch is healthy: `docker compose ps`
   - Verify network connectivity: `docker network inspect agentic_sales_copilot_elk-network`

2. **Configuration Validation**
   - Test Logstash config: `docker run --rm -v $(pwd)/logstash/pipeline:/usr/share/logstash/pipeline:ro docker.elastic.co/logstash/logstash:8.11.3 bin/logstash --config.test_and_exit`

3. **Index Template Issues**
   - Apply template manually: `curl -X PUT "localhost:9200/_index_template/agentic-sales-copilot" -H "Content-Type: application/json" -d @elasticsearch/index-template.json`

### Monitoring

Check service health:
```bash
# Elasticsearch cluster health
curl -s "localhost:9200/_cluster/health?pretty"

# Logstash node info
curl -s "localhost:9600/_node/stats?pretty"

# Container health status
docker compose ps
```

## Development Notes

- Security is disabled in development mode for ease of use
- For production deployment, enable X-Pack security features
- Consider implementing ILM (Index Lifecycle Management) for log retention
- Add monitoring and alerting for production environments

## Maintenance

### Log Rotation
- Implement ILM policies for automatic log rotation
- Monitor disk usage and set appropriate retention policies

### Performance Tuning
- Adjust JVM heap sizes based on log volume
- Configure appropriate shard and replica settings
- Monitor resource usage and scale as needed