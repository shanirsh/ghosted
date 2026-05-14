"""Centralized role-based AWS authentication for Ghosted Cloud AI."""

import boto3
import logging
import os
import time
from typing import Dict, Any, Optional
from botocore.config import Config

logger = logging.getLogger(__name__)

_credential_cache = {}
_CACHE_EXPIRY_BUFFER = 900  # Refresh 15 minutes before actual expiry


def _make_service_config():
    return Config(connect_timeout=5, read_timeout=5, retries={"max_attempts": 1})


def get_aws_client(
    service_name: str,
    credentials: Optional[Dict[str, Any]] = None,
    default_region: str = None,
) -> Any:
    """Create an AWS service client via STS AssumeRole or the default credential chain."""
    role_arn = (credentials or {}).get("role_arn") or os.environ.get("AWS_ROLE_ARN")
    external_id = (credentials or {}).get("external_id")
    region = (credentials or {}).get("region") or default_region or os.environ.get("AWS_REGION", "us-east-1")

    if not role_arn:
        logger.info(f"No role ARN — using default credential chain for {service_name} in {region}")
        return boto3.client(service_name, region_name=region)

    cache_key = f"{role_arn}:{external_id or ''}:{region}"
    now = time.time()

    if cache_key in _credential_cache:
        entry = _credential_cache[cache_key]
        if now < entry["expiration_time"] - _CACHE_EXPIRY_BUFFER:
            logger.info(f"Using cached credentials for {service_name} in {region}")
            creds = entry["credentials"]
            return boto3.client(
                service_name,
                region_name=region,
                aws_access_key_id=creds["AccessKeyId"],
                aws_secret_access_key=creds["SecretAccessKey"],
                aws_session_token=creds["SessionToken"],
                config=_make_service_config(),
            )

    logger.info(f"Assuming role for {service_name} in {region}")
    sts_client = boto3.client("sts", region_name=region)
    params = {"RoleArn": role_arn, "RoleSessionName": "GhostedAISession", "DurationSeconds": 3600}
    if external_id:
        params["ExternalId"] = external_id

    try:
        assumed = sts_client.assume_role(**params)
    except Exception as e:
        logger.error(f"Error assuming role: {e}")
        logger.info("Falling back to default credential chain")
        return boto3.client(service_name, region_name=region)

    temp_creds = assumed["Credentials"]
    expiration = temp_creds["Expiration"]
    exp_ts = expiration.timestamp() if hasattr(expiration, "timestamp") else time.mktime(expiration.timetuple())
    _credential_cache[cache_key] = {"credentials": temp_creds, "expiration_time": exp_ts}

    return boto3.client(
        service_name,
        region_name=region,
        aws_access_key_id=temp_creds["AccessKeyId"],
        aws_secret_access_key=temp_creds["SecretAccessKey"],
        aws_session_token=temp_creds["SessionToken"],
        config=_make_service_config(),
    )
