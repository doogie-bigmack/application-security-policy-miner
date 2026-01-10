"""Worker auto-scaling service for Celery workers."""

import asyncio
import os
from typing import Any

import docker
import structlog
from celery import current_app as celery_app

logger = structlog.get_logger(__name__)


class WorkerAutoscaler:
    """
    Manages automatic scaling of Celery workers based on queue depth and load.

    This service monitors the Celery queue depth and worker utilization,
    and automatically scales workers up or down using Docker API.
    """

    def __init__(
        self,
        min_workers: int = 3,
        max_workers: int = 50,
        scale_up_threshold: int = 10,
        scale_down_threshold: int = 2,
        check_interval: int = 30,
    ):
        """
        Initialize the autoscaler.

        Args:
            min_workers: Minimum number of workers to maintain
            max_workers: Maximum number of workers to scale to
            scale_up_threshold: Queue depth threshold to trigger scale-up
            scale_down_threshold: Queue depth threshold to trigger scale-down
            check_interval: Seconds between scaling checks
        """
        self.min_workers = min_workers
        self.max_workers = max_workers
        self.scale_up_threshold = scale_up_threshold
        self.scale_down_threshold = scale_down_threshold
        self.check_interval = check_interval
        self.docker_client = None
        self.project_name = os.getenv("COMPOSE_PROJECT_NAME", "poalo_policy_miner")
        self._running = False

        logger.info(
            "Autoscaler initialized",
            min_workers=min_workers,
            max_workers=max_workers,
            scale_up_threshold=scale_up_threshold,
            scale_down_threshold=scale_down_threshold,
        )

    def _init_docker_client(self) -> docker.DockerClient:
        """Initialize Docker client."""
        if not self.docker_client:
            try:
                self.docker_client = docker.from_env()
                logger.info("Docker client initialized")
            except Exception as e:
                logger.error("Failed to initialize Docker client", error=str(e))
                raise
        return self.docker_client

    def get_queue_stats(self) -> dict[str, Any]:
        """
        Get current queue depth and worker stats from Celery.

        Returns:
            Dictionary with queue and worker statistics
        """
        inspect = celery_app.control.inspect()

        # Get active tasks per worker
        active_tasks_by_worker = inspect.active() or {}

        # Get reserved tasks per worker
        reserved_tasks_by_worker = inspect.reserved() or {}

        # Get stats per worker
        worker_stats_data = inspect.stats() or {}

        # Calculate totals
        total_workers = len(worker_stats_data)
        total_tasks_active = sum(len(tasks) for tasks in active_tasks_by_worker.values())
        total_tasks_reserved = sum(len(tasks) for tasks in reserved_tasks_by_worker.values())
        queue_depth = total_tasks_reserved + total_tasks_active

        return {
            "total_workers": total_workers,
            "queue_depth": queue_depth,
            "active_tasks": total_tasks_active,
            "reserved_tasks": total_tasks_reserved,
        }

    def get_worker_containers(self) -> list[docker.models.containers.Container]:
        """
        Get all worker containers for this project.

        Returns:
            List of Docker container objects
        """
        try:
            client = self._init_docker_client()

            # Find worker containers by label
            containers = client.containers.list(
                filters={
                    "label": [
                        f"com.docker.compose.project={self.project_name}",
                        "com.docker.compose.service=worker",
                    ],
                    "status": "running",
                }
            )

            logger.debug("Found worker containers", count=len(containers))
            return containers
        except Exception as e:
            logger.error("Failed to get worker containers", error=str(e))
            return []

    def scale_workers(self, target_count: int) -> bool:
        """
        Scale workers to target count using docker-compose.

        Args:
            target_count: Desired number of worker containers

        Returns:
            True if scaling succeeded, False otherwise
        """
        try:
            # Enforce min/max constraints
            target_count = max(self.min_workers, min(self.max_workers, target_count))

            current_count = len(self.get_worker_containers())

            if current_count == target_count:
                logger.debug("Workers already at target count", count=target_count)
                return True

            logger.info(
                "Scaling workers",
                current_count=current_count,
                target_count=target_count,
            )

            # Use Docker API to scale containers directly
            # This is more reliable than docker-compose CLI in containers
            client = self._init_docker_client()

            # Get current worker containers
            current_containers = self.get_worker_containers()

            if target_count > current_count:
                # Scale up: create new worker containers
                scale_up_count = target_count - current_count

                # Use the first worker as a template
                if current_containers:
                    template = current_containers[0]

                    for i in range(scale_up_count):
                        try:
                            # Parse volume mounts from template
                            volumes = {}
                            for mount in template.attrs["Mounts"]:
                                if mount["Type"] == "bind":
                                    volumes[mount["Source"]] = {
                                        "bind": mount["Destination"],
                                        "mode": mount.get("Mode", "rw"),
                                    }

                            # Create new container with same config
                            new_container = client.containers.run(
                                image=template.image.tags[0] if template.image.tags else template.image.id,
                                command=template.attrs["Config"]["Cmd"],
                                environment=template.attrs["Config"]["Env"],
                                network=f"{self.project_name}_default",
                                labels={
                                    "com.docker.compose.project": self.project_name,
                                    "com.docker.compose.service": "worker",
                                },
                                volumes=volumes,
                                detach=True,
                                restart_policy={"Name": "unless-stopped"},
                            )
                            logger.info("Created new worker container", container_id=new_container.short_id)
                        except Exception as e:
                            logger.error("Failed to create worker container", error=str(e))

            elif target_count < current_count:
                # Scale down: remove excess worker containers
                scale_down_count = current_count - target_count

                # Sort by creation time and remove oldest idle workers
                for container in current_containers[:scale_down_count]:
                    try:
                        container.stop(timeout=30)
                        container.remove()
                        logger.info("Removed worker container", container_id=container.short_id)
                    except Exception as e:
                        logger.error("Failed to remove worker container", error=str(e))

            logger.info(
                "Successfully scaled workers",
                from_count=current_count,
                to_count=target_count,
            )
            return True

        except Exception as e:
            logger.error("Exception while scaling workers", error=str(e))
            return False

    def check_and_scale(self) -> None:
        """
        Check queue depth and scale workers if needed.
        """
        try:
            stats = self.get_queue_stats()
            current_workers = stats["total_workers"]
            queue_depth = stats["queue_depth"]

            logger.debug(
                "Autoscaler check",
                current_workers=current_workers,
                queue_depth=queue_depth,
            )

            # Scale up if queue depth exceeds threshold
            if queue_depth > self.scale_up_threshold * current_workers:
                # Scale up by 50% or add at least 5 workers
                scale_factor = 1.5
                new_count = max(
                    current_workers + 5,
                    int(current_workers * scale_factor),
                )

                logger.info(
                    "Queue depth high, scaling up",
                    queue_depth=queue_depth,
                    threshold=self.scale_up_threshold * current_workers,
                    new_count=new_count,
                )

                self.scale_workers(new_count)

            # Scale down if queue is empty and we have more than min workers
            elif queue_depth < self.scale_down_threshold and current_workers > self.min_workers:
                # Scale down to min workers or reduce by 25%
                new_count = max(
                    self.min_workers,
                    int(current_workers * 0.75),
                )

                logger.info(
                    "Queue depth low, scaling down",
                    queue_depth=queue_depth,
                    threshold=self.scale_down_threshold,
                    new_count=new_count,
                )

                self.scale_workers(new_count)

        except Exception as e:
            logger.error("Error in autoscaler check", error=str(e))

    def restart_failed_workers(self) -> None:
        """
        Check for failed workers and restart them.
        """
        try:
            client = self._init_docker_client()

            # Find unhealthy or exited worker containers
            all_workers = client.containers.list(
                all=True,
                filters={
                    "label": [
                        f"com.docker.compose.project={self.project_name}",
                        "com.docker.compose.service=worker",
                    ],
                }
            )

            for container in all_workers:
                if container.status in ["exited", "dead"]:
                    logger.warning(
                        "Restarting failed worker",
                        container_id=container.short_id,
                        status=container.status,
                    )
                    try:
                        container.restart()
                        logger.info("Worker restarted", container_id=container.short_id)
                    except Exception as e:
                        logger.error(
                            "Failed to restart worker",
                            container_id=container.short_id,
                            error=str(e),
                        )

        except Exception as e:
            logger.error("Error checking failed workers", error=str(e))

    async def start(self) -> None:
        """
        Start the autoscaler monitoring loop.
        """
        self._running = True
        logger.info("Autoscaler started")

        while self._running:
            try:
                # Check queue depth and scale if needed
                self.check_and_scale()

                # Restart any failed workers
                self.restart_failed_workers()

                # Wait before next check
                await asyncio.sleep(self.check_interval)

            except Exception as e:
                logger.error("Error in autoscaler loop", error=str(e))
                await asyncio.sleep(self.check_interval)

    def stop(self) -> None:
        """
        Stop the autoscaler monitoring loop.
        """
        self._running = False
        logger.info("Autoscaler stopped")

    def get_metrics(self) -> dict[str, Any]:
        """
        Get current autoscaler metrics.

        Returns:
            Dictionary with autoscaler configuration and current state
        """
        stats = self.get_queue_stats()
        workers = self.get_worker_containers()

        return {
            "config": {
                "min_workers": self.min_workers,
                "max_workers": self.max_workers,
                "scale_up_threshold": self.scale_up_threshold,
                "scale_down_threshold": self.scale_down_threshold,
                "check_interval": self.check_interval,
            },
            "current_state": {
                "total_workers": stats["total_workers"],
                "running_containers": len(workers),
                "queue_depth": stats["queue_depth"],
                "active_tasks": stats["active_tasks"],
            },
            "status": "running" if self._running else "stopped",
        }


# Global autoscaler instance
_autoscaler: WorkerAutoscaler | None = None


def get_autoscaler() -> WorkerAutoscaler:
    """
    Get or create the global autoscaler instance.

    Returns:
        WorkerAutoscaler instance
    """
    global _autoscaler
    if _autoscaler is None:
        _autoscaler = WorkerAutoscaler(
            min_workers=int(os.getenv("AUTOSCALER_MIN_WORKERS", "3")),
            max_workers=int(os.getenv("AUTOSCALER_MAX_WORKERS", "50")),
            scale_up_threshold=int(os.getenv("AUTOSCALER_SCALE_UP_THRESHOLD", "10")),
            scale_down_threshold=int(os.getenv("AUTOSCALER_SCALE_DOWN_THRESHOLD", "2")),
            check_interval=int(os.getenv("AUTOSCALER_CHECK_INTERVAL", "30")),
        )
    return _autoscaler
