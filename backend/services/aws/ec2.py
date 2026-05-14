import os
import logging
import boto3
import json
import re
import base64
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from botocore.exceptions import ClientError
from services.aws.client import get_aws_client as get_base_client

logger = logging.getLogger(__name__)


def get_aws_client(credentials: Optional[Dict[str, Any]] = None, default_region: str = None):
    return get_base_client('ec2', credentials, default_region)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_instance_name(ec2, instance_id: str) -> str:
    try:
        resp = ec2.describe_instances(InstanceIds=[instance_id])
        inst = resp['Reservations'][0]['Instances'][0]
        for tag in inst.get('Tags', []):
            if tag['Key'] == 'Name':
                return tag['Value']
    except Exception:
        pass
    return "Unknown"


def _instance_action(action_name: str, api_call, instance_id: str, ec2,
                     fallback_filter: str = None) -> Dict[str, Any]:
    """Shared logic for stop / start / terminate / reboot."""
    try:
        if not instance_id and fallback_filter:
            instances = ec2.describe_instances(
                Filters=[{'Name': 'instance-state-name', 'Values': [fallback_filter]}]
            )
            for res in instances.get('Reservations', []):
                for inst in res.get('Instances', []):
                    if inst['State']['Name'] == fallback_filter:
                        instance_id = inst['InstanceId']
                        break
                if instance_id:
                    break

        if not instance_id:
            return {"success": False, "message": f"No suitable EC2 instance found to {action_name}.",
                    "action": action_name}

        name = _get_instance_name(ec2, instance_id)
        api_call(InstanceIds=[instance_id])

        status_map = {'stop': 'stopping', 'start': 'starting',
                      'terminate': 'terminating', 'reboot': 'rebooting'}
        return {
            "success": True,
            "message": f"Successfully initiated {action_name} for EC2 instance {instance_id} ({name}).",
            "action": action_name,
            "instance_id": instance_id,
            "data": {"instance_id": instance_id, "instance_name": name,
                     "action": action_name, "status": status_map.get(action_name, action_name)},
        }
    except Exception as e:
        logger.error(f"Error {action_name}ing instance {instance_id}: {e}")
        return {"success": False, "message": f"Error {action_name}ing instance {instance_id}: {e}",
                "error": str(e), "action": action_name, "instance_id": instance_id}


# ── Core operations ───────────────────────────────────────────────────────────

