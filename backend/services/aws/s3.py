"""S3 operations for Ghosted Cloud AI."""

import os
import asyncio
import logging
from typing import Dict, Any, Optional

from botocore.exceptions import ClientError
from services.aws.client import get_aws_client as get_base_client

logger = logging.getLogger(__name__)


def get_aws_client(credentials: Optional[Dict[str, Any]] = None, default_region: str = None):
    return get_base_client('s3', credentials, default_region)


async def create_bucket(s3, bucket_name: str, region: str = 'us-east-1') -> Dict[str, Any]:
    try:
        loop = asyncio.get_event_loop()
        if region == 'us-east-1':
            await loop.run_in_executor(None, lambda: s3.create_bucket(Bucket=bucket_name))
        else:
            await loop.run_in_executor(None, lambda: s3.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={'LocationConstraint': region},
            ))

        return {
            "success": True,
            "message": f"Successfully created S3 bucket: {bucket_name}",
            "bucket_name": bucket_name,
            "region": region,
            "console_link": f"https://s3.console.aws.amazon.com/s3/buckets/{bucket_name}?region={region}",
        }
    except ClientError as e:
        code = e.response['Error']['Code']
        if code == 'BucketAlreadyExists':
            return {"success": False, "message": f"Bucket name '{bucket_name}' is already taken."}
        if code == 'InvalidBucketName':
            return {"success": False, "message": f"Invalid bucket name '{bucket_name}'. Names must be 3-63 chars, lowercase letters/numbers/hyphens."}
        logger.error(f"Error creating bucket: {e}")
        return {"success": False, "message": f"Error creating bucket: {e}"}
    except Exception as e:
        logger.error(f"Error creating bucket: {e}")
        return {"success": False, "message": f"Error creating bucket: {e}"}


async def list_buckets(s3) -> Dict[str, Any]:
    try:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: s3.list_buckets())
        bucket_names = [b['Name'] for b in response.get('Buckets', [])]

        bucket_details = []
        for name in bucket_names:
            try:
                location = s3.get_bucket_location(Bucket=name)['LocationConstraint'] or 'us-east-1'
                try:
                    versioning = s3.get_bucket_versioning(Bucket=name).get('Status', 'Disabled')
                except Exception:
                    versioning = 'Disabled'
                bucket_details.append({
                    "name": name, "region": location, "versioning": versioning,
                    "console_link": f"https://s3.console.aws.amazon.com/s3/buckets/{name}?region={location}",
                })
            except Exception:
                bucket_details.append({"name": name})

        count = len(bucket_names)
        message = f"Found {count} S3 bucket{'s' if count != 1 else ''}." if count else "No S3 buckets found."

        return {
            "success": True,
            "message": message,
            "buckets": bucket_names,
            "bucket_details": bucket_details,
            "data": {"buckets": bucket_names, "bucket_details": bucket_details},
        }
    except Exception as e:
        logger.error(f"Error listing buckets: {e}")
        return {"success": False, "message": f"Error listing buckets: {e}"}


