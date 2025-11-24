"""Job management system for async audio separation processing."""

import logging
import time
import uuid
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    """Job status enumeration."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Job:
    """Represents a separation job."""

    def __init__(self, job_id: str, file_path: Path, stems: int):
        """
        Initialize a new job.

        Args:
            job_id: Unique job identifier
            file_path: Path to the uploaded audio file
            stems: Number of stems to separate into
        """
        self.job_id = job_id
        self.file_path = file_path
        self.stems = stems
        self.status = JobStatus.PENDING
        self.created_at = time.time()
        self.started_at: float | None = None
        self.completed_at: float | None = None
        self.error: str | None = None
        self.result_path: Path | None = None
        self.progress: float = 0.0  # 0.0 to 1.0

    def to_dict(self) -> dict[str, Any]:
        """Convert job to dictionary for API response."""
        result = {
            "job_id": self.job_id,
            "status": self.status.value,
            "stems": self.stems,
            "created_at": self.created_at,
            "progress": self.progress,
        }

        if self.started_at:
            result["started_at"] = self.started_at
        if self.completed_at:
            result["completed_at"] = self.completed_at
        if self.error:
            result["error"] = self.error
        if self.status == JobStatus.COMPLETED and self.result_path:
            result["result_url"] = f"/jobs/{self.job_id}/result"
            result["result_size_mb"] = (
                round(self.result_path.stat().st_size / (1024 * 1024), 2)
                if self.result_path.exists()
                else None
            )

        # Calculate elapsed time
        if self.completed_at and self.started_at:
            result["processing_time_seconds"] = round(self.completed_at - self.started_at, 2)
        elif self.started_at:
            result["elapsed_time_seconds"] = round(time.time() - self.started_at, 2)

        return result


class JobManager:
    """Manages separation jobs in memory."""

    def __init__(self):
        """Initialize the job manager."""
        self._jobs: dict[str, Job] = {}
        self._cleanup_interval = 3600  # Clean up completed jobs after 1 hour
        logger.info("JobManager initialized")

    def create_job(self, file_path: Path, stems: int) -> Job:
        """
        Create a new separation job.

        Args:
            file_path: Path to the uploaded audio file
            stems: Number of stems to separate into

        Returns:
            Created job instance
        """
        job_id = str(uuid.uuid4())
        job = Job(job_id, file_path, stems)
        self._jobs[job_id] = job
        logger.info(f"Created job {job_id} for file {file_path.name} with {stems} stems")
        return job

    def get_job(self, job_id: str) -> Job | None:
        """
        Get a job by ID.

        Args:
            job_id: Job identifier

        Returns:
            Job instance or None if not found
        """
        return self._jobs.get(job_id)

    def update_job_status(
        self,
        job_id: str,
        status: JobStatus,
        progress: float | None = None,
        error: str | None = None,
        result_path: Path | None = None,
    ) -> bool:
        """
        Update job status.

        Args:
            job_id: Job identifier
            status: New status
            progress: Progress (0.0 to 1.0)
            error: Error message if failed
            result_path: Path to result file if completed

        Returns:
            True if job was updated, False if not found
        """
        job = self._jobs.get(job_id)
        if not job:
            return False

        job.status = status
        if progress is not None:
            job.progress = max(0.0, min(1.0, progress))
        if error:
            job.error = error
        if result_path:
            job.result_path = result_path

        if status == JobStatus.PROCESSING and not job.started_at:
            job.started_at = time.time()
        elif status in (JobStatus.COMPLETED, JobStatus.FAILED):
            job.completed_at = time.time()
            job.progress = 1.0

        logger.info(f"Job {job_id} status updated to {status.value}")
        return True

    def cleanup_old_jobs(self) -> int:
        """
        Clean up completed/failed jobs older than cleanup interval.

        Returns:
            Number of jobs cleaned up
        """
        current_time = time.time()
        jobs_to_remove = []

        for job_id, job in self._jobs.items():
            if job.completed_at and (current_time - job.completed_at) > self._cleanup_interval:
                jobs_to_remove.append(job_id)

        for job_id in jobs_to_remove:
            del self._jobs[job_id]

        if jobs_to_remove:
            logger.info(f"Cleaned up {len(jobs_to_remove)} old jobs")
        return len(jobs_to_remove)

    def get_all_jobs(self) -> list[Job]:
        """Get all jobs (for debugging/monitoring)."""
        return list(self._jobs.values())


# Global job manager instance
job_manager = JobManager()

