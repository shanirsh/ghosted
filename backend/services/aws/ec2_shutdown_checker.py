"""Analyze why an EC2 instance was shut down or terminated."""

import logging
import datetime
from typing import Dict, Any

import boto3

logger = logging.getLogger(__name__)

REASON_EXPLANATIONS = {
    "User initiated": "This instance was manually stopped by a user.",
    "Server.InternalError": "Stopped due to an internal AWS server error.",
    "Client.UserInitiated": "Stopped by a user or automated process with user credentials.",
    "Server.SpotInstanceTermination": "Spot instance terminated due to capacity or price constraints.",
    "Client.InstanceInitiatedShutdown": "The instance initiated its own shutdown (e.g., OS shutdown command).",
    "Client.VolumeLimitExceeded": "Terminated because the account exceeded the EBS volume limit.",
    "Client.InternalError": "Terminated due to an internal client error.",
}


def _get_cloudtrail_events(ec2, instance_id: str) -> list:
    try:
        ct = boto3.client(
            'cloudtrail',
            aws_access_key_id=ec2._client_config.credentials.access_key,
            aws_secret_access_key=ec2._client_config.credentials.secret_key,
            aws_session_token=ec2._client_config.credentials.token,
            region_name=ec2._client_config.region_name,
        )
        end = datetime.datetime.now()
        events = ct.lookup_events(
            LookupAttributes=[{'AttributeKey': 'ResourceName', 'AttributeValue': instance_id}],
            StartTime=end - datetime.timedelta(days=7), EndTime=end,
        )
        return [
            {
                'event_name': e.get('EventName'),
                'event_time': e['EventTime'].strftime("%Y-%m-%d %H:%M:%S") if isinstance(e.get('EventTime'), datetime.datetime) else str(e.get('EventTime')),
                'username': e.get('Username', 'Unknown'),
                'source_ip': e.get('SourceIPAddress', 'Unknown'),
            }
            for e in events.get('Events', [])
            if 'StopInstances' in e.get('EventName', '') or 'TerminateInstances' in e.get('EventName', '')
        ]
    except Exception as e:
        logger.warning(f"Could not check CloudTrail: {e}")
        return []


def _get_asg_events(ec2, instance_id: str) -> list:
    try:
        asg = boto3.client(
            'autoscaling',
            aws_access_key_id=ec2._client_config.credentials.access_key,
            aws_secret_access_key=ec2._client_config.credentials.secret_key,
            aws_session_token=ec2._client_config.credentials.token,
            region_name=ec2._client_config.region_name,
        )
        resp = asg.describe_auto_scaling_instances(InstanceIds=[instance_id])
        if not resp.get('AutoScalingInstances'):
            return []

        asg_inst = resp['AutoScalingInstances'][0]
        asg_name = asg_inst.get('AutoScalingGroupName')
        result = [{'asg_name': asg_name, 'lifecycle_state': asg_inst.get('LifecycleState', 'Unknown')}]

        activities = asg.describe_scaling_activities(AutoScalingGroupName=asg_name)
        for a in activities.get('Activities', []):
            if instance_id in a.get('Description', ''):
                result.append({
                    'description': a.get('Description'), 'cause': a.get('Cause'),
                    'status_code': a.get('StatusCode'),
                    'start_time': a['StartTime'].strftime("%Y-%m-%d %H:%M:%S") if isinstance(a.get('StartTime'), datetime.datetime) else str(a.get('StartTime')),
                })
        return result
    except Exception as e:
        logger.warning(f"Could not check Auto Scaling: {e}")
        return []


async def check_instance_shutdown_reason(ec2, instance_id: str) -> Dict[str, Any]:
    try:
        response = ec2.describe_instances(InstanceIds=[instance_id])
        if not response['Reservations'] or not response['Reservations'][0]['Instances']:
            return {"success": False, "message": f"Instance {instance_id} not found."}

        instance = response['Reservations'][0]['Instances'][0]
        state = instance['State']['Name']
        state_reason = instance.get('StateTransitionReason', 'No reason provided')
        name = next((t['Value'] for t in instance.get('Tags', []) if t['Key'] == 'Name'), 'Unknown')

        cloudtrail_events = _get_cloudtrail_events(ec2, instance_id)
        asg_events = _get_asg_events(ec2, instance_id)

        lines = [f"Shutdown analysis for {instance_id} ({name}):", f"State: {state}", f"Reason: {state_reason}", ""]

        for prefix, explanation in REASON_EXPLANATIONS.items():
            if prefix in state_reason:
                lines.append(explanation)
                break
        else:
            if state == "stopped" and not state_reason:
                lines.append("No specific reason recorded. Possible causes: Auto-Scaling, scheduled actions, CloudWatch alarms, or Budget actions.")

        itype = instance.get('InstanceType', '')
        if itype.startswith(('t2.', 't3.')):
            lines.append(f"\nBurstable instance type ({itype}) — may throttle on CPU credit exhaustion.")

        if asg_events:
            lines.append("\nAuto Scaling group activity:")
            for e in asg_events:
                if 'asg_name' in e:
                    lines.append(f"  Group: {e['asg_name']} ({e['lifecycle_state']})")
                elif 'description' in e:
                    lines.append(f"  {e['description']} — {e['cause']} ({e['status_code']})")

        if cloudtrail_events:
            lines.append("\nCloudTrail events:")
            for e in cloudtrail_events:
                lines.append(f"  {e['event_name']} at {e['event_time']} by {e['username']}")

        return {
            "success": True, "message": "\n".join(lines),
            "state": state, "state_reason": state_reason,
            "events": cloudtrail_events, "asg_events": asg_events,
        }
    except Exception as e:
        logger.error(f"Error checking shutdown reason: {e}")
        return {"success": False, "message": f"Error checking shutdown for {instance_id}: {e}"}
