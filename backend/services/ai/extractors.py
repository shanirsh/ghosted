"""Parameter extraction utilities for natural-language AWS commands."""

import re
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def extract_instance_id(text: str, last_instance_id: str = None, instance_mapping: dict = None) -> Optional[str]:
    """Extract an EC2 instance ID from text via regex, numbered reference, or context."""
    match = re.search(r'\bi-[0-9a-f]{8,17}\b', text)
    if match:
        return match.group(0)

    match = re.search(r'i-[a-f0-9]{8,}', text)
    if match:
        return match.group(0)

    if instance_mapping:
        num = re.search(r'(?:instance|vm|server|ec2)[\s#]*(\d+)', text) or re.search(r'#(\d+)', text)
        if num and num.group(1) in instance_mapping.get('by_number', {}):
            return instance_mapping['by_number'][num.group(1)]

        text_lower = text.lower()
        for name, iid in instance_mapping.get('by_name', {}).items():
            if name in text_lower:
                return iid

    words = text.strip().split()
    if len(words) <= 2 and ('it' in text.lower() or text.strip().lower() in ['stop', 'terminate', 'start', 'reboot']):
        if last_instance_id:
            return last_instance_id

    context_refs = ['this', 'this instance', 'the instance', 'that instance', 'it']
    if any(ref in text.lower() for ref in context_refs) and last_instance_id:
        return last_instance_id

    return None


def extract_bucket_name(text: str, last_bucket_name: str = None) -> Optional[str]:
    """Extract an S3 bucket name from text."""
    match = re.search(r'\b(?:bucket|s3)[\s:]*["\']([-\w.]+)["\'\s]', text, re.IGNORECASE)
    if match:
        return match.group(1)

    match = re.search(r'\b(?:bucket|s3)[\s:]*([-\w.]+)\b', text, re.IGNORECASE)
    if match:
        name = match.group(1)
        skip = {'named', 'called', 'name', 'create', 'make', 'new', 'delete', 'remove', 'list'}
        if name.lower() not in skip:
            return name

    context_refs = ['this bucket', 'the bucket', 'that bucket', 'it']
    if any(ref in text.lower() for ref in context_refs) and last_bucket_name:
        return last_bucket_name

    return None


def extract_complex_ec2_params(text: str) -> Dict[str, Any]:
    """Extract EC2 creation parameters from natural language."""
    params: Dict[str, Any] = {}
    text_lower = text.lower()

    # Instance type
    m = re.search(r'\b(t2|t3|t3a|m5|c5|r5)\.(nano|micro|small|medium|large|xlarge|2xlarge|4xlarge|8xlarge)\b', text_lower)
    if m:
        params['instance_type'] = f"{m.group(1)}.{m.group(2)}"

    # Region
    m = re.search(r'\b(us|eu|ap|sa|ca|me|af)-(north|south|east|west|central)-\d\b', text_lower)
    if m:
        params['region'] = m.group(0)

    # Storage size
    m = re.search(r'(\d+)\s*(?:gb|gigabytes?)\s*(?:storage|disk|volume|io1|io2|gp2|gp3|st1|sc1)', text_lower)
    if not m:
        m = re.search(r'with\s+(\d+)\s*(?:gb|gigabytes?)', text_lower)
    if m:
        params['volume_size'] = int(m.group(1))

    # Volume type
    for vtype, patterns in {
        'gp3': ['gp3'], 'io1': ['io1', 'provisioned iops'], 'io2': ['io2'],
        'st1': ['st1', 'throughput optimized'], 'sc1': ['sc1', 'cold storage'],
    }.items():
        if any(p in text_lower for p in patterns):
            params['volume_type'] = vtype
            break

    # IOPS
    if params.get('volume_type') in ('io1', 'io2', 'gp3'):
        m = re.search(r'(\d+)\s*iops', text_lower)
        if m:
            params['iops'] = int(m.group(1))

    # Throughput
    if params.get('volume_type') == 'gp3':
        m = re.search(r'(\d+)\s*(?:mb/s|mbps|throughput)', text_lower)
        if m:
            params['throughput'] = int(m.group(1))

    # Name
    for pattern in [r"name\s+it\s+['\"](.*?)['\"]", r"name\s+['\"](.*?)['\"]",
                    r"named\s+['\"](.*?)['\"]", r"call\s+it\s+['\"](.*?)['\"]"]:
        m = re.search(pattern, text_lower)
        if m:
            params['name'] = m.group(1)
            break

    # Count
    m = re.search(r'(?:create|launch|start)\s+(\d+)\s+(?:ec2\s+)?instances?', text_lower)
    if m:
        params['count'] = int(m.group(1))

    # User data
    user_data = extract_user_data(text)
    if user_data:
        params['user_data'] = user_data

    return params


