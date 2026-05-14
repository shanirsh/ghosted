"""Unified interface for AWS operations, wrapping AWSExecutor."""

from typing import Dict, Any, Optional
from services.aws.executor import AWSExecutor


class AWSOperations:
    def __init__(self, credentials: Optional[Dict[str, Any]] = None):
        self.executor = AWSExecutor(credentials)
        self.credentials = credentials or {}

    async def execute(self, service: str, action: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        return await self.executor.execute_operation({
            'service': service, 'action': action, 'parameters': parameters or {},
        })

    async def list_ec2_instances(self) -> Dict[str, Any]:
        return await self.execute('ec2', 'describe_instances')

    async def create_ec2_instance(self, instance_type='t2.micro', count=1,
                                  tags=None, storage_config=None, user_data=None) -> Dict[str, Any]:
        params = {'instance_type': instance_type, 'count': count}
        if tags:
            params['tags'] = tags
        if storage_config:
            params['storage_config'] = storage_config
        if user_data:
            params['user_data'] = user_data
        return await self.execute('ec2', 'create', params)

    async def stop_ec2_instance(self, instance_id: str) -> Dict[str, Any]:
        return await self.execute('ec2', 'stop', {'instance_id': instance_id})

    async def start_ec2_instance(self, instance_id: str) -> Dict[str, Any]:
        return await self.execute('ec2', 'start', {'instance_id': instance_id})

    async def terminate_ec2_instance(self, instance_id: str) -> Dict[str, Any]:
        return await self.execute('ec2', 'terminate', {'instance_id': instance_id})

    async def describe_ec2_instance(self, instance_id: str) -> Dict[str, Any]:
        return await self.execute('ec2', 'describe', {'instance_id': instance_id})

    async def list_s3_buckets(self) -> Dict[str, Any]:
        return await self.execute('s3', 'list_buckets')

    async def create_s3_bucket(self, bucket_name: str) -> Dict[str, Any]:
        return await self.execute('s3', 'create', {'bucket_name': bucket_name})

    async def delete_s3_bucket(self, bucket_name: str, force: bool = False) -> Dict[str, Any]:
        return await self.execute('s3', 'delete', {'bucket_name': bucket_name, 'force': force})

    async def list_s3_bucket_contents(self, bucket_name: str) -> Dict[str, Any]:
        return await self.execute('s3', 'list_contents', {'bucket_name': bucket_name})
