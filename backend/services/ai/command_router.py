"""Pattern-based command routing — matches user text to AWS operations."""

import re
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# ── EC2 patterns ──────────────────────────────────────────────────────────────

LIST_INSTANCES_RE = re.compile(
    r'\b(list|show|get|display)\b.*\b(all\s+my|my\s+all|all|my)?\s*\b(instances?|servers?|vms?|ec2s?)\b',
    re.IGNORECASE,
)
LIST_RUNNING_RE = re.compile(
    r'\b(list|show|get|display)\b.*\b(running|active)\b.*\b(instances?|servers?|vms?|ec2s?)\b',
    re.IGNORECASE,
)
STOP_ALL_RE = re.compile(
    r'\b(stop|halt|shutdown|turn\s+off)\b.*\ball\b.*\b(instances?|servers?|vms?|ec2s?|everything)\b',
    re.IGNORECASE,
)
TERMINATE_ALL_RE = re.compile(
    r'\b(terminate|delete|remove|destroy|kill)\b.*\ball\b.*\b(instances?|servers?|vms?|ec2s?|everything)\b',
    re.IGNORECASE,
)
STOP_INSTANCE_RE = re.compile(
    r'\b(stop|halt|shutdown|turn\s+off|pause|suspend)\b.*\b(instance|server|vm|ec2|it)\b',
    re.IGNORECASE,
)
START_INSTANCE_RE = re.compile(
    r'\b(start|power\s+on|boot|turn\s+on)\b.*\b(instance|server|vm|ec2|it)\b',
    re.IGNORECASE,
)
TERMINATE_INSTANCE_RE = re.compile(
    r'\b(terminate|delete|remove|destroy|kill)\b.*\b(instance|server|vm|ec2|it)\b',
    re.IGNORECASE,
)
REBOOT_INSTANCE_RE = re.compile(
    r'\b(reboot|restart|cycle|power\s+cycle)\b.*\b(instance|server|vm|ec2|it)\b',
    re.IGNORECASE,
)
DESCRIBE_INSTANCE_RE = re.compile(
    r'\b(describe|details?|info)\b.*\b(instance|server|vm|ec2)\b',
    re.IGNORECASE,
)
CREATE_INSTANCE_RE = re.compile(
    r'\b(create|deploy|launch|provision|spin\s+up)\b.*\b(instance|vm|server|ec2)\b',
    re.IGNORECASE,
)
INSTANCE_TYPE_RE = re.compile(
    r'\b(t2|t3|t3a|m5|c5|r5)\.'
    r'(nano|micro|small|medium|large|xlarge|2xlarge|4xlarge|8xlarge|12xlarge|16xlarge|24xlarge)\b',
    re.IGNORECASE,
)

# ── S3 patterns ───────────────────────────────────────────────────────────────

LIST_BUCKETS_RE = re.compile(
    r'\b(list|show|get|display)\b.*\b(s3|buckets?|storage)\b',
    re.IGNORECASE,
)
CREATE_BUCKET_RE = re.compile(
    r'\b(create|make|new|add|set\s+up|establish)\b.*\bbuckets?\b',
    re.IGNORECASE,
)
DELETE_BUCKET_RE = re.compile(
    r'\b(delete|remove|destroy|drop|erase|get\s+rid\s+of)\b.*\bbuckets?\b',
    re.IGNORECASE,
)
BUCKET_CONTENTS_RE = re.compile(
    r'\b(list|show|get)\b.*\b(contents?|files?|objects?)\b.*?\b(?:of|in|from)\b.*?\b(?:bucket|s3)?\s*["\']?([\w.-]+)["\']?',
    re.IGNORECASE,
)
UPLOAD_RE = re.compile(
    r'\b(upload|put)\b.*?["\']?([\w./-]+\.[\w]+)["\']?.*?\b(?:to|in|into)\b.*?\b(?:bucket|s3)?\s*["\']?([\w.-]+)["\']?',
    re.IGNORECASE,
)
DOWNLOAD_RE = re.compile(
    r'\b(download|get)\b.*?["\']?([\w./-]+)["\']?.*?\b(?:from|in)\b.*?\b(?:bucket|s3)?\s*["\']?([\w.-]+)["\']?',
    re.IGNORECASE,
)
DELETE_OBJECT_RE = re.compile(
    r'\b(delete|remove)\b.*?["\']?([\w./-]+)["\']?.*?\b(?:from|in)\b.*?\b(?:bucket|s3)?\s*["\']?([\w.-]+)["\']?',
    re.IGNORECASE,
)

# ── Greeting / meta ──────────────────────────────────────────────────────────

GREETING_WORDS = frozenset(['hi', 'hello', 'hey', 'greetings'])
CAPABILITIES_RE = re.compile(
    r'\b(what can you do|capabilities|features|help)\b', re.IGNORECASE,
)

