# Operational Guide

## Deployment Procedures

### Production Deployment

1. **Pre-deployment Checklist**
```bash
# Run tests
pytest tests/

# Check configurations
python scripts/validate_configs.py

# Verify dependencies
poetry export -f requirements.txt
```

2. **Deployment Steps**
```bash
# Build container
docker build -t financial-pipeline:latest .

# Push to registry
docker push registry.company.com/financial-pipeline:latest

# Deploy to Kubernetes
kubectl apply -f k8s/
```

3. **Post-deployment Verification**
```bash
# Check pod status
kubectl get pods

# Check logs
kubectl logs -l app=financial-pipeline

# Verify metrics
curl http://monitoring-endpoint/metrics
```

## Backup and Recovery

### Database Backup

1. **InfluxDB Backup**
```bash
# Full backup
influx backup /path/to/backup

# Incremental backup
influx backup -start $(date -d '1 day ago') /path/to/backup
```

2. **Configuration Backup**
```bash
# Backup configs
cp -r configs/ /path/to/backup/configs

# Backup environments
cp .env /path/to/backup/.env
```

### Recovery Procedures

1. **Database Recovery**
```bash
# Restore from backup
influx restore /path/to/backup

# Verify restoration
influx query 'show measurements'
```

2. **Service Recovery**
```bash
# Restart services
docker-compose restart

# Check service health
docker-compose ps
```

## Scaling Guidelines

### Horizontal Scaling

1. **Add Processing Nodes**
```yaml
# docker-compose.scale.yaml
services:
  worker:
    image: financial-pipeline
    deploy:
      replicas: 3
```

2. **Database Scaling**
```yaml
# influxdb-cluster.yaml
apiVersion: apps/v1
kind: StatefulSet
spec:
  replicas: 3
```

### Performance Tuning

1. **Airflow Settings**
```python
# airflow.cfg
parallelism = 32
dag_file_processor_timeout = 600
```

2. **InfluxDB Optimization**
```toml
# influxdb.conf
cache-max-memory-size = "1g"
max-series-per-database = "1000000"
```

## Security Guidelines

### Access Control

1. **API Authentication**
```python
# Example API key rotation
def rotate_api_keys():
    """Rotate API keys periodically"""
    pass
```

2. **Database Access**
```sql
-- Create restricted user
CREATE USER readonly WITH PASSWORD 'secret'
WITH READ ON market_data
```

### Data Protection

1. **Encryption Settings**
```yaml
# security-config.yaml
encryption:
  at_rest: true
  in_transit: true
  key_rotation: 90d
```

2. **Audit Logging**
```python
# Example audit log
def audit_log(action: str, user: str, resource: str):
    """Log audit events"""
    pass
```

## Disaster Recovery

### Recovery Time Objectives

1. **Service Level Objectives**
```yaml
# slo-config.yaml
rto:
  critical: 1h
  high: 4h
  medium: 24h
```

2. **Recovery Steps**
```bash
# Example recovery script
#!/bin/bash
set -e

# Restore database
restore_database

# Verify data integrity
check_data_integrity

# Restart services
restart_services
```

### Failover Procedures

1. **Manual Failover**
```bash
# Switch to backup system
kubectl failover financial-pipeline

# Verify failover
kubectl get pods -w
```

2. **Automatic Failover**
```yaml
# ha-config.yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
spec:
  minAvailable: 2
```