def extract_user_data(text: str) -> Optional[str]:
    """Extract bootstrap script hints from command text."""
    patterns = [
        r'with\s+bootstrap\s+script[:\s]+(.*?)(?:and|,|\.|$)',
        r'with\s+user\s+data[:\s]+(.*?)(?:and|,|\.|$)',
        r'install\s+(.*?)(?:on startup|when it starts|after launch)',
        r'run\s+script[:\s]+(.*?)(?:on startup|when it starts|after launch)',
        r'bootstrap[:\s]+(.*?)(?:and|,|\.|$)',
    ]
    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if m:
            hint = m.group(1).strip()
            if 'nginx' in hint.lower() or 'web server' in hint.lower():
                return "#!/bin/bash\napt-get update -y\napt-get install -y nginx\nsystemctl enable nginx\nsystemctl start nginx\n"
            if 'docker' in hint.lower() or 'container' in hint.lower():
                return "#!/bin/bash\napt-get update -y\napt-get install -y apt-transport-https ca-certificates curl software-properties-common\ncurl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add -\napt-get install -y docker-ce\nsystemctl enable docker\nsystemctl start docker\n"
            if 'install' in hint.lower():
                packages = [p for p in re.findall(r'\b([a-zA-Z0-9\-\.]+)\b', hint)
                            if p.lower() not in ('and', 'the', 'on', 'with', 'for', 'to', 'a', 'an')]
                if packages:
                    return "#!/bin/bash\napt-get update -y\n" + "".join(f"apt-get install -y {p}\n" for p in packages)
            return f"#!/bin/bash\napt-get update -y\n# {hint}\n"
    return None


# Action-to-endpoint mapping

EC2_ACTION_MAP = {
    'list': 'all-instances', 'list_instances': 'all-instances', 'list_all_instances': 'all-instances',
    'list_running_instances': 'running-instances', 'describe_instances': 'all-instances',
    'describe': 'describe-instance', 'describe_instance': 'describe-instance',
    'start': 'start-instance', 'start_instance': 'start-instance',
    'stop': 'stop-instance', 'stop_instance': 'stop-instance',
    'terminate': 'terminate-instance', 'terminate_instance': 'terminate-instance',
    'reboot': 'reboot-instance', 'reboot_instance': 'reboot-instance',
    'create': 'create-instance', 'create_instance': 'create-instance', 'launch': 'create-instance',
}

S3_ACTION_MAP = {
    'list_buckets': 'list-buckets', 'list': 'list-buckets',
    'create_bucket': 'create-bucket', 'create': 'create-bucket',
    'delete_bucket': 'delete-bucket', 'delete': 'delete-bucket',
    'list_contents': 'list-objects', 'list_objects': 'list-objects',
    'upload': 'upload-object', 'download': 'download-object', 'delete_object': 'delete-object',
}


def map_action_to_endpoint(service: str, action: str) -> Optional[str]:
    """Map an AI-extracted action to the corresponding direct endpoint name."""
    if not service or not action:
        return None
    service_lower, action_lower = service.lower(), action.lower()

    if service_lower == 'ec2':
        if any(t in action_lower for t in ['create', 'launch', 'new', 'provision', 'deploy']):
            return 'create-instance'
        if 'list' in action_lower and not any(t in action_lower for t in ['running', 'active']):
            return 'all-instances'
        if 'list' in action_lower and any(t in action_lower for t in ['running', 'active']):
            return 'running-instances'
        if 'stop' in action_lower:
            return 'stop-all-instances' if 'all' in action_lower else 'stop-instance'
        if 'terminate' in action_lower:
            return 'terminate-all-instances' if 'all' in action_lower else 'terminate-instance'
        if any(t in action_lower for t in ['describe', 'details', 'info', 'get']):
            return 'describe-instance'
        return EC2_ACTION_MAP.get(action_lower)

    if service_lower == 's3':
        if any(t in action_lower for t in ['list', 'show', 'get']) and 'bucket' in action_lower:
            return 'list-buckets'
        if any(t in action_lower for t in ['create', 'new', 'make']) and 'bucket' in action_lower:
            return 'create-bucket'
        if any(t in action_lower for t in ['delete', 'remove', 'destroy']) and 'bucket' in action_lower:
            return 'delete-bucket'
        return S3_ACTION_MAP.get(action_lower)

    return None
