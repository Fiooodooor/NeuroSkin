"""Ctrl+C, lifecycle shutdown, and archive preservation checks.

Windows fan-out of Ctrl+C cannot be emulated on Linux, but the worker's signal
policy and the parent shutdown lifecycle are checked independently.
"""
import concurrent.futures
import multiprocessing
import os
import signal
import tempfile
import time
import unittest
from pathlib import Path

from advanced import EvolutionEngine, evolution_worker_initializer


def worker_signal_policy():
    return signal.getsignal(signal.SIGINT) == signal.SIG_IGN


class TestShutdownV211(unittest.TestCase):
    def test_spawned_workers_ignore_parent_console_sigint(self):
        with concurrent.futures.ProcessPoolExecutor(
                max_workers=2, mp_context=multiprocessing.get_context('spawn'),
                initializer=evolution_worker_initializer) as pool:
            self.assertTrue(pool.submit(worker_signal_policy).result(timeout=20))
            self.assertTrue(pool.submit(worker_signal_policy).result(timeout=20))

    def test_stop_during_pause_is_not_stuck(self):
        with tempfile.TemporaryDirectory() as folder:
            e=EvolutionEngine(folder)
            e.start('all',300,86,12,.4,cores=1,audit_grid=3,fem=False)
            e.pause()
            e.stop()
            self.assertFalse(e.pause_event.is_set())
            self.assertTrue(e.shutdown(timeout=15))
            self.assertIn(e.snapshot()['status'],('stopped','completed'))

    def test_forced_worker_termination_after_grace_period(self):
        with tempfile.TemporaryDirectory() as folder:
            e=EvolutionEngine(folder)
            class FakePool:
                calls=0
                def terminate_workers(self):
                    self.calls+=1
                    thread.alive=False
            class FakeThread:
                alive=True
                def is_alive(self):return self.alive
                def join(self,timeout):pass
            thread=FakeThread()
            pool=FakePool()
            e.thread=thread
            e._pool=pool
            self.assertTrue(e.shutdown(timeout=0.0))
            self.assertEqual(pool.calls,1)

    def test_async_lifespan_requests_evolution_shutdown(self):
        import asyncio
        import server
        from unittest.mock import patch

        class Probe:
            def __init__(self):self.called=0
            def shutdown(self,timeout):self.called+=1;return True

        probe=Probe()
        async def run():
            with patch.object(server,'EVO',probe):
                async with server.application_lifespan(server.app):
                    self.assertEqual(probe.called,0)
                self.assertEqual(probe.called,1)
        asyncio.run(run())


if __name__=='__main__':unittest.main()