# ── Bucket name extraction ────────────────────────────────────────────────────

BUCKET_NAME_RE = re.compile(r'(?:bucket|s3)[\s:]+([\w.-]+)', re.IGNORECASE)
BUCKET_NAME_QUOTED_RE = re.compile(r'["\']([\\w.-]+)["\']')


_BUCKET_SKIP = frozenset({
    'named', 'called', 'name', 'create', 'make', 'new', 'delete', 'remove',
    'list', 'show', 'get', 'bucket', 'buckets', 'an', 'a', 'the', 'my',
    'for', 'in', 'to', 'from', 'with', 'set', 'up', 'please',
})


def extract_bucket_name_from_command(text: str) -> Optional[str]:
    m = BUCKET_NAME_QUOTED_RE.search(text)
    if m:
        return m.group(1)
    m = BUCKET_NAME_RE.search(text)
    if m and m.group(1).lower() not in _BUCKET_SKIP:
        return m.group(1)
    return None


def route_command(command: str) -> Tuple[Optional[str], Optional[str], dict]:
    """Classify a command into (service, action, extra_info).

    Returns (None, None, {}) when the command does not match any pattern
    and should fall through to the AI interpreter.
    """
    cmd = command.strip()
    cmd_lower = cmd.lower()

    # ── Greeting ──────────────────────────────────────────────────────────
    if cmd_lower in GREETING_WORDS:
        return ('meta', 'greeting', {})
    if CAPABILITIES_RE.search(cmd_lower):
        return ('meta', 'capabilities', {})

    # ── EC2: list running (must be checked before generic list) ────────────
    if LIST_RUNNING_RE.search(cmd_lower):
        return ('ec2', 'running-instances', {})

    # ── EC2: list all ─────────────────────────────────────────────────────
    if LIST_INSTANCES_RE.search(cmd_lower) and not re.search(r'\b(running|active)\b', cmd_lower):
        return ('ec2', 'all-instances', {})

    # ── EC2: stop/terminate all ───────────────────────────────────────────
    if STOP_ALL_RE.search(cmd_lower):
        return ('ec2', 'stop-all-instances', {})
    if TERMINATE_ALL_RE.search(cmd_lower):
        return ('ec2', 'terminate-all-instances', {})

    # ── EC2: single-instance operations ───────────────────────────────────
    if cmd_lower.strip() == 'stop' or STOP_INSTANCE_RE.search(cmd_lower):
        return ('ec2', 'stop-instance', {})
    if cmd_lower.strip() == 'start' or START_INSTANCE_RE.search(cmd_lower):
        return ('ec2', 'start-instance', {})
    if cmd_lower.strip() == 'terminate' or TERMINATE_INSTANCE_RE.search(cmd_lower):
        return ('ec2', 'terminate-instance', {})
    if REBOOT_INSTANCE_RE.search(cmd_lower):
        return ('ec2', 'reboot-instance', {})
    if DESCRIBE_INSTANCE_RE.search(cmd_lower):
        return ('ec2', 'describe-instance', {})

    # ── EC2: create instance ──────────────────────────────────────────────
    if CREATE_INSTANCE_RE.search(cmd_lower):
        extra = {}
        if INSTANCE_TYPE_RE.search(cmd_lower):
            extra['has_complex_params'] = True
        return ('ec2', 'create-instance', extra)

    # ── S3: delete bucket (before generic list to avoid false positives) ──
    if DELETE_BUCKET_RE.search(cmd_lower):
        bucket = extract_bucket_name_from_command(cmd_lower)
        return ('s3', 'delete-bucket', {'bucket_name': bucket})

    # ── S3: create bucket ─────────────────────────────────────────────────
    if CREATE_BUCKET_RE.search(cmd_lower):
        bucket = extract_bucket_name_from_command(cmd_lower)
        return ('s3', 'create-bucket', {'bucket_name': bucket})

    # ── S3: list buckets ──────────────────────────────────────────────────
    if LIST_BUCKETS_RE.search(cmd_lower):
        return ('s3', 'list-buckets', {})

    # ── S3: bucket contents ───────────────────────────────────────────────
    m = BUCKET_CONTENTS_RE.search(cmd_lower)
    if m:
        return ('s3', 'list-objects', {'bucket_name': m.group(3)})

    # ── S3: upload / download / delete object ─────────────────────────────
    m = UPLOAD_RE.search(cmd_lower)
    if m:
        return ('s3', 'upload-object', {'file_path': m.group(2), 'bucket_name': m.group(3)})

    m = DOWNLOAD_RE.search(cmd_lower)
    if m:
        return ('s3', 'download-object', {'object_key': m.group(2), 'bucket_name': m.group(3)})

    m = DELETE_OBJECT_RE.search(cmd_lower)
    if m:
        return ('s3', 'delete-object', {'object_key': m.group(2), 'bucket_name': m.group(3)})

    return (None, None, {})