async def delete_bucket(s3, bucket_name: str, force: bool = False) -> Dict[str, Any]:
    try:
        loop = asyncio.get_event_loop()

        try:
            await loop.run_in_executor(None, lambda: s3.get_bucket_location(Bucket=bucket_name))
        except ClientError as e:
            code = e.response['Error']['Code']
            if code == 'AccessDenied':
                return {"success": False, "message": "You don't have permission to delete this bucket."}
            if code == 'NoSuchBucket':
                return {"success": False, "message": f"Bucket '{bucket_name}' does not exist."}
            raise

        if force:
            try:
                paginator = s3.get_paginator('list_objects_v2')
                for page in paginator.paginate(Bucket=bucket_name):
                    if 'Contents' in page:
                        objects = [{'Key': obj['Key']} for obj in page['Contents']]
                        await loop.run_in_executor(None, lambda objs=objects: s3.delete_objects(
                            Bucket=bucket_name, Delete={'Objects': objs}))

                paginator = s3.get_paginator('list_object_versions')
                for page in paginator.paginate(Bucket=bucket_name):
                    versions = []
                    for key in ('Versions', 'DeleteMarkers'):
                        versions += [{'Key': v['Key'], 'VersionId': v['VersionId']} for v in page.get(key, [])]
                    if versions:
                        await loop.run_in_executor(None, lambda vers=versions: s3.delete_objects(
                            Bucket=bucket_name, Delete={'Objects': vers}))
            except ClientError as e:
                if e.response['Error']['Code'] == 'AccessDenied':
                    return {"success": False, "message": "Access Denied. Ensure you have s3:DeleteObject permission."}
                if e.response['Error']['Code'] != 'NoSuchBucket':
                    raise

        await loop.run_in_executor(None, lambda: s3.delete_bucket(Bucket=bucket_name))

        return {
            "success": True,
            "message": f"Successfully deleted S3 bucket '{bucket_name}'.",
            "bucket_name": bucket_name,
            "data": {"bucket_name": bucket_name, "action": "deleted"},
        }
    except ClientError as e:
        code = e.response['Error']['Code']
        if code == 'NoSuchBucket':
            return {"success": False, "message": f"Bucket '{bucket_name}' does not exist."}
        if code == 'BucketNotEmpty':
            return {"success": False, "message": f"Bucket '{bucket_name}' is not empty. Use force delete to remove contents first."}
        if code == 'AccessDenied':
            return {"success": False, "message": "Access Denied. Ensure you have the required S3 permissions."}
        logger.error(f"Error deleting bucket: {e}")
        return {"success": False, "message": f"Error deleting bucket: {e}"}
    except Exception as e:
        logger.error(f"Error deleting bucket: {e}")
        return {"success": False, "message": f"Error deleting bucket: {e}"}


async def list_bucket_contents(s3, bucket_name: str) -> Dict[str, Any]:
    try:
        paginator = s3.get_paginator('list_objects_v2')
        objects = []
        total_size = 0

        for page in paginator.paginate(Bucket=bucket_name):
            for obj in page.get('Contents', []):
                objects.append({
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'].strftime("%Y-%m-%d %H:%M:%S"),
                })
                total_size += obj['Size']

        if not objects:
            return {"success": True, "message": f"Bucket '{bucket_name}' is empty."}

        return {
            "success": True,
            "message": f"Found {len(objects)} object(s) in '{bucket_name}' ({format_size(total_size)} total).",
            "objects": objects,
        }
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchBucket':
            return {"success": False, "message": f"Bucket '{bucket_name}' does not exist."}
        logger.error(f"Error listing bucket contents: {e}")
        return {"success": False, "message": f"Error listing bucket contents: {e}"}
    except Exception as e:
        logger.error(f"Error listing bucket contents: {e}")
        return {"success": False, "message": f"Error listing bucket contents: {e}"}


def format_size(size_bytes: int) -> str:
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f} PB"


async def upload_file(s3, bucket_name: str, file_path: str, object_key: str = None) -> Dict[str, Any]:
    try:
        if not object_key:
            object_key = os.path.basename(file_path)
        if not os.path.exists(file_path):
            return {"success": False, "message": f"File '{file_path}' does not exist."}

        try:
            s3.head_bucket(Bucket=bucket_name)
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return {"success": False, "message": f"Bucket '{bucket_name}' does not exist."}
            raise

        file_size = os.path.getsize(file_path)
        with open(file_path, 'rb') as f:
            s3.upload_fileobj(f, bucket_name, object_key)

        url = s3.generate_presigned_url('get_object', Params={'Bucket': bucket_name, 'Key': object_key}, ExpiresIn=3600)
        return {
            "success": True,
            "message": f"Uploaded '{file_path}' to '{bucket_name}/{object_key}' ({format_size(file_size)}).",
            "url": url, "bucket": bucket_name, "key": object_key, "size": file_size,
        }
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        return {"success": False, "message": f"Error uploading file: {e}"}


