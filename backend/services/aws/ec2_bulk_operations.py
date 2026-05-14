"""Bulk EC2 operations — stop/start/terminate/reboot all instances."""

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


def _collect_instances(ec2, state_filter: List[str]) -> tuple:
    response = ec2.describe_instances(Filters=[{'Name': 'instance-state-name', 'Values': state_filter}])
    ids, details = [], []
    for res in response.get('Reservations', []):
        for inst in res.get('Instances', []):
            iid = inst['InstanceId']
            name = next((t['Value'] for t in inst.get('Tags', []) if t['Key'] == 'Name'), 'Unknown')
            ids.append(iid)
            details.append({
                'id': iid, 'name': name,
                'type': inst.get('InstanceType', 'Unknown'),
                'state': inst.get('State', {}).get('Name', 'Unknown'),
            })
    return ids, details


def _format_result(action_word: str, ids: list, details: list, extra_key: str) -> Dict[str, Any]:
    if not ids:
        return {"success": True, "message": f"No instances found to {action_word}."}

    lines = [f"Successfully initiated {action_word} for {len(ids)} EC2 instance(s):\n"]
    for d in details:
        lines.append(f"  {d['id']} ({d['name']}): {d['type']}")
    return {
        "success": True,
        "message": "\n".join(lines),
        extra_key: ids,
        "instance_details": details,
    }


async def stop_all_instances(ec2) -> Dict[str, Any]:
    ids, details = _collect_instances(ec2, ['running'])
    if ids:
        ec2.stop_instances(InstanceIds=ids)
    return _format_result("stop", ids, details, "stopped_instances")


async def start_all_instances(ec2) -> Dict[str, Any]:
    ids, details = _collect_instances(ec2, ['stopped'])
    if ids:
        ec2.start_instances(InstanceIds=ids)
    return _format_result("start", ids, details, "started_instances")


async def terminate_all_instances(ec2) -> Dict[str, Any]:
    ids, details = _collect_instances(ec2, ['pending', 'running', 'stopping', 'stopped'])
    for iid in ids:
        try:
            resp = ec2.describe_instance_attribute(InstanceId=iid, Attribute='disableApiTermination')
            if resp.get('DisableApiTermination', {}).get('Value', False):
                ec2.modify_instance_attribute(InstanceId=iid, DisableApiTermination={'Value': False})
        except Exception:
            pass
    if ids:
        ec2.terminate_instances(InstanceIds=ids)
    return _format_result("terminate", ids, details, "terminated_instances")


async def reboot_all_instances(ec2) -> Dict[str, Any]:
    ids, details = _collect_instances(ec2, ['running'])
    if ids:
        ec2.reboot_instances(InstanceIds=ids)
    return _format_result("reboot", ids, details, "rebooted_instances")


async def list_instances_with_actions(ec2) -> Dict[str, Any]:
    response = ec2.describe_instances()
    instances = []
    counts = {'running': 0, 'stopped': 0, 'other': 0}

    for res in response.get('Reservations', []):
        for inst in res.get('Instances', []):
            state = inst.get('State', {}).get('Name', 'Unknown')
            name = next((t['Value'] for t in inst.get('Tags', []) if t['Key'] == 'Name'), 'Unknown')
            if state == 'running':
                counts['running'] += 1
            elif state == 'stopped':
                counts['stopped'] += 1
            else:
                counts['other'] += 1
            instances.append({
                'id': inst['InstanceId'], 'name': name,
                'type': inst.get('InstanceType', 'Unknown'), 'state': state,
                'public_ip': inst.get('PublicIpAddress', 'N/A'),
                'private_ip': inst.get('PrivateIpAddress', 'N/A'),
                'launch_time': inst.get('LaunchTime', 'Unknown'),
            })

    if not instances:
        return {"success": True, "message": "You don't have any EC2 instances."}

    mapping = {
        'by_number': {str(i + 1): inst['id'] for i, inst in enumerate(instances)},
        'by_name': {inst['name'].lower(): inst['id'] for inst in instances if inst['name'] != 'Unknown'},
        'by_id': {inst['id']: inst['id'] for inst in instances},
    }
    for i, inst in enumerate(instances):
        inst['number'] = i + 1

    counts['total'] = len(instances)
    return {
        "success": True,
        "message": f"Found {len(instances)} EC2 instance(s).",
        "instances": instances,
        "instance_mapping": mapping,
        "counts": counts,
    }
