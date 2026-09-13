import threading
import time
from typing import Dict, Any


class SyslogMetrics:
    """
    In-memory thread-safe metrics collector for live Syslog ingestion.
    Tracks throughput, error rates, queue depth, and latency without external agents.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self.messages_received: int = 0
        self.messages_processed: int = 0
        self.messages_failed: int = 0
        self.messages_dropped: int = 0
        self.oversized_messages: int = 0
        self.malformed_messages: int = 0
        self.active_tcp_connections: int = 0
        self.queue_depth: int = 0

        # Latency tracking (exponential moving average or cumulative average)
        self._total_latency_ms: float = 0.0
        self._latency_count: int = 0

        # Throughput tracking
        self._start_time: float = time.time()
        self._last_calc_time: float = time.time()
        self._last_processed_count: int = 0
        self._current_eps: float = 0.0

    def record_received(self, count: int = 1) -> None:
        with self._lock:
            self.messages_received += count

    def record_processed(self, latency_ms: float = 0.0) -> None:
        with self._lock:
            self.messages_processed += 1
            self._total_latency_ms += latency_ms
            self._latency_count += 1

    def record_failed(self) -> None:
        with self._lock:
            self.messages_failed += 1

    def record_dropped(self, count: int = 1) -> None:
        with self._lock:
            self.messages_dropped += count

    def record_oversized(self) -> None:
        with self._lock:
            self.oversized_messages += 1

    def record_malformed(self) -> None:
        with self._lock:
            self.malformed_messages += 1

    def set_queue_depth(self, depth: int) -> None:
        with self._lock:
            self.queue_depth = depth

    def increment_connections(self) -> None:
        with self._lock:
            self.active_tcp_connections += 1

    def decrement_connections(self) -> None:
        with self._lock:
            if self.active_tcp_connections > 0:
                self.active_tcp_connections -= 1

    def get_events_per_second(self) -> float:
        now = time.time()
        with self._lock:
            elapsed = now - self._last_calc_time
            if elapsed >= 1.0:
                processed_delta = self.messages_processed - self._last_processed_count
                self._current_eps = round(processed_delta / elapsed, 2)
                self._last_calc_time = now
                self._last_processed_count = self.messages_processed
            return self._current_eps

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            avg_latency = round(self._total_latency_ms / max(self._latency_count, 1), 2) if self._latency_count > 0 else 0.0
            total_elapsed = max(time.time() - self._start_time, 0.001)
            overall_eps = round(self.messages_processed / total_elapsed, 2)

            return {
                "messages_received": self.messages_received,
                "messages_processed": self.messages_processed,
                "messages_failed": self.messages_failed,
                "messages_dropped": self.messages_dropped,
                "oversized_messages": self.oversized_messages,
                "malformed_messages": self.malformed_messages,
                "active_tcp_connections": self.active_tcp_connections,
                "queue_depth": self.queue_depth,
                "processing_latency_ms_avg": avg_latency,
                "events_per_second": self._current_eps if self._current_eps > 0 else overall_eps,
                "uptime_seconds": int(total_elapsed)
            }

    def reset(self) -> None:
        with self._lock:
            self.messages_received = 0
            self.messages_processed = 0
            self.messages_failed = 0
            self.messages_dropped = 0
            self.oversized_messages = 0
            self.malformed_messages = 0
            self.active_tcp_connections = 0
            self.queue_depth = 0
            self._total_latency_ms = 0.0
            self._latency_count = 0
            self._start_time = time.time()
            self._last_calc_time = time.time()
            self._last_processed_count = 0
            self._current_eps = 0.0


# Singleton metrics instance
syslog_metrics = SyslogMetrics()