async def download_file(s3, bucket_name: str, object_key: str, file_path: str = None) -> Dict[str, Any]:
    try:
        if not file_path:
            file_path = os.path.basename(object_key)

        try:
            s3.head_bucket(Bucket=bucket_name)
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return {"success": False, "message": f"Bucket '{bucket_name}' does not exist."}
            raise

        try:
            resp = s3.head_object(Bucket=bucket_name, Key=object_key)
            size = resp['ContentLength']
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return {"success": False, "message": f"Object '{object_key}' does not exist in bucket '{bucket_name}'."}
            raise

        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        s3.download_file(bucket_name, object_key, file_path)

        return {
            "success": True,
            "message": f"Downloaded '{bucket_name}/{object_key}' to '{file_path}' ({format_size(size)}).",
            "file_path": file_path, "size": size,
        }
    except Exception as e:
        logger.error(f"Error downloading file: {e}")
        return {"success": False, "message": f"Error downloading file: {e}"}


async def delete_object(s3, bucket_name: str, object_key: str) -> Dict[str, Any]:
    try:
        try:
            s3.head_bucket(Bucket=bucket_name)
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return {"success": False, "message": f"Bucket '{bucket_name}' does not exist."}
            raise

        try:
            s3.head_object(Bucket=bucket_name, Key=object_key)
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return {"success": False, "message": f"Object '{object_key}' does not exist in bucket '{bucket_name}'."}
            raise

        s3.delete_object(Bucket=bucket_name, Key=object_key)
        return {"success": True, "message": f"Deleted '{object_key}' from bucket '{bucket_name}'."}
    except Exception as e:
        logger.error(f"Error deleting object: {e}")
        return {"success": False, "message": f"Error deleting object: {e}"}


async def configure_bucket(s3, bucket_name: str, config: Dict[str, Any]) -> Dict[str, Any]:
    try:
        try:
            s3.head_bucket(Bucket=bucket_name)
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return {"success": False, "message": f"Bucket '{bucket_name}' does not exist."}
            raise

        changes = []

        if 'versioning' in config:
            status = 'Enabled' if config['versioning'] else 'Suspended'
            s3.put_bucket_versioning(Bucket=bucket_name, VersioningConfiguration={'Status': status})
            changes.append(f"Versioning: {status}")

        if 'public_access' in config:
            if config['public_access']:
                s3.delete_public_access_block(Bucket=bucket_name)
                changes.append("Public Access: Allowed")
            else:
                s3.put_public_access_block(Bucket=bucket_name, PublicAccessBlockConfiguration={
                    'BlockPublicAcls': True, 'IgnorePublicAcls': True,
                    'BlockPublicPolicy': True, 'RestrictPublicBuckets': True,
                })
                changes.append("Public Access: Blocked")

        if 'encryption' in config:
            if config['encryption']:
                s3.put_bucket_encryption(Bucket=bucket_name, ServerSideEncryptionConfiguration={
                    'Rules': [{'ApplyServerSideEncryptionByDefault': {'SSEAlgorithm': 'AES256'}, 'BucketKeyEnabled': True}],
                })
                changes.append("Encryption: Enabled (AES256)")
            else:
                try:
                    s3.delete_bucket_encryption(Bucket=bucket_name)
                    changes.append("Encryption: Disabled")
                except ClientError as e:
                    if e.response['Error']['Code'] == 'ServerSideEncryptionConfigurationNotFoundError':
                        changes.append("Encryption: Already Disabled")
                    else:
                        raise

        if not changes:
            return {"success": True, "message": f"No configuration changes specified for '{bucket_name}'."}

        return {"success": True, "message": f"Configuration for '{bucket_name}':\n" + "\n".join(f"  - {c}" for c in changes)}
    except Exception as e:
        logger.error(f"Error configuring bucket: {e}")
        return {"success": False, "message": f"Error configuring bucket: {e}"}
