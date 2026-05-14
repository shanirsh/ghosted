"""Conversational AI-powered routes for Ghosted Cloud AI."""

from utils.logging_config import get_logger, bind_request_context
logger = get_logger(__name__)

from fastapi import APIRouter, Request
import re
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, validator, constr
from services.aws.ec2 import (
    get_aws_client as get_ec2_client,
    list_instances,
    create_instance,
    stop_instance,
    start_instance,
    terminate_instance,
)
from services.aws.s3 import (
    get_aws_client as get_s3_client,
    create_bucket,
    list_buckets,
)
from services.ai.processor import AIProcessor
from services.aws.executor import AWSExecutor
from utils.secrets import get_secrets_manager
import uuid


class CommandRequest(BaseModel):
    command: constr(min_length=1, max_length=1000) = Field(..., description="The command to process")
    user_id: constr(min_length=1, max_length=100) = Field("default_user", description="User identifier")
    aws_credentials: Optional[Dict[str, str]] = Field(None, description="AWS credentials")
    conversation_history: Optional[List[Dict[str, str]]] = Field(None, description="Previous conversation history")

    @validator("command")
    def validate_command(cls, v):
        suspicious_patterns = [
            r";\s*rm\s", r";\s*dd\s", r";\s*wget\s", r";\s*curl\s",
            r"`.*`", r"\$\(.*\)", r">\s*/etc", r">>\s*/etc",
        ]
        for pattern in suspicious_patterns:
            if re.search(pattern, v):
                raise ValueError(f"Command contains potentially malicious pattern")
        return v


class CommandResponse(BaseModel):
    type: str = Field(..., description="Response type (success or error)")
    content: str = Field(..., description="Response content")
    details: Optional[Dict[str, Any]] = Field({}, description="Additional response details")


router = APIRouter()
secrets_manager = get_secrets_manager()

ai_processor = None
try:
    ai_processor = AIProcessor()
    logger.info("AI processor initialized successfully")
except Exception as e:
    logger.error("Failed to initialize AI components", error=str(e))


def _build_executor(credentials: dict):
    return AWSExecutor(credentials)


def _extract_credentials(request_data: CommandRequest):
    creds = request_data.aws_credentials or {}
    return {
        "role_arn": creds.get("role_arn"),
        "external_id": creds.get("external_id"),
        "region": creds.get("region", "us-east-1"),
    }


@router.post("/test-ai", response_model=CommandResponse)
async def test_ai_processor(request_data: CommandRequest, request: Request):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    log = bind_request_context(logger, request_id)

    try:
        if not ai_processor:
            return CommandResponse(type="error", content="AI processing is not available.", details={"request_id": request_id})

        credentials = _extract_credentials(request_data)
        log.info("Processing test AI command", command=request_data.command)

        executor = _build_executor(credentials)
        result = await ai_processor.process_command(request_data.command, executor, credentials=credentials)

        return CommandResponse(
            type=result.get("type", "success"),
            content=result.get("content", "I processed your command."),
            details={"result": result, "request_id": request_id},
        )
    except Exception as e:
        log.error("Error in test AI processor", error=str(e))
        return CommandResponse(type="error", content=f"Error processing your command: {e}", details={"request_id": request_id})


@router.post("/process", response_model=CommandResponse)
async def process_conversational_command(request_data: CommandRequest, request: Request):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    log = bind_request_context(logger, request_id)

    try:
        command = request_data.command
        credentials = _extract_credentials(request_data)

        if not command:
            return CommandResponse(type="error", content="Command is required", details={"request_id": request_id})
        if not credentials["role_arn"]:
            return CommandResponse(type="error", content="Role ARN is required for AWS operations", details={"request_id": request_id})
        if not credentials["external_id"]:
            return CommandResponse(type="error", content="External ID is required for AWS operations", details={"request_id": request_id})

        if not ai_processor:
            return CommandResponse(type="error", content="AI processing is not available.", details={"request_id": request_id})

        log.info("Processing command", command=command, region=credentials["region"])

        executor = _build_executor(credentials)
        result = await ai_processor.process_command(command, executor, credentials=credentials)

        return CommandResponse(
            type=result.get("type", "success"),
            content=result.get("content", "I processed your command."),
            details={"result": result, "request_id": request_id},
        )
    except Exception as e:
        log.error("Unhandled exception in process_command", error=str(e), error_type=type(e).__name__)
        return CommandResponse(
            type="error",
            content="An unexpected error occurred. Our team has been notified.",
            details={"error": "Internal server error", "request_id": request_id},
        )
