"""Durable build job manager and worker."""

import asyncio
from collections.abc import Awaitable, Callable

from astraforge.state.store import StateStore

JobExecutor = Callable[[dict], Awaitable[None]]


class BuildWorker:
    """Claims persisted jobs and executes them outside HTTP request handlers."""

    def __init__(
        self,
        state_store: StateStore,
        executor: JobExecutor,
        *,
        poll_interval: float = 0.5,
        recovery_age: int = 300,
    ) -> None:
        self.state_store = state_store
        self.executor = executor
        self.poll_interval = poll_interval
        self.recovery_age = recovery_age
        self._stop = asyncio.Event()

    async def run_once(self) -> bool:
        job = self.state_store.claim_next_queued_run()
        if job is None:
            return False
        try:
            await self.executor(job)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self.state_store.update_run(
                job["id"],
                stage="failed",
                status="failed",
                attempts=job["attempts"],
                error=str(exc),
                context=job["context"],
            )
        return True

    async def run_forever(self) -> None:
        self.state_store.recover_stale_runs(self.recovery_age)
        while not self._stop.is_set():
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
        recovery_age: int = 300,
    ) -> None:
        self.worker = BuildWorker(
            state_store,
            executor,
            poll_interval=poll_interval,
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