async def create_instance(ec2, count: int = 1, instance_type='t2.micro', tags=None,
                          storage_config: Dict[str, Any] = None, user_data: str = None,
                          region: str = None) -> Dict[str, Any]:
    try:
        try:
            client_region = ec2._client_config.region_name if hasattr(ec2, '_client_config') else 'us-east-1'
        except AttributeError:
            client_region = 'us-east-1'
        actual_region = region or client_region

        if region and region != client_region:
            try:
                ec2 = boto3.client('ec2', region_name=region)
            except Exception:
                pass

        # Ensure valid instance_type
        if not isinstance(instance_type, str):
            instance_type = str(instance_type) if instance_type else 't2.micro'
        if not re.match(r'^[a-z][0-9][a-z]?\.[a-z0-9]+$', instance_type):
            instance_type = 't2.micro'

        # Networking: find or create VPC / subnet / SG / IGW
        vpc_id, subnet_id, security_group_id = await setup_networking(ec2)

        # Storage
        if storage_config is None:
            storage_config = {'size': 8, 'type': 'gp2'}
        ebs = {'VolumeSize': storage_config.get('size', 8),
               'VolumeType': storage_config.get('type', 'gp2'),
               'DeleteOnTermination': True}
        if storage_config.get('type') in ('io1', 'io2', 'gp3') and 'iops' in storage_config:
            ebs['Iops'] = storage_config['iops']
        if storage_config.get('type') == 'gp3':
            ebs.setdefault('Iops', 3000)
            ebs['Throughput'] = storage_config.get('throughput', 125)
        block_devices = [{'DeviceName': '/dev/sda1', 'Ebs': ebs}]

        # Tags
        ghosted_tags = [
            {'Key': 'AutoShutdown', 'Value': 'Disabled'},
            {'Key': 'KeepRunning', 'Value': 'True'},
            {'Key': 'CreatedBy', 'Value': 'GhostedCloudAIBot'},
        ]
        if isinstance(tags, str):
            try:
                tags = json.loads(tags) if tags.strip().startswith('{') else {"Name": tags}
            except json.JSONDecodeError:
                tags = {"Name": tags}
        if isinstance(tags, dict):
            existing = {t['Key'] for t in ghosted_tags}
            for k, v in tags.items():
                if k not in existing:
                    ghosted_tags.append({'Key': k, 'Value': str(v)})
                    existing.add(k)
        if 'Name' not in {t['Key'] for t in ghosted_tags}:
            ghosted_tags.append({'Key': 'Name', 'Value': 'Ghosted-Instance'})

        # AMI
        ami_id = 'ami-0261755bbcb8c4a84'
        if region and region != 'us-east-1':
            try:
                ssm = boto3.client('ssm', region_name=region)
                ami_id = ssm.get_parameter(
                    Name='/aws/service/ami-amazon-linux-latest/amzn2-ami-hvm-x86_64-gp2'
                )['Parameter']['Value']
            except Exception:
                pass

        # Build params
        instance_params = {
            'ImageId': ami_id,
            'InstanceType': instance_type,
            'MinCount': 1,
            'MaxCount': 1,
            'BlockDeviceMappings': block_devices,
            'DisableApiTermination': True,
            'Monitoring': {'Enabled': True},
            'TagSpecifications': [{'ResourceType': 'instance', 'Tags': ghosted_tags}],
        }
        if subnet_id:
            instance_params['NetworkInterfaces'] = [{
                'DeviceIndex': 0, 'SubnetId': subnet_id,
                'Groups': [security_group_id] if security_group_id else [],
                'AssociatePublicIpAddress': True,
            }]
        else:
            if security_group_id:
                instance_params['SecurityGroupIds'] = [security_group_id]

        if user_data:
            instance_params['UserData'] = base64.b64encode(user_data.encode()).decode()
        else:
            default_script = "#!/bin/bash\necho 'Instance started' > /tmp/startup.log\ntouch /tmp/instance-started\n"
            instance_params['UserData'] = base64.b64encode(default_script.encode()).decode()

        response = ec2.run_instances(**instance_params)
        if 'Instances' not in response or not response['Instances']:
            return {'success': False, 'message': 'No instances created.', 'region': actual_region}

        instance_ids = [i['InstanceId'] for i in response['Instances']]
        console_links = [
            f"https://{actual_region}.console.aws.amazon.com/ec2/home"
            f"?region={actual_region}#InstanceDetails:instanceId={iid}"
            for iid in instance_ids
        ]

        details = []
        for iid in instance_ids:
            details.append(await describe_instance(ec2, iid))

        return {
            "success": True,
            "message": f"Created {len(instance_ids)} {instance_type} instance(s) in {actual_region}.",
            "instance_ids": instance_ids,
            "details": details,
            "region": actual_region,
            "console_links": console_links,
        }
    except Exception as e:
        logger.error(f"Error creating EC2 instance: {e}")
        return {"success": False, "message": f"Error creating EC2 instance: {e}",
                "error": str(e), "region": region}


async def list_instances(ec2, filter_state: str = None) -> Dict[str, Any]:
    try:
        filters = [{'Name': 'instance-state-name', 'Values': [filter_state]}] if filter_state else []
        response = ec2.describe_instances(Filters=filters) if filters else ec2.describe_instances()

        instances = []
        for reservation in response.get('Reservations', []):
            for inst in reservation.get('Instances', []):
                tags = {t['Key']: t['Value'] for t in inst.get('Tags', [])} if inst.get('Tags') else {}
                instances.append({
                    "id": inst.get('InstanceId', 'unknown'),
                    "name": tags.get('Name', 'Unnamed'),
                    "state": inst.get('State', {}).get('Name', 'unknown'),
                    "type": inst.get('InstanceType', 'unknown'),
                    "public_ip": inst.get('PublicIpAddress', 'N/A'),
                    "private_ip": inst.get('PrivateIpAddress', 'N/A'),
                })

        label = f" {filter_state}" if filter_state else ""
        if not instances:
            return {"success": True, "message": f"No{label} EC2 instances found.", "details": []}

        return {"success": True, "message": f"Found {len(instances)}{label} EC2 instance(s).",
                "details": instances}
    except Exception as e:
        logger.error(f"Error listing EC2 instances: {e}")
        return {"success": False, "message": f"Error listing EC2 instances: {e}"}


