
# Custom implementation file that starts the gRPC server and connects incoming RPC requests to your CacheManager business logic.
# Its elements implement service methods (like Get, Put) and define how cache operations are executed when clients send requests.

# This is the flow: cache.proto generates cache_pb2.py and cache_pb2_grpc.py, which define the gRPC service and message classes. This grpc_server.py uses them to call cache manager (manager.py) methods and handle client requests. The server listens for gRPC calls, processes them using the CacheManager, and sends back structured responses defined in the protobuf messages.

from __future__ import annotations

import asyncio
import sys
import logging
import os
import time
import uuid
from typing import AsyncIterator

import grpc                              
from grpc import aio as grpc_aio       

try:
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "generated"))
    import cache_pb2
    import cache_pb2_grpc
    _STUBS_AVAILABLE = True
except ImportError:
    cache_pb2 = None
    cache_pb2_grpc = None
    _STUBS_AVAILABLE = False

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cache.manager import CacheEvent, CacheManager, EventKind, Policy, Tier

logger = logging.getLogger("aegiscache.server")


_POLICY_TO_PROTO: dict[Policy, int] = {}
_TIER_TO_PROTO: dict[Tier, int]     = {}
_KIND_TO_PROTO: dict[EventKind, int] = {}

# _init_proto_maps initalizes conversion between python enums and protobuf integer values.

def _init_proto_maps() -> None:
    """Populate conversion dicts once the generated stubs are available."""
    if not _STUBS_AVAILABLE:
        return
    global _POLICY_TO_PROTO, _TIER_TO_PROTO, _KIND_TO_PROTO
    _POLICY_TO_PROTO = {
        Policy.LRU:  cache_pb2.LRU,
        Policy.LFU:  cache_pb2.LFU,
        Policy.FIFO: cache_pb2.FIFO,
    }
    _TIER_TO_PROTO = {
        Tier.L1_MEMORY:  cache_pb2.L1_MEMORY,
        Tier.L2_REDIS:   cache_pb2.L2_REDIS,
        Tier.DB_BACKEND: cache_pb2.DB_BACKEND,
    }
    _KIND_TO_PROTO = {
        EventKind.HIT:           cache_pb2.HIT,
        EventKind.MISS:          cache_pb2.MISS,
        EventKind.EVICTION:      cache_pb2.EVICTION,
        EventKind.POLICY_CHANGE: cache_pb2.POLICY_CHANGE,
        EventKind.ERROR:         cache_pb2.ERROR,
    }

_PROTO_TO_POLICY: dict[int, Policy] = {}

def _proto_to_policy(proto_val: int) -> Policy:
    if not _PROTO_TO_POLICY:
        if _STUBS_AVAILABLE:
            _PROTO_TO_POLICY.update({
                cache_pb2.LRU:  Policy.LRU,
                cache_pb2.LFU:  Policy.LFU,
                cache_pb2.FIFO: Policy.FIFO,
            })
    return _PROTO_TO_POLICY.get(proto_val, Policy.LRU)


class AegisCacheServicer:

    def __init__(self, manager: CacheManager) -> None:
        self._manager = manager

    def _make_meta(self, request_id: str = "", latency_ms: float = 0.0):
        if not _STUBS_AVAILABLE:
            return None
        return cache_pb2.RequestMeta(
            request_id   = request_id or str(uuid.uuid4()),
            timestamp_ms = int(time.time() * 1000),
            latency_ms   = latency_ms,
        )

    def _stats_proto(self):
        if not _STUBS_AVAILABLE:
            return None
        s = self._manager.get_stats()
        return cache_pb2.CacheStats(
            total_requests  = s["total_requests"],
            l1_hits         = s["l1_hits"],
            l2_hits         = s["l2_hits"],
            db_hits         = s["db_hits"],
            total_evictions = s["total_evictions"],
            hit_rate        = s["hit_rate"],
            avg_latency_ms  = s["avg_latency_ms"],
            l1_size         = s["size"],
            l1_capacity     = s["capacity"],
            active_policy   = _POLICY_TO_PROTO.get(
                self._manager.active_policy, cache_pb2.LRU
            ),
        )

