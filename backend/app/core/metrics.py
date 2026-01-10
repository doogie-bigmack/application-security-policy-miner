"""
Prometheus metrics configuration and collectors.
"""
import structlog
from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, generate_latest

logger = structlog.get_logger()

# Create a custom registry (separate from the default)
metrics_registry = CollectorRegistry()

# Scan duration metrics
scan_duration_histogram = Histogram(
    'policy_miner_scan_duration_seconds',
    'Duration of policy scans in seconds',
    ['repository_id', 'scan_type'],
    registry=metrics_registry
)

# Policy extraction count metrics
policies_extracted_counter = Counter(
    'policy_miner_policies_extracted_total',
    'Total number of policies extracted',
    ['repository_id', 'policy_type'],
    registry=metrics_registry
)

# Scan count metrics
scans_total_counter = Counter(
    'policy_miner_scans_total',
    'Total number of scans performed',
    ['scan_type', 'status'],
    registry=metrics_registry
)

# Error rate metrics
errors_total_counter = Counter(
    'policy_miner_errors_total',
    'Total number of errors',
    ['error_type', 'service'],
    registry=metrics_registry
)

# Active scans gauge
active_scans_gauge = Gauge(
    'policy_miner_active_scans',
    'Number of currently active scans',
    registry=metrics_registry
)

# Repository count gauge
repositories_total_gauge = Gauge(
    'policy_miner_repositories_total',
    'Total number of registered repositories',
    ['repository_type'],
    registry=metrics_registry
)

# Policy count gauge
policies_total_gauge = Gauge(
    'policy_miner_policies_total',
    'Total number of policies in the system',
    ['status'],
    registry=metrics_registry
)

# API request metrics
api_requests_counter = Counter(
    'policy_miner_api_requests_total',
    'Total number of API requests',
    ['method', 'endpoint', 'status_code'],
    registry=metrics_registry
)

api_request_duration_histogram = Histogram(
    'policy_miner_api_request_duration_seconds',
    'Duration of API requests in seconds',
    ['method', 'endpoint'],
    registry=metrics_registry
)


def get_metrics() -> bytes:
    """
    Generate and return metrics in Prometheus format.

    Returns:
        bytes: Metrics in Prometheus exposition format
    """
    logger.info("metrics_requested")
    return generate_latest(metrics_registry)


def record_scan_duration(repository_id: str, scan_type: str, duration: float) -> None:
    """
    Record scan duration metric.

    Args:
        repository_id: ID of the repository
        scan_type: Type of scan (full, incremental, etc.)
        duration: Duration in seconds
    """
    scan_duration_histogram.labels(
        repository_id=repository_id,
        scan_type=scan_type
    ).observe(duration)
    logger.debug("scan_duration_recorded", repository_id=repository_id, scan_type=scan_type, duration=duration)


def increment_policies_extracted(repository_id: str, policy_type: str, count: int = 1) -> None:
    """
    Increment policies extracted counter.

    Args:
        repository_id: ID of the repository
        policy_type: Type of policy extracted
        count: Number of policies to increment by
    """
    policies_extracted_counter.labels(
        repository_id=repository_id,
        policy_type=policy_type
    ).inc(count)
    logger.debug("policies_extracted_incremented", repository_id=repository_id, policy_type=policy_type, count=count)


def increment_scan_count(scan_type: str, status: str) -> None:
    """
    Increment scan count.

    Args:
        scan_type: Type of scan (full, incremental, etc.)
        status: Status of scan (success, failure, etc.)
    """
    scans_total_counter.labels(
        scan_type=scan_type,
        status=status
    ).inc()
    logger.debug("scan_count_incremented", scan_type=scan_type, status=status)


def increment_error_count(error_type: str, service: str) -> None:
    """
    Increment error counter.

    Args:
        error_type: Type of error (validation, extraction, etc.)
        service: Service where error occurred
    """
    errors_total_counter.labels(
        error_type=error_type,
        service=service
    ).inc()
    logger.debug("error_count_incremented", error_type=error_type, service=service)


def set_active_scans(count: int) -> None:
    """
    Set the number of active scans.

    Args:
        count: Number of active scans
    """
    active_scans_gauge.set(count)
    logger.debug("active_scans_set", count=count)


def set_repositories_total(repository_type: str, count: int) -> None:
    """
    Set the total number of repositories.

    Args:
        repository_type: Type of repository
        count: Total count
    """
    repositories_total_gauge.labels(repository_type=repository_type).set(count)
    logger.debug("repositories_total_set", repository_type=repository_type, count=count)


def set_policies_total(status: str, count: int) -> None:
    """
    Set the total number of policies.

    Args:
        status: Policy status
        count: Total count
    """
    policies_total_gauge.labels(status=status).set(count)
    logger.debug("policies_total_set", status=status, count=count)


def record_api_request(method: str, endpoint: str, status_code: int, duration: float) -> None:
    """
    Record API request metrics.

    Args:
        method: HTTP method
        endpoint: API endpoint
        status_code: HTTP status code
        duration: Request duration in seconds
    """
    api_requests_counter.labels(
        method=method,
        endpoint=endpoint,
        status_code=str(status_code)
    ).inc()

    api_request_duration_histogram.labels(
        method=method,
        endpoint=endpoint
    ).observe(duration)

    logger.debug("api_request_recorded", method=method, endpoint=endpoint, status_code=status_code, duration=duration)
