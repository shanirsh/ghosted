"""Centralized AWS operation executor with routing and error handling."""

import logging
import traceback
from typing import Dict, Any, Optional

from services.aws.ec2 import get_aws_client as get_ec2_client
from services.aws.s3 import get_aws_client as get_s3_client
from services.aws.ec2 import (
    list_instances, create_instance, stop_instance,
    start_instance, terminate_instance, describe_instance,
    list_running_instances, reboot_instance,
)
from services.aws.ec2_shutdown_checker import check_instance_shutdown_reason
from services.aws.ec2_bulk_operations import (
    stop_all_instances, terminate_all_instances, reboot_all_instances,
    list_instances_with_actions, start_all_instances,
)
from services.aws.s3 import (
    list_buckets, create_bucket, delete_bucket, list_bucket_contents,
    upload_file, download_file, delete_object, configure_bucket,
)

logger = logging.getLogger(__name__)


class AWSExecutor:
    def __init__(self, credentials: Optional[Dict[str, Any]] = None):
        self.credentials = credentials or {}
        self.region = self.credentials.get('region', 'us-east-1')

    async def execute_operation(self, params: Dict[str, Any]) -> Dict[str, Any]:
        service = params.get('service')
        action = params.get('action')
        parameters = params.get('parameters', {})

        try:
            parameters.setdefault('region', self.region)
            if self.credentials:
                for k, v in self.credentials.items():
                    if k not in parameters and v is not None:
                        parameters[k] = v

            if service == 'ec2':
                return await self._execute_ec2(action, parameters)
            if service == 's3':
                return await self._execute_s3(action, parameters)
            return {'success': False, 'message': f"Unsupported service: {service}"}
        except Exception as e:
            logger.error(f"Error in {service}.{action}: {e}\n{traceback.format_exc()}")
            return {'success': False, 'message': f"Error: {e}", 'error': str(e)}

    async def _execute_ec2(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        ec2 = get_ec2_client(params)

        EC2_DISPATCH = {
            'describe_instances': lambda: list_instances(ec2),
            'list': lambda: list_instances(ec2, filter_state=params.get('filter_state')),
            'list_all_instances': lambda: list_instances(ec2),
            'list_running_instances': lambda: list_running_instances(ec2),
            'list_with_actions': lambda: list_instances_with_actions(ec2),
            'stop': lambda: stop_instance(ec2, params.get('instance_id')),
            'stop_all': lambda: stop_all_instances(ec2),
            'start': lambda: start_instance(ec2, params.get('instance_id')),
            'start_all': lambda: start_all_instances(ec2),
            'reboot': lambda: reboot_instance(ec2, params.get('instance_id')),
            'reboot_all': lambda: reboot_all_instances(ec2),
            'terminate': lambda: terminate_instance(ec2, params.get('instance_id')),
            'terminate_all': lambda: terminate_all_instances(ec2),
            'describe': lambda: describe_instance(ec2, params.get('instance_id')),
            'check_shutdown_reason': lambda: check_instance_shutdown_reason(ec2, params.get('instance_id')),
        }

        if action == 'create':
            valid_keys = {'count', 'instance_type', 'tags', 'region', 'storage_config', 'user_data'}
            return await create_instance(ec2, **{k: v for k, v in params.items() if k in valid_keys})

        handler = EC2_DISPATCH.get(action)
        if handler:
            return await handler()
        return {'success': False, 'message': f"Unsupported EC2 operation: {action}"}

    async def _execute_s3(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        s3 = get_s3_client(params)

        S3_DISPATCH = {
            'list_buckets': lambda: list_buckets(s3),
            'create': lambda: create_bucket(s3, params.get('bucket_name')),
            'delete': lambda: delete_bucket(s3, params.get('bucket_name'), params.get('force', False)),
            'list_contents': lambda: list_bucket_contents(s3, params.get('bucket_name')),
            'upload': lambda: upload_file(s3, params.get('bucket_name'), params.get('file_path'), params.get('object_key')),
            'download': lambda: download_file(s3, params.get('bucket_name'), params.get('object_key'), params.get('file_path')),
            'delete_object': lambda: delete_object(s3, params.get('bucket_name'), params.get('object_key')),
            'configure': lambda: configure_bucket(s3, params.get('bucket_name'), params.get('config', {})),
        }

        handler = S3_DISPATCH.get(action)
        if handler:
            return await handler()
        return {'success': False, 'message': f"Unsupported S3 operation: {action}"}
