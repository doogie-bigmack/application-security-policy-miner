# Policy Miner Monitoring

This directory contains the monitoring setup for Policy Miner using Prometheus and Grafana.

## Architecture

- **Prometheus**: Scrapes metrics from the backend API at `/metrics` endpoint every 10 seconds
- **Grafana**: Visualizes metrics in dashboards with Prometheus as the datasource

## Services

### Prometheus
- **URL**: http://localhost:9090
- **Config**: `monitoring/prometheus/prometheus.yml`
- **Metrics endpoint**: Backend API at `http://backend:8000/metrics`

### Grafana
- **URL**: http://localhost:4000
- **Username**: `admin`
- **Password**: `admin`
- **Datasource**: Prometheus (auto-provisioned)
- **Dashboard**: Policy Miner Dashboard (auto-provisioned)

## Available Metrics

The following metrics are collected:

### Scan Metrics
- `policy_miner_scan_duration_seconds` - Histogram of scan durations
- `policy_miner_scans_total` - Counter of total scans by type and status
- `policy_miner_active_scans` - Gauge of currently active scans

### Policy Metrics
- `policy_miner_policies_extracted_total` - Counter of extracted policies by type
- `policy_miner_policies_total` - Gauge of total policies by status

### Repository Metrics
- `policy_miner_repositories_total` - Gauge of total repositories by type

### Error Metrics
- `policy_miner_errors_total` - Counter of errors by type and service

### API Metrics
- `policy_miner_api_requests_total` - Counter of API requests by method, endpoint, and status code
- `policy_miner_api_request_duration_seconds` - Histogram of API request durations

## Dashboard Features

The Policy Miner Dashboard includes:

1. **Overview Stats**: Total policies, repositories, active scans, error rate
2. **Scan Metrics**: Scan rate by type and status, scan duration percentiles
3. **Policy Metrics**: Policy extraction rate by type
4. **Error Analysis**: Error rate by type and service
5. **API Performance**: Request rate and duration percentiles

All panels update in real-time with a 10-second refresh interval.

## Accessing the Dashboard

1. Start all services:
   ```bash
   docker-compose up -d
   ```

2. Open Grafana:
   ```bash
   open http://localhost:4000
   ```

3. Login with:
   - Username: `admin`
   - Password: `admin`

4. Navigate to Dashboards → Policy Miner Dashboard

Or access directly:
```
http://localhost:4000/d/policy-miner-main/policy-miner-dashboard
```

## Alerting

You can set up alerting rules in Grafana based on the available metrics:

- Alert when error rate exceeds threshold
- Alert when scan duration is too high
- Alert when no scans have completed in X minutes
- Alert when active scans are stuck

## Exporting Dashboards

To export the dashboard for sharing:

1. Open the dashboard in Grafana
2. Click the "Share" button
3. Select "Export" tab
4. Choose "Save to file" or copy JSON

## Customization

### Adding New Metrics

1. Add metric collector in `backend/app/core/metrics.py`
2. Use the metric in your code
3. Metrics will automatically be scraped by Prometheus
4. Add new panels to the dashboard in Grafana UI
5. Export and save the updated dashboard JSON

### Modifying Scrape Interval

Edit `monitoring/prometheus/prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'policy-miner-backend'
    scrape_interval: 15s  # Change this value
```

Then restart Prometheus:
```bash
docker-compose restart prometheus
```
