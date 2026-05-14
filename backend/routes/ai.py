"""Primary AI command processing route for Ghosted Cloud AI."""

import logging
import os
import re

from fastapi import APIRouter, Request
from starlette.responses import JSONResponse
from fastapi.responses import PlainTextResponse

from services.ai.processor import AIProcessor

logger = logging.getLogger(__name__)

global_processor = AIProcessor()

router = APIRouter()


def _get_backend_url():
    return "http://backend:8000" if os.environ.get("DOCKER_ENV") == "true" else "http://localhost:8000"


def _success(message: str, **extra) -> JSONResponse:
    return JSONResponse(content={"success": True, "message": message, **extra})


def _error(message: str) -> JSONResponse:
    return JSONResponse(content={"success": False, "message": message})


def _extract_buckets(result: dict):
    """Walk common nesting patterns and return (buckets, bucket_details)."""
    buckets, details = [], []
    for src in [result, result.get("result", {}), result.get("data", {}),
                (result.get("data", {}) or {}).get("result", {})]:
        if not isinstance(src, dict):
            continue
        if not buckets and isinstance(src.get("buckets"), list):
            buckets = src["buckets"]
        if not details and isinstance(src.get("bucket_details"), list):
            details = src["bucket_details"]
    return buckets, details


@router.post("/test")
async def test_endpoint():
    return PlainTextResponse("This is a test response")


@router.post("/process")
@router.post("/process-command")
async def process_command(request: Request):
    try:
        payload = await request.json()
    except Exception as e:
        return _error(f"Error parsing request: {e}")

    command = payload.get("command")
    role_arn = payload.get("role_arn")
    external_id = payload.get("external_id")
    region = payload.get("region", "us-east-1")

    if not command:
        return PlainTextResponse("Error: Command is required")
    if not role_arn:
        return PlainTextResponse("Error: AWS Role ARN is required")
    if not external_id:
        return PlainTextResponse("Error: External ID is required")

    credentials = {"role_arn": role_arn, "external_id": external_id, "region": region}
    user_id = payload.get("user_id", "default_user")
    conversation_history = payload.get("conversation_history", [])

    try:
        result = await global_processor.process_command(
            command=command,
            executor=None,
            credentials=credentials,
            conversation_history=conversation_history,
            user_id=user_id,
        )
    except Exception as e:
        logger.error(f"Error in processor: {e}", exc_info=True)
        return _error(f"Error in processor: {e}")

    if result is None:
        return _error("Failed to process command")

    if not isinstance(result, dict):
        return _success(str(result))

    content = result.get("content", "")
    rtype = result.get("type", "")
    data = result.get("data") or {}

    # S3 bucket listing
    is_bucket_listing = any(kw in (content or "").lower() for kw in ("s3 bucket", "list_buckets"))
    if is_bucket_listing or "buckets" in result or "bucket_details" in result:
        buckets, bucket_details = _extract_buckets(result)
        if buckets or bucket_details or is_bucket_listing:
            return JSONResponse(content={
                "success": True,
                "message": content or "S3 bucket listing complete.",
                "buckets": buckets,
                "bucket_details": bucket_details,
                "data": {"buckets": buckets, "bucket_details": bucket_details},
            })

    if rtype == "error":
        return _error(content or "Unknown error")

    if rtype == "success" and content:
        # S3 bucket creation/operation
        if isinstance(data, dict) and "bucket_name" in data:
            return JSONResponse(content={
                "success": True,
                "message": content,
                "data": data,
                "bucket": {"name": data["bucket_name"], "region": data.get("region", region)},
            })

        # EC2 instance operation
        if isinstance(data, dict) and ("instance_ids" in data or "instance" in result):
            instance_ids = data.get("instance_ids", [])
            if not isinstance(instance_ids, list):
                instance_ids = [instance_ids]
            return JSONResponse(content={
                "success": True,
                "message": content,
                "data": data,
                "instance": {"ids": instance_ids, "type": data.get("instance_type", "t2.micro"), "region": data.get("region", region)},
            })

        # List operation with array result
        if isinstance(result.get("result"), list):
            return JSONResponse(content={"success": True, "message": content, "data": {"items": result["result"], "count": len(result["result"])}})

        # EC2 listing with details
        nested = result.get("result", {})
        if isinstance(nested, dict) and "details" in nested:
            return JSONResponse(content={"success": True, "message": content, "instances": nested["details"]})

        return _success(content)

    if rtype == "success":
        nested = result.get("result", {})
        if isinstance(nested, dict) and "details" in nested:
            return JSONResponse(content={"success": True, "message": result.get("content", ""), "instances": nested["details"]})
        if isinstance(nested, (dict, list)):
            return JSONResponse(content={"success": True, "message": result.get("content", "Command processed"), "data": nested})
        return _success(result.get("content", "Command processed successfully."))

    if "message" in result:
        resp = {"success": True, "message": result["message"]}
        if data:
            resp["data"] = data
        return JSONResponse(content=resp)

    return _success("Command processed successfully.")
