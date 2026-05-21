from __future__ import annotations

import asyncio
import redis.asyncio as aioredis
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

from .eviction import EvictionStrategy, FIFOCache, LFUCache, LRUCache

# manager.py is a file which orchestrates the cache layers and eviction strategies, and also handles event broadcasting for observability. It defines the CacheManager class which is the main entry point for cache operations. The CacheManager supports dynamic policy swapping at runtime and maintains aggregate statistics for monitoring purposes.

# manager.py uses eviction.py for the concrete eviction strategy implementations (LRU, LFU, FIFO) and defines a common EvictionStrategy interface. It also defines enums for Policy, Tier, and EventKind to standardize the types of policies, cache tiers, and events that can occur.

logger = logging.getLogger("aegiscache.manager")



# Policy is inheriting from str to allow easy serialization and display, and Enum to define a fixed set of eviction policies.

class Policy(str, Enum):
    LRU  = "LRU"
    LFU  = "LFU"
    FIFO = "FIFO"


class Tier(str, Enum):
    L1_MEMORY  = "L1_MEMORY"
    L2_REDIS   = "L2_REDIS"
    DB_BACKEND = "DB_BACKEND"


class EventKind(str, Enum):
    HIT           = "HIT"
    MISS          = "MISS"
    EVICTION      = "EVICTION"
    POLICY_CHANGE = "POLICY_CHANGE"
    ERROR         = "ERROR"


# @dataclass makes the life simpler by automatically generating init, repr, and other methods.
# We have required and optional fields with default values.

@dataclass
class CacheEvent:
    kind:       EventKind
    key:        str        = ""
    tier:       Tier       = Tier.L1_MEMORY
    latency_ms: float      = 0.0
    policy:     Policy     = Policy.LRU
    detail:     str        = ""
    timestamp_ms: int      = field(default_factory=lambda: int(time.time() * 1000))
    stats:      dict       = field(default_factory=dict)


@dataclass
class AggregateStats:
    total_requests:  int   = 0
    l1_hits:         int   = 0
    l2_hits:         int   = 0
    db_hits:         int   = 0
    total_evictions: int   = 0
    total_latency_ms: float = 0.0

    @property
    def hit_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return round((self.l1_hits + self.l2_hits) / self.total_requests, 4)

    @property
    def avg_latency_ms(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return round(self.total_latency_ms / self.total_requests, 3)

    def to_dict(self) -> dict:
        return {
            "total_requests":  self.total_requests,
            "l1_hits":         self.l1_hits,
            "l2_hits":         self.l2_hits,
            "db_hits":         self.db_hits,
            "total_evictions": self.total_evictions,
            "hit_rate":        self.hit_rate,
            "avg_latency_ms":  self.avg_latency_ms,
        }

_STRATEGY_MAP: dict[Policy, type[EvictionStrategy]] = {
    Policy.LRU:  LRUCache,
    Policy.LFU:  LFUCache,
    Policy.FIFO: FIFOCache,
}

def _build_strategy(policy: Policy, capacity: int) -> EvictionStrategy:
    cls = _STRATEGY_MAP.get(policy)
    if cls is None:
        raise ValueError(f"Unknown eviction policy: {policy!r}")
    return cls(capacity)


class CacheManager:

    # Here faking the DB latency with a sleep in the get() method, and we can configure it via the constructor. The default is 100ms, which is a reasonable approximation for a typical database query.

    _DB_LATENCY_MIN = 0.05
    _DB_LATENCY_MAX = 0.15

    def __init__(
        self,
        capacity:  int    = 256,
        policy:    Policy = Policy.LRU,
        db_latency_s: float = 0.10,
    ) -> None:
        self._policy        = policy
        self._capacity      = capacity
        self._db_latency_s  = db_latency_s

        self._l1: EvictionStrategy = _build_strategy(policy, capacity)

        self._redis: Optional[Any] = None  

        self._observers: list[Callable[[CacheEvent], Any]] = []

        self._stats = AggregateStats()

        # The asyncio.Lock ensures that get/put/delete operations are atomic with respect to policy swaps, preventing race conditions. For example if a get() is in progress while a policy swap occurs, the lock ensures that the get() either sees the old policy or the new policy.

        self._lock = asyncio.Lock() 

        logger.info("CacheManager started | policy=%s capacity=%d", policy, capacity)

   

    # The async functions in generally can pause their execution to allow other tasks to run, which is essential for handling I/O-bound operations like Redis interactions without blocking the entire cache manager.
    # These async functions are called coroutines, and they can be awaited by other parts of the code that need to ensure the connection is established before proceeding with cache operations.

    async def connect_redis(self, url: str = "redis://localhost:6379") -> None:
        try:
            import redis.asyncio as aioredis
            self._redis = await aioredis.from_url(url, decode_responses=False)
            logger.info("L2 Redis connected: %s", url)
        except Exception as exc:
            logger.warning("Redis unavailable — running L1-only: %s", exc)
            self._redis = None

    async def disconnect_redis(self) -> None:
        if self._redis:
            await self._redis.close()
            self._redis = None



    # The subscribe and unsubscribe methods allow external components to register callbacks that will be invoked whenever a CacheEvent occurs. This is a simple observer pattern implementation.
    # subscribe() adds a callback to the list of observers, while unsubscribe() removes it. The callbacks are expected to be async functions that take a CacheEvent as an argument, allowing them to perform asynchronous operations if needed. For example external service and updating metrics.

    def subscribe(self, callback: Callable[[CacheEvent], Any]) -> None:
        """Register an async callback to receive CacheEvent broadcasts."""
        self._observers.append(callback)

    def unsubscribe(self, callback: Callable[[CacheEvent], Any]) -> None:
        try:
            self._observers.remove(callback)
        except ValueError:
            pass

    # The _broadcast method is responsible for sending a CacheEvent to all registered observers concurrently. It gathers the current aggregate stats and L1 stats into the event before broadcasting. It uses asyncio.gather to run all observer callbacks in parallel, and it handles any exceptions that may occur in the observers without affecting the main cache operations.

    async def _broadcast(self, event: CacheEvent) -> None:
        """Fan-out a CacheEvent to all registered observers concurrently."""
        event.stats = {**self._stats.to_dict(), **self._l1.stats}
        coros = [cb(event) for cb in self._observers]
        if coros:
            results = await asyncio.gather(*coros, return_exceptions=True)
            for r in results:
                if isinstance(r, Exception):
                    logger.error("Observer error: %s", r)


# When get is called it first checks the L1 cache for the key. If it finds it, it records a hit and broadcasts a CacheEvent with the HIT kind. If it doesn't find it in L1, it checks Redis (L2) if connected. If found in Redis, it promotes the value to L1 and broadcasts another HIT event for L2. If it's not found in either layer, it simulates a DB fetch with a sleep, records a MISS event, and returns None.

# The broadcast event helps to decouple the cache logic from the monitoring and logging logic, allowing for flexible observability without cluttering the core cache operations. For example, you could have one observer that logs events to a file, another that updates Prometheus metrics, and another that sends alerts for certain conditions, all without modifying the CacheManager's core logic.

    async def get(self, key: str) -> tuple[Optional[bytes], Tier]:
        start_ns = time.monotonic_ns()
        self._stats.total_requests += 1

        async with self._lock:
            value = self._l1.get(key)

        if value is not None:
            latency = _ns_to_ms(time.monotonic_ns() - start_ns)
            self._stats.l1_hits += 1
            self._stats.total_latency_ms += latency
            await self._broadcast(CacheEvent(
                kind=EventKind.HIT, key=key, tier=Tier.L1_MEMORY,
                latency_ms=latency, policy=self._policy,
            ))
            return value, Tier.L1_MEMORY

        if self._redis:
            try:
                value = await self._redis.get(key)
            except Exception as exc:
                logger.error("Redis GET error: %s", exc)
                value = None

            if value is not None:
                async with self._lock:
                    evicted = self._l1.put(key, value)
                latency = _ns_to_ms(time.monotonic_ns() - start_ns)
                self._stats.l2_hits += 1
                self._stats.total_latency_ms += latency
                if evicted:
                    self._stats.total_evictions += 1
                    await self._broadcast(CacheEvent(
                        kind=EventKind.EVICTION, key=evicted, tier=Tier.L1_MEMORY,
                        policy=self._policy,
                    ))
                await self._broadcast(CacheEvent(
                    kind=EventKind.HIT, key=key, tier=Tier.L2_REDIS,
                    latency_ms=latency, policy=self._policy,
                ))
                return value, Tier.L2_REDIS

        await asyncio.sleep(self._db_latency_s)   # simulated I/O latency
        latency = _ns_to_ms(time.monotonic_ns() - start_ns)
        self._stats.db_hits += 1
        self._stats.total_latency_ms += latency
        await self._broadcast(CacheEvent(
            kind=EventKind.MISS, key=key, tier=Tier.DB_BACKEND,
            latency_ms=latency, policy=self._policy,
            detail="Cache miss — value would be populated from DB here",
        ))
        return None, Tier.DB_BACKEND

    async def put(
        self,
        key:           str,
        value:         bytes,
        ttl_seconds:   int  = 0,
        write_through: bool = False,
    ) -> Optional[str]:
        
        async with self._lock:
            evicted = self._l1.put(key, value)

        if evicted:
            self._stats.total_evictions += 1
            await self._broadcast(CacheEvent(
                kind=EventKind.EVICTION, key=evicted,
                tier=Tier.L1_MEMORY, policy=self._policy,
            ))

        if write_through and self._redis:
            try:
                if ttl_seconds > 0:
                    await self._redis.set(key, value, ex=ttl_seconds)
                else:
                    await self._redis.set(key, value)
            except Exception as exc:
                logger.error("Redis SET error: %s", exc)

        return evicted

    async def delete(self, key: str) -> bool:
        """Remove a key from L1 (and L2 if connected)."""
        async with self._lock:
            existed = self._l1.delete(key)

        if self._redis:
            try:
                await self._redis.delete(key)
            except Exception as exc:
                logger.error("Redis DEL error: %s", exc)

        return existed

# Swap policy is the most complex operation, as it needs to migrate existing entries from the old eviction strategy to the new one without losing data. it first locks the cache to prevent concurrent modifications, then it takes a snapshot of all current entries in L1. It builds a new eviction strategy instance based on the new policy and capacity, and it re-inserts all the saved entries into the new strategy. Finally, it updates the internal references to the new strategy and broadcasts a POLICY_CHANGE event with details about the swap.

    async def swap_policy(
        self,
        new_policy:   Policy,
        new_capacity: int = 0,
    ) -> dict:
        old_policy   = self._policy
        new_capacity = new_capacity if new_capacity > 0 else self._capacity

        async with self._lock:
            saved_entries: list[tuple[str, Any]] = self._snapshot_l1()

            new_strategy = _build_strategy(new_policy, new_capacity)

            for k, v in saved_entries:
                new_strategy.put(k, v)

            self._l1       = new_strategy
            self._policy   = new_policy
            self._capacity = new_capacity

        logger.info(
            "Policy swap: %s → %s (capacity %d → %d), migrated %d entries",
            old_policy, new_policy, self._capacity, new_capacity, len(saved_entries),
        )

        await self._broadcast(CacheEvent(
            kind=EventKind.POLICY_CHANGE,
            policy=new_policy,
            detail=f"Swapped {old_policy} → {new_policy} | migrated {len(saved_entries)} entries",
        ))

        return {
            "old_policy":    old_policy,
            "new_policy":    new_policy,
            "new_capacity":  new_capacity,
            "migrated_keys": len(saved_entries),
        }

    def _snapshot_l1(self) -> list[tuple[str, Any]]:
        l1 = self._l1
        if isinstance(l1, LRUCache):
            entries: list[tuple[str, Any]] = []
            node = l1._list.tail.prev
            while node is not l1._list.head:
                entries.append((node.key, node.value))
                node = node.prev
            return list(reversed(entries))   # oldest first

        if isinstance(l1, LFUCache):
            return [(k, v.value) for k, v in l1._store.items()]

        if isinstance(l1, FIFOCache):
            return [(k, l1._store[k]) for k in l1._order]

        # Fallback: best-effort via contains + internal store introspection
        return []

    @property
    def active_policy(self) -> Policy:
        return self._policy

    @property
    def capacity(self) -> int:
        return self._capacity

    def get_stats(self) -> dict:
        return {
            **self._stats.to_dict(),
            **self._l1.stats,
            "active_policy": self._policy.value,
            "capacity":      self._capacity,
        }

    def reset_stats(self) -> None:
        self._stats    = AggregateStats()
        self._l1.reset_stats()


def _ns_to_ms(ns: int) -> float:
    return round(ns / 1_000_000, 3)