async def stop_instance(ec2, instance_id: str = None) -> Dict[str, Any]:
    return _instance_action('stop', ec2.stop_instances, instance_id, ec2, fallback_filter='running')


async def start_instance(ec2, instance_id: str = None) -> Dict[str, Any]:
    return _instance_action('start', ec2.start_instances, instance_id, ec2, fallback_filter='stopped')


async def terminate_instance(ec2, instance_id: str = None) -> Dict[str, Any]:
    if not instance_id:
        instances = ec2.describe_instances()
        for res in instances.get('Reservations', []):
            for inst in res.get('Instances', []):
                if inst['State']['Name'] not in ('terminated', 'shutting-down'):
                    instance_id = inst['InstanceId']
                    break
            if instance_id:
                break
        if not instance_id:
            return {"success": False, "message": "No instances found to terminate.", "action": "terminate"}
    return _instance_action('terminate', ec2.terminate_instances, instance_id, ec2)


async def reboot_instance(ec2, instance_id: str = None) -> Dict[str, Any]:
    return _instance_action('reboot', ec2.reboot_instances, instance_id, ec2, fallback_filter='running')


async def describe_instance(ec2, instance_id: str = None) -> Dict[str, Any]:
    try:
        if not instance_id:
            instances = ec2.describe_instances()
            if not instances['Reservations']:
                return {"success": False, "message": "No EC2 instances found to describe"}
            instance_id = instances['Reservations'][0]['Instances'][0]['InstanceId']

        response = ec2.describe_instances(InstanceIds=[instance_id])
        if not response['Reservations']:
            return {"success": False, "message": f"Instance {instance_id} not found"}

        inst = response['Reservations'][0]['Instances'][0]
        details = {
            "Instance ID": inst['InstanceId'],
            "Instance Type": inst['InstanceType'],
            "State": inst['State']['Name'],
            "Launch Time": inst['LaunchTime'].strftime("%Y-%m-%d %H:%M:%S"),
            "Public IP": inst.get('PublicIpAddress', 'N/A'),
            "Private IP": inst.get('PrivateIpAddress', 'N/A'),
            "VPC ID": inst.get('VpcId', 'N/A'),
            "Subnet ID": inst.get('SubnetId', 'N/A'),
            "Key Name": inst.get('KeyName', 'N/A'),
            "Security Groups": [sg['GroupName'] for sg in inst.get('SecurityGroups', [])],
            "Tags": {t['Key']: t['Value'] for t in inst.get('Tags', [])},
        }
        return {"success": True, "message": f"Details for instance {instance_id}", "details": details}
    except Exception as e:
        logger.error(f"Error describing instance: {e}")
        return {"success": False, "message": f"Error describing instance {instance_id}: {e}"}


# ── Termination protection ────────────────────────────────────────────────────

async def check_termination_protection(ec2, instance_id: str) -> Dict[str, Any]:
    try:
        resp = ec2.describe_instance_attribute(InstanceId=instance_id, Attribute='disableApiTermination')
        return {"success": True, "is_protected": resp.get('DisableApiTermination', {}).get('Value', False),
                "instance_id": instance_id}
    except Exception as e:
        logger.error(f"Error checking termination protection: {e}")
        return {"success": False, "message": f"Error: {e}"}


async def disable_termination_protection(ec2, instance_id: str) -> Dict[str, Any]:
    try:
        ec2.modify_instance_attribute(InstanceId=instance_id, DisableApiTermination={'Value': False})
        return {"success": True, "message": f"Disabled termination protection for {instance_id}",
                "instance_id": instance_id}
    except Exception as e:
        logger.error(f"Error disabling termination protection: {e}")
        return {"success": False, "message": f"Error: {e}"}


# ── Convenience wrappers ──────────────────────────────────────────────────────

