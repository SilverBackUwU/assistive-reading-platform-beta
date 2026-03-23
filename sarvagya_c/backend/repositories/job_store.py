from __future__ import annotations

from threading import Lock

from core.exceptions import NotFoundError
from schemas.pipeline import PipelineResponse


class InMemoryJobRepository:
    def __init__(self) -> None:
        self._jobs: dict[str, PipelineResponse] = {}
        self._lock = Lock()

    def save(self, job: PipelineResponse) -> None:
        with self._lock:
            self._jobs[job.job_id] = job

    def get(self, job_id: str) -> PipelineResponse:
        with self._lock:
            job = self._jobs.get(job_id)
        if job is None:
            raise NotFoundError(f"No job found for id '{job_id}'.")
        return job
