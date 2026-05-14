"""Direct S3 routes — bypass AI interpretation for S3 operations."""

import logging
import os
import tempfile
from typing import Tuple, Dict, Any

from fastapi import APIRouter, HTTPException, Request, File, UploadFile, Form

from services.aws.s3 import (
    get_aws_client, list_buckets, create_bucket, delete_bucket,
    list_bucket_contents, upload_file, download_file, delete_object, configure_bucket,
)

logger = logging.getLogger(__name__)
router = APIRouter()


async def _parse_request(request: Request, *required_fields: str) -> Tuple[dict, Dict[str, Any]]:
    data = await request.json()
    role_arn = data.get("role_arn")
    external_id = data.get("external_id")

    if not role_arn:
        raise HTTPException(status_code=400, detail="role_arn is required")
    if not external_id:
        raise HTTPException(status_code=400, detail="external_id is required")
    for field in required_fields:
        if not data.get(field):
            raise HTTPException(status_code=400, detail=f"{field} is required")

    credentials = {"role_arn": role_arn, "external_id": external_id, "region": data.get("region", "us-east-1")}
    return credentials, data


@router.post("/list-buckets")
async def list_s3_buckets(request: Request):
    credentials, _ = await _parse_request(request)
    return await list_buckets(get_aws_client(credentials))


@router.post("/create-bucket")
async def create_s3_bucket(request: Request):
    credentials, data = await _parse_request(request, "bucket_name")
    return await create_bucket(get_aws_client(credentials), data["bucket_name"])


@router.post("/delete-bucket")
async def delete_s3_bucket(request: Request):
    credentials, data = await _parse_request(request, "bucket_name")
    return await delete_bucket(get_aws_client(credentials), data["bucket_name"], data.get("force", False))


@router.post("/list-bucket-contents")
async def list_s3_bucket_contents(request: Request):
    credentials, data = await _parse_request(request, "bucket_name")
    return await list_bucket_contents(get_aws_client(credentials), data["bucket_name"])


@router.post("/upload-file")
async def upload_file_to_s3(request: Request):
    credentials, data = await _parse_request(request, "bucket_name", "file_path")
    return await upload_file(get_aws_client(credentials), data["bucket_name"], data["file_path"], data.get("object_key"))


@router.post("/upload")
async def upload_file_direct(
    bucket_name: str = Form(...),
    object_key: str = Form(None),
    role_arn: str = Form(...),
    external_id: str = Form(...),
    region: str = Form("us-east-1"),
    file: UploadFile = File(...),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")

    credentials = {"role_arn": role_arn, "external_id": external_id, "region": region}
    s3_client = get_aws_client(credentials)
    key = object_key or file.filename

    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        result = await upload_file(s3_client, bucket_name, tmp_path, key)
        result["original_filename"] = file.filename
        return result
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


@router.post("/download-file")
async def download_file_from_s3(request: Request):
    credentials, data = await _parse_request(request, "bucket_name", "object_key")
    return await download_file(get_aws_client(credentials), data["bucket_name"], data["object_key"], data.get("file_path"))


@router.post("/delete-object")
async def delete_s3_object(request: Request):
    credentials, data = await _parse_request(request, "bucket_name", "object_key")
    return await delete_object(get_aws_client(credentials), data["bucket_name"], data["object_key"])


@router.post("/configure-bucket")
async def configure_s3_bucket(request: Request):
    credentials, data = await _parse_request(request, "bucket_name")
    return await configure_bucket(get_aws_client(credentials), data["bucket_name"], data.get("config", {}))
