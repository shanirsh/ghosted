"""Advanced AI-powered routes for Ghosted Cloud AI."""

import logging

from fastapi import APIRouter, HTTPException, Request

from services.aws.executor import AWSExecutor
from services.ai.processor import AIProcessor

logger = logging.getLogger(__name__)

router = APIRouter()
ai_processor = None
try:
    ai_processor = AIProcessor()
except Exception as e:
    logger.error(f"Failed to initialize AI processor: {e}")


@router.post("/process")
async def process_advanced_command(request: Request):
    try:
        data = await request.json()

        command = data.get("command")
        role_arn = data.get("role_arn")
        external_id = data.get("external_id")
        region = data.get("region", "us-east-1")

        if not command:
            raise HTTPException(status_code=400, detail="command is required")
        if not role_arn:
            raise HTTPException(status_code=400, detail="role_arn is required")
        if not external_id:
            raise HTTPException(status_code=400, detail="external_id is required")

        credentials = {"role_arn": role_arn, "external_id": external_id, "region": region}

        if not ai_processor:
            return {"type": "error", "content": "AI processing is not available. Please check if OpenAI API key is configured."}

        executor = AWSExecutor(credentials)
        return await ai_processor.process_command(command, executor, credentials=credentials)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing advanced command: {e}", exc_info=True)
        return {"type": "error", "content": f"I encountered an error processing your request: {e}"}
