"""In-memory job tracking with a single worker thread.

Jobs run one at a time because the LLM and the TTS model share one GPU.
Job state is lost on restart; the rendered files stay in data/jobs/.
"""

import threading
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from typing import Callable, Literal

Status = Literal["queued", "running", "done", "error"]


@dataclass
class Job:
    id: str
    status: Status = "queued"
    stage: str = "Queued"
    progress: int = 0
    error: str | None = None
    title: str | None = None
    script: str | None = None
    video_url: str | None = None
    options: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


class JobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="job")

    def create(self, options: dict) -> Job:
        job = Job(id=uuid.uuid4().hex[:12], options=options)
        with self._lock:
            self._jobs[job.id] = job
        return job

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def update(self, job_id: str, **changes) -> None:
        with self._lock:
            job = self._jobs[job_id]
            for key, value in changes.items():
                setattr(job, key, value)

    def submit(self, job: Job, work: Callable[[Job], None]) -> None:
        def run() -> None:
            self.update(job.id, status="running")
            try:
                work(job)
                self.update(job.id, status="done", stage="Done", progress=100)
            except Exception as exc:  # surface any failure to the UI
                traceback.print_exc()
                self.update(job.id, status="error", error=str(exc) or type(exc).__name__)

        self._executor.submit(run)


jobs = JobStore()