async def list_running_instances(ec2) -> Dict[str, Any]:
    return await list_instances(ec2, filter_state='running')


async def list_all_instances(ec2) -> Dict[str, Any]:
    return await list_instances(ec2)


async def terminate_all_instances(ec2) -> Dict[str, Any]:
    try:
        response = ec2.describe_instances()
        ids = [inst['InstanceId']
               for res in response['Reservations']
               for inst in res['Instances']
               if inst['State']['Name'] not in ('terminated', 'shutting-down')]
        if not ids:
            return {"success": True, "message": "No instances to terminate."}
        ec2.terminate_instances(InstanceIds=ids)
        return {"success": True, "message": f"Initiated termination of {len(ids)} instance(s)."}
    except Exception as e:
        logger.error(f"Error terminating all instances: {e}")
        return {"success": False, "message": f"Error: {e}"}


# ── Bulk / multi-instance operations ─────────────────────────────────────────

async def deploy_multiple_instances(ec2, count: int = 1) -> Dict[str, Any]:
    try:
        if count < 1 or count > 20:
            return {"success": False, "message": "Count must be between 1 and 20."}
        vpc_id, subnet_id, security_group_id = await setup_networking(ec2)
        response = ec2.run_instances(
            ImageId='ami-0e731c8a588258d0d',
            InstanceType='t2.micro', MinCount=count, MaxCount=count,
            NetworkInterfaces=[{'SubnetId': subnet_id, 'DeviceIndex': 0,
                                'AssociatePublicIpAddress': True, 'Groups': [security_group_id]}],
            TagSpecifications=[{'ResourceType': 'instance',
                                'Tags': [{'Key': 'Name', 'Value': 'Ghosted-Instance'}]}],
        )
        ids = [i['InstanceId'] for i in response['Instances']]
        waiter = ec2.get_waiter('instance_running')
        waiter.wait(InstanceIds=ids)
        return {"success": True, "message": f"Deployed {count} instance(s): {', '.join(ids)}"}
    except Exception as e:
        logger.error(f"Error deploying multiple instances: {e}")
        return {"success": False, "message": f"Error: {e}"}


async def stop_multiple_instances(ec2, instance_ids: List[str]) -> Dict[str, Any]:
    try:
        if not instance_ids:
            return {"success": False, "message": "No instance IDs provided."}
        resp = ec2.describe_instances(InstanceIds=instance_ids)
        running = [inst['InstanceId']
                   for res in resp['Reservations']
                   for inst in res['Instances']
                   if inst['State']['Name'] == 'running']
        if not running:
            return {"success": False, "message": "No running instances found."}
        ec2.stop_instances(InstanceIds=running)
        return {"success": True, "message": f"Stopping {len(running)} instance(s)."}
    except Exception as e:
        logger.error(f"Error stopping multiple instances: {e}")
        return {"success": False, "message": f"Error: {e}"}


async def modify_instance(ec2, instance_id: str, changes: Dict[str, Any]) -> Dict[str, Any]:
    try:
        resp = ec2.describe_instances(InstanceIds=[instance_id])
        if not resp['Reservations']:
            return {"success": False, "message": f"Instance {instance_id} not found."}
        state = resp['Reservations'][0]['Instances'][0]['State']['Name']

        if state == 'running' and ('instance_type' in changes or 'security_groups' in changes):
            ec2.stop_instances(InstanceIds=[instance_id])
            ec2.get_waiter('instance_stopped').wait(InstanceIds=[instance_id])

        if 'instance_type' in changes:
            ec2.modify_instance_attribute(InstanceId=instance_id,
                                          InstanceType={'Value': changes['instance_type']})
        if 'security_groups' in changes:
            ec2.modify_instance_attribute(InstanceId=instance_id, Groups=changes['security_groups'])
        if 'tags' in changes:
            ec2.create_tags(Resources=[instance_id],
                            Tags=[{'Key': k, 'Value': v} for k, v in changes['tags'].items()])

        if state == 'running':
            ec2.start_instances(InstanceIds=[instance_id])
            ec2.get_waiter('instance_running').wait(InstanceIds=[instance_id])

        return {"success": True, "message": f"Modified instance {instance_id}."}
    except Exception as e:
        logger.error(f"Error modifying instance: {e}")
        return {"success": False, "message": f"Error: {e}"}


