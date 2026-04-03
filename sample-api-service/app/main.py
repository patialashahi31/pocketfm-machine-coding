from __future__ import annotations

import logging
import os
import sys
from typing import Any

import httpx
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


app = FastAPI(title="sample-api-service")
RATE_LIMITER_URL = os.getenv(
    "RATE_LIMITER_URL", "http://rate-limiter-service:8001/v1/rate-limits/check"
)
logger = logging.getLogger("sample-api-service")

if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
    )
    logger.addHandler(handler)

logger.setLevel(logging.INFO)
logger.propagate = False


class EchoRequest(BaseModel):
    message: str = Field(..., min_length=1, description="Message to echo back")
    client_id: str = Field(..., min_length=1, description="Client identifier to rate limit")


def check_rate_limit(client_id: str) -> dict[str, Any]:
    payload = {
        "service_name": "sample-api-service",
        "client_id": client_id,
        "route": "/v1/echo",
    }

    try:
        response = httpx.post(RATE_LIMITER_URL, json=payload, timeout=5.0)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as exc:
        raise RuntimeError("Rate limiter rejected the request") from exc
    except httpx.RequestError as exc:
        raise ConnectionError("Rate limiter is unavailable") from exc


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "sample-api-service",
    }


@app.post("/v1/echo")
def echo(payload: EchoRequest) -> dict[str, Any]:
    logger.info(
        "Received echo request client_id=%s message=%s",
        payload.client_id,
        payload.message,
    )
    try:
        rate_limit_result = check_rate_limit(payload.client_id)
    except ConnectionError:
        logger.warning("Rate limiter unavailable for client_id=%s", payload.client_id)
        return JSONResponse(
            status_code=503,
            content={
                "detail": "rate_limiter_unavailable",
            },
        )
    except RuntimeError:
        logger.warning("Rate limiter error for client_id=%s", payload.client_id)
        return JSONResponse(
            status_code=503,
            content={
                "detail": "rate_limiter_error",
            },
        )

    logger.info("Rate limiter response client_id=%s payload=%s", payload.client_id, rate_limit_result)

    if not rate_limit_result["allowed"]:
        response_body = {
            "detail": "rate_limit_exceeded",
            "rate_limit": {
                "limit": rate_limit_result["limit"],
                "remaining": rate_limit_result["remaining"],
                "window_seconds": rate_limit_result["window_seconds"],
                "retry_after_seconds": rate_limit_result["retry_after_seconds"],
                "current_count": rate_limit_result["current_count"],
            },
        }
        logger.info("Returning rate limited response client_id=%s payload=%s", payload.client_id, response_body)
        return JSONResponse(
            status_code=429,
            content=response_body,
        )

    response_body = {
        "message": payload.message,
        "status": "received",
        "client_id": payload.client_id,
        "rate_limit": {
            "limit": rate_limit_result["limit"],
            "remaining": rate_limit_result["remaining"],
            "window_seconds": rate_limit_result["window_seconds"],
            "current_count": rate_limit_result["current_count"],
        },
    }
    logger.info("Returning success response client_id=%s payload=%s", payload.client_id, response_body)
    return response_body
