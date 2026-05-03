import time


class Metrics:
    def __init__(self):
        self.total_requests = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.errors = 0
        self.total_latency = 0

    def start_timer(self):
        return time.time()

    def end_timer(self, start):
        self.total_latency += time.time() - start

    def get(self):
        avg_latency = (
            self.total_latency / self.total_requests
            if self.total_requests else 0
        )

        hit_rate = (
            self.cache_hits / self.total_requests
            if self.total_requests else 0
        )

        return {
            "total_requests": self.total_requests,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": round(hit_rate, 4),
            "errors": self.errors,
            "avg_latency_sec": round(avg_latency, 4)
        }

metrics = Metrics()