async def get_instance_metrics(ec2, instance_id: str) -> Dict[str, Any]:
    try:
        cw = boto3.client('cloudwatch')
        now = datetime.utcnow()
        dims = [{'Name': 'InstanceId', 'Value': instance_id}]
        cpu = cw.get_metric_statistics(
            Namespace='AWS/EC2', MetricName='CPUUtilization', Dimensions=dims,
            StartTime=now - timedelta(hours=1), EndTime=now, Period=300, Statistics=['Average'])
        net = cw.get_metric_statistics(
            Namespace='AWS/EC2', MetricName='NetworkIn', Dimensions=dims,
            StartTime=now - timedelta(hours=1), EndTime=now, Period=300, Statistics=['Sum'])
        metrics = {
            "cpu_utilization": cpu['Datapoints'][-1]['Average'] if cpu['Datapoints'] else 0,
            "network_in": net['Datapoints'][-1]['Sum'] if net['Datapoints'] else 0,
        }
        return {"success": True, "message": f"Metrics for {instance_id}", "metrics": metrics}
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        return {"success": False, "message": f"Error: {e}"}


# ── Networking setup ──────────────────────────────────────────────────────────

async def setup_networking(ec2) -> tuple:
    vpc_id = subnet_id = security_group_id = None
    try:
        vpcs = ec2.describe_vpcs()
        for vpc in vpcs['Vpcs']:
            vpc_id = vpc['VpcId']
            break

        if not vpc_id:
            vpc = ec2.create_vpc(CidrBlock='10.0.0.0/16')
            vpc_id = vpc['Vpc']['VpcId']
            ec2.get_waiter('vpc_available').wait(VpcIds=[vpc_id])
            ec2.modify_vpc_attribute(VpcId=vpc_id, EnableDnsHostnames={'Value': True})

        subnets = ec2.describe_subnets(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])
        if subnets['Subnets']:
            subnet_id = subnets['Subnets'][0]['SubnetId']
        else:
            sub = ec2.create_subnet(VpcId=vpc_id, CidrBlock='10.0.1.0/24')
            subnet_id = sub['Subnet']['SubnetId']
            ec2.get_waiter('subnet_available').wait(SubnetIds=[subnet_id])

        try:
            sgs = ec2.describe_security_groups(
                Filters=[{'Name': 'group-name', 'Values': ['CloudAIBot-SG']},
                         {'Name': 'vpc-id', 'Values': [vpc_id]}])
            if sgs['SecurityGroups']:
                security_group_id = sgs['SecurityGroups'][0]['GroupId']
            else:
                sg = ec2.create_security_group(
                    GroupName='CloudAIBot-SG',
                    Description='Security group for Ghosted EC2 instances', VpcId=vpc_id)
                security_group_id = sg['GroupId']
                ec2.authorize_security_group_ingress(
                    GroupId=security_group_id,
                    IpPermissions=[{'IpProtocol': 'tcp', 'FromPort': 22, 'ToPort': 22,
                                    'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}])
        except Exception as e:
            logger.error(f"Error with security group: {e}")

        igws = ec2.describe_internet_gateways(
            Filters=[{'Name': 'attachment.vpc-id', 'Values': [vpc_id]}])
        if igws['InternetGateways']:
            igw_id = igws['InternetGateways'][0]['InternetGatewayId']
        else:
            igw = ec2.create_internet_gateway()
            igw_id = igw['InternetGateway']['InternetGatewayId']
            ec2.attach_internet_gateway(InternetGatewayId=igw_id, VpcId=vpc_id)

        rts = ec2.describe_route_tables(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])
        try:
            ec2.create_route(RouteTableId=rts['RouteTables'][0]['RouteTableId'],
                             DestinationCidrBlock='0.0.0.0/0', GatewayId=igw_id)
        except Exception:
            pass

        return vpc_id, subnet_id, security_group_id
    except Exception as e:
        logger.error(f"Error setting up networking: {e}")
        return vpc_id, subnet_id, security_group_id
