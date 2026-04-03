from __future__ import annotations

import json
import os
import time
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from redis import Redis
from redis.exceptions import RedisError


BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = Path(
    os.getenv("RATE_LIMIT_CONFIG_PATH", BASE_DIR / "config" / "rate_limits.json")
)
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))

app = FastAPI(title="rate-limiter-service")


class RateLimitCheckRequest(BaseModel):
    service_name: str = Field(..., min_length=1, description="Calling service name")
    client_id: str = Field(..., min_length=1, description="Unique subject to rate limit")
    route: str = Field(..., min_length=1, description="Route being accessed")


class RateLimitRule(BaseModel):
    limit: int = Field(..., gt=0)
    window_seconds: int = Field(..., gt=0)


@lru_cache(maxsize=1)
def load_config() -> dict[str, Any]:
    with CONFIG_PATH.open("r", encoding="utf-8") as config_file:
        return json.load(config_file)


@lru_cache(maxsize=1)
def get_redis_client() -> Redis:
    return Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)


def resolve_rule(service_name: str, route: str) -> RateLimitRule:
    config = load_config()
    service_config = config.get("services", {}).get(service_name, {})
    route_config = service_config.get("routes", {}).get(route)
    default_config = service_config.get("default") or config.get("default")

    selected_config = route_config or default_config
    if not selected_config:
        raise HTTPException(
            status_code=404,
            detail=f"No rate limit configuration found for service '{service_name}' and route '{route}'",
        )

    return RateLimitRule.model_validate(selected_config)


def build_redis_key(service_name: str, client_id: str, route: str, window_start: int) -> str:
    return f"rate-limit:{service_name}:{route}:{client_id}:{window_start}"


@app.get("/health")
def healthcheck() -> dict[str, str]:
    try:
        get_redis_client().ping()
    except RedisError as exc:
        raise HTTPException(status_code=503, detail="Redis unavailable") from exc

    return {
        "status": "ok",
        "service": "rate-limiter-service",
    }


@app.post("/v1/rate-limits/check")
def check_rate_limit(payload: RateLimitCheckRequest) -> dict[str, int | bool | str]:
    rule = resolve_rule(payload.service_name, payload.route)
    now = int(time.time())
    window_start = now - (now % rule.window_seconds)
    window_end = window_start + rule.window_seconds
    key = build_redis_key(payload.service_name, payload.client_id, payload.route, window_start)

    try:
        redis_client = get_redis_client()
        current_count = redis_client.incr(key)
        if current_count == 1:
            redis_client.expire(key, rule.window_seconds)
    except RedisError as exc:
        raise HTTPException(status_code=503, detail="Failed to evaluate rate limit") from exc

    allowed = current_count <= rule.limit
    remaining = max(rule.limit - current_count, 0)

    return {
        "allowed": allowed,
        "service_name": payload.service_name,
        "client_id": payload.client_id,
        "route": payload.route,
        "limit": rule.limit,
        "remaining": remaining,
        "window_seconds": rule.window_seconds,
        "window_start": window_start,
        "window_end": window_end,
        "retry_after_seconds": max(window_end - now, 0) if not allowed else 0,
        "current_count": current_count,
    }