# All receive protobuf request messages, call the corresponding CacheManager method, and return a protobuf response message. They also measure latency and include it in the response metadata.

    async def GetValue(self, request, context):
        t0   = time.monotonic()
        key  = request.key
        rid  = request.meta.request_id if request.HasField("meta") else str(uuid.uuid4())

        value, tier = await self._manager.get(key) # tier represents where the value was found (L1, L2, or DB)
        latency_ms  = (time.monotonic() - t0) * 1000

        if not _STUBS_AVAILABLE:
            return None

        return cache_pb2.ValueResponse(
            key         = key,
            value       = value if value is not None else b"",
            found       = value is not None,
            source_tier = _TIER_TO_PROTO.get(tier, cache_pb2.DB_BACKEND),
            meta        = self._make_meta(rid, latency_ms),
        )


    async def SetValue(self, request, context):
        t0    = time.monotonic()
        entry = request.entry
        rid   = request.meta.request_id if request.HasField("meta") else str(uuid.uuid4())

        await self._manager.put(
            key           = entry.key,
            value         = entry.value,
            ttl_seconds   = entry.ttl_seconds,
            write_through = request.write_through,
        )
        latency_ms = (time.monotonic() - t0) * 1000

        if not _STUBS_AVAILABLE:
            return None

        return cache_pb2.SetResponse(
            success = True,
            message = f"Stored key '{entry.key}' successfully",
            meta    = self._make_meta(rid, latency_ms),
        )


    async def DeleteValue(self, request, context):
        t0      = time.monotonic()
        key     = request.key
        rid     = request.meta.request_id if request.HasField("meta") else str(uuid.uuid4())
        deleted = await self._manager.delete(key)
        latency_ms = (time.monotonic() - t0) * 1000

        if not _STUBS_AVAILABLE:
            return None

        return cache_pb2.DeleteResponse(
            deleted = deleted,
            meta    = self._make_meta(rid, latency_ms),
        )


    async def SetPolicy(self, request, context):
        t0         = time.monotonic()
        rid        = request.meta.request_id if request.HasField("meta") else str(uuid.uuid4())
        new_policy = _proto_to_policy(request.policy)
        capacity   = request.capacity

        result = await self._manager.swap_policy(new_policy, capacity)
        latency_ms = (time.monotonic() - t0) * 1000

        if not _STUBS_AVAILABLE:
            return None

        return cache_pb2.ToggleResponse(
            success          = True,
            active_policy    = _POLICY_TO_PROTO.get(new_policy, cache_pb2.LRU),
            current_capacity = self._manager.capacity,
            message          = (
                f"Policy switched to {new_policy.value}; "
                f"migrated {result['migrated_keys']} keys"
            ),
            meta             = self._make_meta(rid, latency_ms),
        )


    async def GetStats(self, request, context):
        if not _STUBS_AVAILABLE:
            return None
        return self._stats_proto()

    async def MonitorEvents(
        self,
        request,
        context,
    ) -> AsyncIterator:
        client_id   = request.client_id or str(uuid.uuid4())
        filter_set  = set(request.filter_types)   # empty set = all events

        logger.info("MonitorEvents stream opened | client=%s", client_id)

        queue: asyncio.Queue[CacheEvent] = asyncio.Queue(maxsize=512)

        async def _enqueue(event: CacheEvent) -> None:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                # Drop the event rather than blocking the server
                logger.warning("Event queue full for client %s — dropping event", client_id)

        self._manager.subscribe(_enqueue)

        try:
            while not context.done():
                try:
                    event: CacheEvent = await asyncio.wait_for(
                        queue.get(), timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue

                if filter_set:
                    proto_kind = _KIND_TO_PROTO.get(event.kind)
                    if proto_kind not in filter_set:
                        continue

                if not _STUBS_AVAILABLE:
                    continue

                stats_snapshot = event.stats or {}

                proto_event = cache_pb2.CacheEvent(
                    event_type   = _KIND_TO_PROTO.get(event.kind, cache_pb2.MISS),
                    key          = event.key,
                    tier         = _TIER_TO_PROTO.get(event.tier, cache_pb2.L1_MEMORY),
                    latency_ms   = event.latency_ms,
                    policy       = _POLICY_TO_PROTO.get(event.policy, cache_pb2.LRU),
                    detail       = event.detail,
                    timestamp_ms = event.timestamp_ms,
                    stats        = cache_pb2.CacheStats(
                        total_requests  = stats_snapshot.get("total_requests", 0),
                        l1_hits         = stats_snapshot.get("l1_hits", 0),
                        l2_hits         = stats_snapshot.get("l2_hits", 0),
                        db_hits         = stats_snapshot.get("db_hits", 0),
                        total_evictions = stats_snapshot.get("total_evictions", 0),
                        hit_rate        = stats_snapshot.get("hit_rate", 0.0),
                        avg_latency_ms  = stats_snapshot.get("avg_latency_ms", 0.0),
                        l1_size         = stats_snapshot.get("size", 0),
                        l1_capacity     = stats_snapshot.get("capacity", 0),
                        active_policy   = _POLICY_TO_PROTO.get(
                            self._manager.active_policy, cache_pb2.LRU
                        ),
                    ),
                )
                yield proto_event

        finally:
            self._manager.unsubscribe(_enqueue)
            logger.info("MonitorEvents stream closed | client=%s", client_id)



async def serve(
    host:        str   = "0.0.0.0",
    port:        int   = 50051,
    capacity:    int   = 256,
    policy:      str   = "LRU",
    redis_url:   str   = "redis://localhost:6379",
    tls_cert:    str   = "",
    tls_key:     str   = "",
) -> None:
    _init_proto_maps()

    manager = CacheManager(
        capacity = capacity,
        policy   = Policy[policy.upper()],
    )
    await manager.connect_redis(redis_url)

    server = grpc_aio.server(
        options=[
            ("grpc.max_send_message_length",    64 * 1024 * 1024),
            ("grpc.max_receive_message_length",  64 * 1024 * 1024),
            ("grpc.keepalive_time_ms",           30_000),
            ("grpc.keepalive_timeout_ms",        10_000),
            ("grpc.http2.max_pings_without_data", 0),
        ]
    )

    if _STUBS_AVAILABLE:
        servicer = AegisCacheServicer(manager)
        cache_pb2_grpc.add_AegisCacheServicer_to_server(servicer, server)
    else:
        logger.warning(
            "Protobuf stubs not found — server started in stub-less mode. "
            "Run `make proto` to generate them."
        )

    if tls_cert and tls_key:
        with open(tls_cert, "rb") as f:
            cert_data = f.read()
        with open(tls_key, "rb") as f:
            key_data = f.read()
        credentials = grpc.ssl_server_credentials([(key_data, cert_data)])
        server.add_secure_port(f"{host}:{port}", credentials)
        logger.info("gRPC server listening on %s:%d (TLS)", host, port)
    else:
        server.add_insecure_port(f"{host}:{port}")
        logger.info("gRPC server listening on %s:%d (plain-text)", host, port)

    await server.start()

    async def _shutdown_handler() -> None:
        logger.info("Shutting down gRPC server …")
        await server.stop(grace=5)
        await manager.disconnect_redis()

    # Graceful shutdown on SIGINT / SIGTERM
    loop = asyncio.get_running_loop()
    for sig_name in ("SIGINT", "SIGTERM"):
        import signal as _signal
        try:
            loop.add_signal_handler(
                getattr(_signal, sig_name),
                lambda: asyncio.ensure_future(_shutdown_handler()),
            )
        except (NotImplementedError, AttributeError):
            pass  # Windows

    await server.wait_for_termination()



if __name__ == "__main__":
    import argparse

    logging.basicConfig(
        level   = logging.INFO,
        format  = "%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        datefmt = "%Y-%m-%dT%H:%M:%S",
    )

    parser = argparse.ArgumentParser(description="AegisCache gRPC sidecar server")
    parser.add_argument("--host",      default="0.0.0.0",              help="Bind host")
    parser.add_argument("--port",      type=int, default=50051,         help="Bind port")
    parser.add_argument("--capacity",  type=int, default=256,           help="L1 capacity")
    parser.add_argument("--policy",    default="LRU",
                        choices=["LRU", "LFU", "FIFO"],                 help="Eviction policy")
    parser.add_argument("--redis",     default="redis://localhost:6379", help="Redis URL")
    parser.add_argument("--tls-cert",  default="",                      help="TLS certificate path")
    parser.add_argument("--tls-key",   default="",                      help="TLS private key path")
    args = parser.parse_args()

    asyncio.run(serve(
        host      = args.host,
        port      = args.port,
        capacity  = args.capacity,
        policy    = args.policy,
        redis_url = args.redis,
        tls_cert  = args.tls_cert,
        tls_key   = args.tls_key,
    ))