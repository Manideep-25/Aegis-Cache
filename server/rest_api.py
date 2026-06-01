import os
import sys
import time
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
from contextlib import asynccontextmanager
from fastapi.responses import StreamingResponse
import asyncio, json

from cache.manager import CacheManager, Policy, Tier


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("aegiscache.api")

manager = CacheManager(capacity=256, policy=Policy.LRU)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("FastAPI starting up - connecting to Redis...")
    await manager.connect_redis("redis://localhost:6379")
    logger.info("FastAPI ready on http://0.0.0.0:8000")
    logger.info("Swagger docs at http://0.0.0.0:8000/docs")
    yield
    logger.info("FastAPI shutting down...")
    await manager.disconnect_redis()


app = FastAPI(
    title="AegisCache REST API",
    description=(
        "REST interface for AegisCache — a high-performance distributed "
        "caching middleware with LRU/LFU/FIFO eviction strategies and "
        "two-tier L1 memory + L2 Redis caching."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8080"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class SetRequest(BaseModel):
    value:         str  = Field(...,   description="Value to cache (string)")
    ttl_seconds:   int  = Field(0,     description="Time-to-live in seconds. 0 = no expiry")
    write_through: bool = Field(False, description="If true, also writes to L2 Redis")

class SetResponse(BaseModel):
    success: bool
    key:     str
    message: str

class GetResponse(BaseModel):
    key:        str
    found:      bool
    value:      Optional[str]
    tier:       str
    latency_ms: float

class DeleteResponse(BaseModel):
    key:     str
    deleted: bool

class PolicyRequest(BaseModel):
    policy:   str = Field(..., description="Eviction policy: LRU, LFU, or FIFO")
    capacity: int = Field(0,   description="New L1 capacity. 0 = keep current")

class PolicyResponse(BaseModel):
    success:       bool
    active_policy: str
    migrated_keys: int
    message:       str

class StatsResponse(BaseModel):
    active_policy:   str
    capacity:        int
    size:            int
    total_requests:  int
    l1_hits:         int
    l2_hits:         int
    db_hits:         int
    total_evictions: int
    hit_rate:        float
    avg_latency_ms:  float

class HealthResponse(BaseModel):
    status: str
    policy: str
    size:   int


def _tier_label(tier: Tier) -> str:
    return {
        Tier.L1_MEMORY:  "L1_MEMORY",
        Tier.L2_REDIS:   "L2_REDIS",
        Tier.DB_BACKEND: "DB_BACKEND",
    }.get(tier, "UNKNOWN")


@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    tags=["System"],
)
async def health():
    stats = manager.get_stats()
    return HealthResponse(
        status="ok",
        policy=manager.active_policy.value,
        size=stats["size"],
    )


@app.get(
    "/cache/{key}",
    response_model=GetResponse,
    summary="Get a cached value",
    tags=["Cache"],
)
async def get_value(key: str):
    start      = time.monotonic()
    value, tier = await manager.get(key)
    latency_ms  = round((time.monotonic() - start) * 1000, 3)

    return GetResponse(
        key        = key,
        found      = value is not None,
        value      = value.decode() if value else None,
        tier       = _tier_label(tier),
        latency_ms = latency_ms,
    )


@app.post(
    "/cache/{key}",
    response_model=SetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Store a value in the cache",
    tags=["Cache"],
)
async def set_value(key: str, body: SetRequest):
    await manager.put(
        key           = key,
        value         = body.value.encode(),
        ttl_seconds   = body.ttl_seconds,
        write_through = body.write_through,
    )
    return SetResponse(
        success = True,
        key     = key,
        message = f"Stored key '{key}' successfully",
    )


@app.delete(
    "/cache/{key}",
    response_model=DeleteResponse,
    summary="Delete a cached key",
    tags=["Cache"],
)
async def delete_value(key: str):
    deleted = await manager.delete(key)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Key '{key}' not found in cache",
        )
    return DeleteResponse(key=key, deleted=True)


@app.post(
    "/policy",
    response_model=PolicyResponse,
    summary="Switch eviction policy at runtime",
    tags=["Control"],
)
async def set_policy(body: PolicyRequest):
    policy_upper = body.policy.upper()
    if policy_upper not in ("LRU", "LFU", "FIFO"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid policy '{body.policy}'. Must be LRU, LFU, or FIFO.",
        )

    result = await manager.swap_policy(
        Policy[policy_upper],
        body.capacity,
    )

    return PolicyResponse(
        success       = True,
        active_policy = manager.active_policy.value,
        migrated_keys = result["migrated_keys"],
        message       = (
            f"Switched from {result['old_policy']} to "
            f"{result['new_policy']} — "
            f"migrated {result['migrated_keys']} keys"
        ),
    )


@app.get(
    "/stats",
    response_model=StatsResponse,
    summary="Get cache statistics",
    tags=["Observability"],
)
async def get_stats():
    s = manager.get_stats()
    return StatsResponse(
        active_policy   = s["active_policy"],
        capacity        = s["capacity"],
        size            = s["size"],
        total_requests  = s["total_requests"],
        l1_hits         = s["l1_hits"],
        l2_hits         = s["l2_hits"],
        db_hits         = s["db_hits"],
        total_evictions = s["total_evictions"],
        hit_rate        = s["hit_rate"],
        avg_latency_ms  = s["avg_latency_ms"],
    )


@app.get(
    "/events",
    summary="Live cache events stream (SSE)",
    tags=["Observability"],
)
async def event_stream(request: Request):
    queue: asyncio.Queue = asyncio.Queue()

    async def on_event(event):
        await queue.put(event)

    manager.subscribe(on_event)

    async def stream():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15.0)
                    try:
                        payload = {
                            "kind":         event.kind.name,
                            "key":          event.key,
                            "tier":         event.tier.name if event.tier else None,
                            "latency_ms":   event.latency_ms,
                            "policy":       event.policy.name if event.policy else None,
                            "detail":       event.detail,
                            "timestamp_ms": event.timestamp_ms,
                            "stats":        event.stats if event.stats else None,
                        }
                        yield f"data: {json.dumps(payload)}\n\n"
                    except Exception as e:
                        logger.error("SSE serialize error: %s", e)
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            manager.unsubscribe(on_event)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "rest_api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )