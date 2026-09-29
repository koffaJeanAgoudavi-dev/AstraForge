"""Durable build job manager and worker."""

import asyncio
import uuid
from collections.abc import Awaitable, Callable

from astraforge.state.store import StateStore

JobExecutor = Callable[[dict], Awaitable[None]]


class BuildWorker:
    """Claims persisted jobs with leases and executes them with heartbeats."""

    def __init__(
        self,
        state_store: StateStore,
        executor: JobExecutor,
        *,
        poll_interval: float = 0.5,
        lease_seconds: int = 60,
        heartbeat_interval: float = 15,
        max_runtime: float = 3600,
        recovery_age: int = 300,
    ) -> None:
        self.state_store = state_store
        self.executor = executor
        self.poll_interval = poll_interval
        self.lease_seconds = lease_seconds
        self.heartbeat_interval = heartbeat_interval
        self.max_runtime = max_runtime
        self.recovery_age = recovery_age
        self.worker_id = uuid.uuid4().hex
        self._stop = asyncio.Event()

    async def _heartbeat(self, run_id: int) -> None:
        while True:
            await asyncio.sleep(self.heartbeat_interval)
            if not self.state_store.heartbeat_run(run_id, self.worker_id, self.lease_seconds):
                return

    async def run_once(self) -> bool:
        job = self.state_store.claim_next_queued_run(self.worker_id, self.lease_seconds)
        if job is None:
            return False
        heartbeat = asyncio.create_task(self._heartbeat(job["id"]))
        try:
            await asyncio.wait_for(self.executor(job), timeout=self.max_runtime)
        except asyncio.CancelledError:
            raise
        except asyncio.TimeoutError:
            self.state_store.update_run(
                job["id"],
                stage="failed",
                status="failed",
                attempts=job["attempts"],
                error=f"Worker execution exceeded {self.max_runtime:.0f}s timeout",
                context=job["context"],
            )
        except Exception as exc:
            self.state_store.update_run(
                job["id"],
                stage="failed",
                status="failed",
                attempts=job["attempts"],
                error=str(exc),
                context=job["context"],
            )
        finally:
            heartbeat.cancel()
            try:
                await heartbeat
            except asyncio.CancelledError:
                pass
        return True

    async def run_forever(self) -> None:
        self.state_store.recover_stale_runs(self.recovery_age)
        while not self._stop.is_set():
            self.state_store.recover_stale_runs(self.recovery_age)
            processed = await self.run_once()
            if not processed:
                try:
                    await asyncio.wait_for(self._stop.wait(), timeout=self.poll_interval)
                except asyncio.TimeoutError:
                    pass

    def stop(self) -> None:
        self._stop.set()


class JobManager:
    """Application-facing queue API; HTTP code submits jobs, workers execute them."""

    def __init__(
        self,
        state_store: StateStore,
        executor: JobExecutor,
        *,
        poll_interval: float = 0.5,
        lease_seconds: int = 60,
        heartbeat_interval: float = 15,
        max_runtime: float = 3600,
        recovery_age: int = 300,
    ) -> None:
        self.worker = BuildWorker(
            state_store,
            executor,
            poll_interval=poll_interval,
            lease_seconds=lease_seconds,
            heartbeat_interval=heartbeat_interval,
            max_runtime=max_runtime,
            recovery_age=recovery_age,
        )
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self.worker.run_forever())

    async def stop(self) -> None:
        self.worker.stop()
        if self._task is not None:
            await self._task
            self._task = None

    async def run_once(self) -> bool:
        return await self.worker.run_once()
