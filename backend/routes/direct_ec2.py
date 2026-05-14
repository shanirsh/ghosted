"""Direct EC2 routes — bypass AI interpretation for EC2 operations."""

import logging
from typing import Any, Dict, Tuple

from fastapi import APIRouter, HTTPException, Request

from services.aws.ec2 import (
    get_aws_client, list_instances, create_instance, stop_instance,
    start_instance, terminate_instance, reboot_instance, describe_instance,
    check_termination_protection, disable_termination_protection,
)
from services.aws.ec2_bulk_operations import (
    stop_all_instances, terminate_all_instances,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Shared helpers ───────────────────────────────────────────────────────────

async def _parse_request(request: Request, require_instance_id: bool = False) -> Tuple[dict, Dict[str, Any]]:
    """Parse JSON body, validate credentials, return (credentials, data)."""
    data = await request.json()
    role_arn = data.get("role_arn")
    external_id = data.get("external_id")

    if not role_arn:
        raise HTTPException(status_code=400, detail="role_arn is required")
    if not external_id:
        raise HTTPException(status_code=400, detail="external_id is required")
    if require_instance_id and not data.get("instance_id"):
        raise HTTPException(status_code=400, detail="instance_id is required")

    credentials = {
        "role_arn": role_arn,
        "external_id": external_id,
        "region": data.get("region", "us-east-1"),
    }
    return credentials, data


def _extract_create_params(data: dict) -> dict:
    """Extract instance creation parameters from request data."""
    name = data.get("name") or data.get("instance_name") or "Ghosted-Instance"

    storage_config = {"size": data.get("volume_size", 8), "type": data.get("volume_type", "gp2")}
    if "iops" in data and storage_config["type"] in ("io1", "io2", "gp3"):
        storage_config["iops"] = data["iops"]
    if "throughput" in data and storage_config["type"] == "gp3":
        storage_config["throughput"] = data["throughput"]

    tags = data.get("tags", {}) if isinstance(data.get("tags"), dict) else {}
    tags["Name"] = name
    tags.setdefault("AutoShutdown", "Disabled")
    tags.setdefault("KeepRunning", "True")
    tags.setdefault("CreatedBy", "GhostedCloudAIBot")

    try:
        count = int(data.get("count", 1))
    except (ValueError, TypeError):
        count = 1

    return {
        "instance_type": data.get("instance_type", "t2.micro"),
        "count": count,
        "tags": tags,
        "storage_config": storage_config,
        "user_data": data.get("user_data"),
        "name": name,
    }


def _add_console_links(instances: list, region: str) -> None:
    for inst in instances:
        iid = inst.get("id")
        if iid and "console_link" not in inst:
            inst["console_link"] = (
                f"https://{region}.console.aws.amazon.com/ec2/home"
                f"?region={region}#InstanceDetails:instanceId={iid}"
            )


# ── Instance listing ─────────────────────────────────────────────────────────

@router.post("/running-instances")
async def list_running_instances_route(request: Request):
    credentials, _ = await _parse_request(request)
    ec2 = get_aws_client(credentials)
    result = await list_instances(ec2, filter_state="running")
    _add_console_links(result.get("details", []), credentials["region"])
    result["instances"] = result.get("details", [])
    return result


@router.post("/all-instances")
async def list_all_instances_route(request: Request):
    credentials, _ = await _parse_request(request)
    ec2 = get_aws_client(credentials)
    result = await list_instances(ec2)
    _add_console_links(result.get("details", []), credentials["region"])
    result["instances"] = result.get("details", [])
    return result


# ── Single-instance operations ───────────────────────────────────────────────

@router.post("/stop-instance")
async def stop_ec2_instance(request: Request):
    credentials, data = await _parse_request(request, require_instance_id=True)
    ec2 = get_aws_client(credentials)
    return await stop_instance(ec2, data["instance_id"])


@router.post("/start-instance")
async def start_ec2_instance(request: Request):
    credentials, data = await _parse_request(request, require_instance_id=True)
    ec2 = get_aws_client(credentials)
    return await start_instance(ec2, data["instance_id"])


@router.post("/reboot-instance")
async def reboot_ec2_instance(request: Request):
    credentials, data = await _parse_request(request, require_instance_id=True)
    ec2 = get_aws_client(credentials)
    return await reboot_instance(ec2, data["instance_id"])


@router.post("/describe-instance")
async def describe_ec2_instance(request: Request):
    credentials, data = await _parse_request(request, require_instance_id=True)
    ec2 = get_aws_client(credentials)
    return await describe_instance(ec2, data["instance_id"])


@router.post("/terminate-instance")
async def terminate_ec2_instance(request: Request):
    credentials, data = await _parse_request(request, require_instance_id=True)
    ec2 = get_aws_client(credentials)
    instance_id = data["instance_id"]

    protection = await check_termination_protection(ec2, instance_id)
    if not protection["success"]:
        return protection
    if protection.get("is_protected"):
        disable_result = await disable_termination_protection(ec2, instance_id)
        if not disable_result["success"]:
            return disable_result

    result = await terminate_instance(ec2, instance_id)
    if protection.get("is_protected") and result.get("success"):
        result["message"] = f"Termination protection was disabled. {result['message']}"
    return result


# ── Create / deploy ──────────────────────────────────────────────────────────

@router.post("/create-instance")
async def create_ec2_instance(request: Request):
    credentials, data = await _parse_request(request)
    ec2 = get_aws_client(credentials)
    params = _extract_create_params(data)

    result = await create_instance(
        ec2,
        count=params["count"],
        instance_type=params["instance_type"],
        tags=params["tags"],
        storage_config=params["storage_config"],
        user_data=params["user_data"],
        region=credentials["region"],
    )
    if result.get("success"):
        result["region"] = credentials["region"]
        result["instance_name"] = params["name"]
    return result


@router.post("/multi-region-deploy")
async def deploy_ec2_to_multiple_regions(request: Request):
    credentials, data = await _parse_request(request)
    regions = data.get("regions", [])
    if not regions or not isinstance(regions, list):
        raise HTTPException(status_code=400, detail="regions must be a non-empty list")

    params = _extract_create_params(data)
    params["tags"]["MultiRegionDeploy"] = "True"

    results = []
    for region in regions:
        try:
            region_creds = {**credentials, "region": region}
            ec2 = get_aws_client(region_creds)
            region_result = await create_instance(
                ec2,
                count=params["count"],
                instance_type=params["instance_type"],
                tags=params["tags"],
                storage_config=params["storage_config"],
                user_data=params["user_data"],
                region=region,
            )
            region_result["region"] = region
            region_result["instance_name"] = params["name"]
            results.append(region_result)
        except Exception as e:
            logger.error(f"Error deploying to {region}: {e}")
            results.append({"success": False, "message": str(e), "region": region})

    ok = sum(1 for r in results if r.get("success"))
    if ok == len(regions):
        msg = f"Successfully deployed {params['name']} to all {len(regions)} regions"
    elif ok > 0:
        msg = f"Partially successful: {ok}/{len(regions)} regions succeeded"
    else:
        msg = f"Failed to deploy to any of the {len(regions)} regions"

    return {
        "success": ok > 0,
        "message": msg,
        "results": results,
        "regions": regions,
        "instance_name": params["name"],
    }


# ── Bulk operations ──────────────────────────────────────────────────────────

@router.post("/stop-all-instances")
async def stop_all_ec2_instances(request: Request):
    credentials, _ = await _parse_request(request)
    ec2 = get_aws_client(credentials)
    result = await stop_all_instances(ec2)
    if result.get("success"):
        result["region"] = credentials["region"]
    return result


@router.post("/terminate-all-instances")
async def terminate_all_ec2_instances(request: Request):
    credentials, _ = await _parse_request(request)
    ec2 = get_aws_client(credentials)
    result = await terminate_all_instances(ec2)
    if result.get("success"):
        result["region"] = credentials["region"]
    return result
