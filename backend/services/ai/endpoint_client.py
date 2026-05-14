"""Direct AWS endpoint client — calls the app's own REST endpoints or AWS SDK."""

import os
import json
import logging
import traceback
from typing import Dict, Any

from httpx import AsyncClient

logger = logging.getLogger(__name__)


def get_backend_url() -> str:
    return "http://backend:8000" if os.environ.get("DOCKER_ENV") == "true" else "http://localhost:8000"


async def call_direct_endpoint(service: str, action: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Call an internal REST endpoint or the AWS SDK directly for common operations."""
    role_arn = payload.get('role_arn')
    external_id = payload.get('external_id')
    region = payload.get('region', 'us-east-1')

    credentials = {'role_arn': role_arn, 'external_id': external_id, 'region': region}

    try:
        # EC2 direct SDK calls
        if service == 'ec2':
            from services.aws.client import get_aws_client
            from services.aws.ec2 import list_instances, create_instance

            ec2_client = get_aws_client('ec2', credentials)

            if action in ('list-instances', 'all-instances'):
                result = await list_instances(ec2_client)
                return _format_instance_listing(result, region)

            if action == 'running-instances':
                result = await list_instances(ec2_client, filter_state='running')
                return _format_instance_listing(result, region, running_only=True)

            if action == 'create-instance':
                instance_type = payload.get('instance_type', 't2.micro')
                if not isinstance(instance_type, str):
                    instance_type = str(instance_type) or 't2.micro'
                count = payload.get('count', 1)
                try:
                    count = int(count)
                except (ValueError, TypeError):
                    count = 1
                tags = payload.get('tags', {})
                return await create_instance(ec2_client, count=count, instance_type=instance_type, tags=tags)

        # S3 direct SDK calls
        if service == 's3':
            from services.aws.client import get_aws_client
            from services.aws.s3 import list_buckets, create_bucket, delete_bucket

            s3_client = get_aws_client('s3', credentials)

            if action == 'list-buckets':
                return await _list_buckets_with_fallback(s3_client, payload)

            if action == 'create-bucket':
                bucket_name = payload.get('bucket_name')
                if not bucket_name:
                    return {"success": False, "message": "Bucket name is required"}
                return await create_bucket(s3_client, bucket_name=bucket_name, region=region)

            if action == 'delete-bucket':
                bucket_name = payload.get('bucket_name')
                if not bucket_name:
                    return {"success": False, "message": "Bucket name is required"}
                force = payload.get('force', False)
                result = await delete_bucket(s3_client, bucket_name=bucket_name, force=force)
                if result and isinstance(result, dict) and result.get('success'):
                    result['message'] = f"Successfully deleted S3 bucket '{bucket_name}'."
                    result['data'] = {'bucket_name': bucket_name, 'region': region, 'action': 'deleted'}
                return result

        # Fallback: HTTP request to internal endpoint
        base_url = get_backend_url()
        endpoint_url = f"{base_url}/api/direct/{service}/{action}"
        timeout = 180.0 if service == "ec2" and action == "create-instance" else 60.0

        async with AsyncClient() as client:
            response = await client.post(endpoint_url, json=payload, timeout=timeout)

        try:
            result = response.json()
        except ValueError:
            return {"success": False, "error": f"Invalid response from {service}/{action}"}

        if response.status_code != 200:
            return {"success": False, "error": result.get('detail', 'Unknown error')}

        if action in ('all-instances', 'running-instances'):
            details = result.get('details', [])
            return {
                "success": True,
                "data": {"type": "success", "content": result.get('message', ''), "result": details},
            }

        return {"success": True, "data": result}

    except Exception as e:
        logger.error(f"Error in direct AWS operation {service}/{action}: {e}")
        logger.error(traceback.format_exc())
        return {"type": "error", "content": f"Error in {service}/{action}: {e}", "error": str(e)}


def _format_instance_listing(result: dict, region: str, running_only: bool = False) -> dict:
    instances = result.get('details', [])
    count = len(instances)
    label = "running " if running_only else ""

    for inst in instances:
        iid = inst.get('id')
        if iid and 'console_link' not in inst:
            inst['console_link'] = (
                f"https://{region}.console.aws.amazon.com/ec2/home"
                f"?region={region}#InstanceDetails:instanceId={iid}"
            )

    if count == 0:
        message = f"You don't have any {label}EC2 instances."
    else:
        message = f"Found {count} {label}EC2 instance(s)."

    return {
        "success": True,
        "message": message,
        "instances": instances,
        "count": count,
        "region": region,
        "console_links": [i.get('console_link', '') for i in instances if i.get('id')],
    }


async def _list_buckets_with_fallback(s3_client, payload: dict) -> dict:
    """List S3 buckets, trying the direct endpoint first then falling back to SDK."""
    from services.aws.s3 import list_buckets

    try:
        async with AsyncClient() as client:
            resp = await client.post(
                f"{get_backend_url()}/api/direct/s3/list-buckets",
                json={k: payload[k] for k in ('role_arn', 'external_id', 'region') if k in payload},
                headers={"Content-Type": "application/json"},
                timeout=30.0,
            )
            if resp.status_code == 200:
                result = resp.json()
            else:
                result = await list_buckets(s3_client)
    except Exception:
        result = await list_buckets(s3_client)

    if not result:
        result = {"success": True, "message": "No buckets found."}
    result.setdefault('buckets', [])
    result.setdefault('bucket_details', [])
    result['data'] = {'buckets': result['buckets'], 'bucket_details': result['bucket_details']}

    bucket_count = len(result['buckets'])
    if bucket_count == 0:
        result['message'] = "No S3 buckets found. Would you like me to create one?"
    else:
        result['message'] = f"Found {bucket_count} S3 bucket{'s' if bucket_count != 1 else ''}."

    return result
