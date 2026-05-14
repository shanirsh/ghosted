"""EC2 routes — listing endpoint used by the executor fallback path."""

from fastapi import APIRouter, HTTPException, Request

from services.aws.ec2 import get_aws_client, list_instances

router = APIRouter()


@router.post("/list-running-instances")
async def list_running_instances(request: Request):
    data = await request.json()
    if not data.get("role_arn"):
        raise HTTPException(status_code=400, detail="role_arn is required")
    if not data.get("external_id"):
        raise HTTPException(status_code=400, detail="external_id is required")

    credentials = {
        "role_arn": data["role_arn"],
        "external_id": data["external_id"],
        "region": data.get("region", "us-east-1"),
    }
    return await list_instances(get_aws_client(credentials), filter_state="running")
