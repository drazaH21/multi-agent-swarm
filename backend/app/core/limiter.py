import asyncio
import time
from typing import List, Tuple

class SlidingWindowTokenBucket:
    """Enterprise dual rate-limiter enforcing Requests-Per-Minute (RPM) and Tokens-Per-Minute (TPM)."""
    def __init__(self, max_rpm: int = 60, max_tpm: int = 40000):
        self.max_rpm = max_rpm
        self.max_tpm = max_tpm
        self.request_timestamps: List[float] = []
        self.token_usage: List[Tuple[float, int]] = []
        self.lock = asyncio.Lock()

    async def acquire(self, estimated_tokens: int = 500) -> bool:
        async with self.lock:
            now = time.time()
            one_minute_ago = now - 60.0

            # Prune events older than 60 seconds
            self.request_timestamps = [t for t in self.request_timestamps if t > one_minute_ago]
            self.token_usage = [(t, count) for (t, count) in self.token_usage if t > one_minute_ago]

            current_rpm = len(self.request_timestamps)
            current_tpm = sum(count for _, count in self.token_usage)

            # If capacity is exceeded, calculate necessary backoff and wait
            if current_rpm >= self.max_rpm or (current_tpm + estimated_tokens) > self.max_tpm:
                oldest_stamp = self.request_timestamps[0] if self.request_timestamps else now
                sleep_seconds = max(0.5, 60.0 - (now - oldest_stamp))
                await asyncio.sleep(sleep_seconds)
                return await self.acquire(estimated_tokens)

            # Record usage
            self.request_timestamps.append(now)
            self.token_usage.append((now, estimated_tokens))
            return True

    def get_metrics(self) -> dict:
        now = time.time()
        one_minute_ago = now - 60.0
        active_requests = len([t for t in self.request_timestamps if t > one_minute_ago])
        active_tokens = sum(c for t, c in self.token_usage if t > one_minute_ago)
        return {
            "current_rpm": active_requests,
            "max_rpm": self.max_rpm,
            "current_tpm": active_tokens,
            "max_tpm": self.max_tpm
        }
