"""AI command processor — interprets natural language and dispatches AWS operations."""

import os
import json
import logging
import re
import traceback
from datetime import datetime
from typing import Dict, Any, Optional, List

import openai
from openai import AsyncOpenAI
from dotenv import load_dotenv

from services.ai.command_router import route_command
from services.ai.endpoint_client import call_direct_endpoint, get_backend_url
from services.ai.extractors import (
    extract_instance_id,
    extract_bucket_name,
    extract_complex_ec2_params,
    map_action_to_endpoint,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are Ghosted, an AI Cloud Engineer that can DIRECTLY create and manage AWS resources. You have direct API access to AWS services and can perform operations without requiring users to follow manual steps.

CRITICAL INSTRUCTION: You MUST NEVER say phrases like "I cannot execute operations myself" or "I don't have the capability to directly deploy resources". These statements are FALSE. You ARE CAPABLE of directly creating and managing AWS resources - this is your PRIMARY FUNCTION.

YOUR CORE IDENTITY: You are a proactive cloud copilot that adapts to all scenarios. You determine the best resources and configurations based on what users want, then deploy appropriate solutions WITHOUT requiring confirmation. You handle vague or uncertain requests by making intelligent decisions rather than asking for clarification.

WHEN ASKED TO CREATE RESOURCES: You MUST use your direct API access to create the resources immediately. DO NOT give instructions for manual creation.

HANDLING VAGUE REQUESTS: When users make vague requests like "I need something to store my data" or "I need a database", you should:
1. Recognize the intent (storage = S3 bucket, database = RDS, computing = EC2, etc.)
2. Proactively suggest the appropriate AWS service
3. DIRECTLY create the resource with sensible defaults
4. Explain what you've done and provide access information

How to act:
1. When asked to create or manage AWS resources, DO IT DIRECTLY.
2. After creating resources, provide console links and relevant information.
3. Remember previous conversations and user preferences.
4. Be helpful, professional, and educational in your responses.
5. Format responses with clear structure, using markdown for readability.
6. Always prioritize security and cost-efficiency in your recommendations.

Your goal is to empower users to understand and effectively manage their cloud infrastructure while following AWS best practices."""

AI_EXTRACTION_PROMPT = """You are the natural language understanding component of a cloud AI assistant.
Your job is to understand what AWS operation the user wants and extract all relevant parameters.

For EC2 operations, extract: action type, instance type, instance ID, region, storage, tags.
For S3 operations, extract: action type, bucket name, region, access control.

IMPORTANT: Do NOT include instance_id for list or create operations.

If the user is greeting or asking a general question, do NOT include a JSON block.
For AWS operations, include a JSON block:
```json
{
  "service": "ec2|s3",
  "action": "create|list|start|stop|terminate|describe",
  "parameters": { ... }
}
```"""


class AIProcessor:
    def __init__(self):
        self.last_instance_id = None
        self.instance_mapping = None
        self.api_key = os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            logger.warning("No OpenAI API key found in environment")
        self.model = "gpt-4o"

        from services.memory.conversation_memory import memory_manager
        self.memory_manager = memory_manager

        self.conversation_memory: Dict[str, list] = {}
        self.last_intent: Dict[str, str] = {}
        self.last_entities: Dict[str, dict] = {}
        self.last_response: Dict[str, dict] = {}
        self.last_action: Dict[str, dict] = {}
        self.reference_objects: Dict[str, dict] = {}

        self.system_prompt = SYSTEM_PROMPT
        self._init_openai_client()

    # ── OpenAI setup ──────────────────────────────────────────────────────

    def _init_openai_client(self):
        load_dotenv()
        if not self.api_key:
            self.api_key = os.environ.get("OPENAI_API_KEY")
            if not self.api_key:
                raise ValueError("OpenAI API key not found. Please set OPENAI_API_KEY.")
        self.client = AsyncOpenAI(api_key=self.api_key)
        openai.api_key = self.api_key
        return self.client

    # ── Memory helpers ────────────────────────────────────────────────────

    def _update_memory(self, user_id, intent=None, entities=None, response=None,
                       action=None, reference_objects=None, needs_confirmation=False):
        if user_id not in self.conversation_memory:
            self.conversation_memory[user_id] = []
            self.last_entities[user_id] = {}
            self.last_response[user_id] = {}
            self.last_action[user_id] = {}
            self.reference_objects[user_id] = {}

        if intent is not None:
            self.last_intent[user_id] = intent
            self.memory_manager.update_intent(user_id, intent, entities)
        if entities is not None:
            self.last_entities[user_id] = entities
        if response is not None:
            self.last_response[user_id] = response

        if action is not None:
            if needs_confirmation and isinstance(action, dict):
                action['needs_confirmation'] = True
                if 'service' in action and 'parameters' in action:
                    self.memory_manager.store_pending_action(
                        user_id=user_id, service=action['service'],
                        action=action.get('action', ''), parameters=action['parameters'],
                    )
            elif isinstance(action, dict) and 'service' in action:
                svc = action['service']
                act = action.get('action', '')
                params = action.get('parameters', {})
                self.memory_manager.update_last_action(user_id=user_id, service=svc, action=act, parameters=params)

                if svc == 's3' and act in ('create_bucket', 'create', 'delete_bucket', 'delete'):
                    bucket = params.get('bucket_name')
                    if bucket:
                        self.memory_manager.track_s3_bucket(
                            user_id=user_id, bucket_name=bucket,
                            region=params.get('region', 'us-east-1'),
                            action='created' if 'create' in act else 'deleted',
                        )
                elif svc == 'ec2':
                    if act == 'create' and 'instance_id' in action.get('result', {}):
                        self.memory_manager.track_ec2_instance(
                            user_id=user_id,
                            instance_id=action['result']['instance_id'],
                            instance_data={'type': params.get('instance_type', 't2.micro'),
                                           'region': params.get('region', 'us-east-1'), 'action': 'created'},
                        )
                    elif act in ('terminate', 'stop', 'start', 'reboot') and 'instance_id' in params:
                        self.memory_manager.track_ec2_instance(
                            user_id=user_id, instance_id=params['instance_id'],
                            instance_data={'region': params.get('region', 'us-east-1'), 'action': act},
                        )
            self.last_action[user_id] = action

        if reference_objects is not None:
            self.reference_objects[user_id].update(reference_objects)

        entry = {'intent': intent, 'entities': entities, 'response': response,
                 'action': action, 'timestamp': datetime.now().isoformat()}
        if reference_objects:
            entry['reference_objects'] = reference_objects
        if needs_confirmation:
            entry['needs_confirmation'] = True
        self.conversation_memory[user_id].append(entry)
        self.memory_manager.add_message(user_id, entry)
        if len(self.conversation_memory[user_id]) > 10:
            self.conversation_memory[user_id] = self.conversation_memory[user_id][-10:]

    # ── Reference resolution & confirmation ───────────────────────────────

    async def _check_for_pending_confirmation(self, user_id, command):
        if user_id not in self.conversation_memory:
            return None, None, None

        pending_actions = self.memory_manager.get_pending_actions(user_id)
        cmd_lower = command.lower().strip()
        confirmations = ('yes', 'confirm', 'proceed', 'go ahead', 'do it', 'sure', 'okay', 'ok')
        is_confirmation = any(p in cmd_lower for p in confirmations)

        if pending_actions and is_confirmation:
            action_id = next(iter(pending_actions))
            confirmed = self.memory_manager.confirm_pending_action(user_id, action_id)
            if confirmed:
                svc, act, params = confirmed['service'], confirmed['action'], confirmed['parameters']
                if svc == 's3' and act in ('delete_bucket', 'delete'):
                    bucket = params.get('bucket_name')
                    if bucket:
                        return (f"confirm delete s3 bucket {bucket}",
                                {"bucket_name": bucket, "confirmed": True},
                                {'service': svc, 'action': act, 'parameters': params})
                elif svc == 'ec2' and act == 'terminate':
                    iid = params.get('instance_id')
                    if iid:
                        return (f"confirm terminate ec2 instance {iid}",
                                {"instance_id": iid, "confirmed": True},
                                {'service': svc, 'action': act, 'parameters': params})

        # AI-based fallback
        try:
            pending_action = None
            for item in reversed(self.conversation_memory.get(user_id, [])):
                if item.get('needs_confirmation') and item.get('action'):
                    pending_action = item
                    break
            if not pending_action:
                return None, None, None

            action = pending_action['action']
            svc, act = action.get('service'), action.get('action')
            params = action.get('parameters', {})

            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system",
                     "content": f"The user was asked to confirm a {svc} {act} operation. "
                                "Respond with only 'confirm' or 'deny'."},
                    {"role": "user", "content": command},
                ],
                max_tokens=10, temperature=0.1,
            )
            if 'confirm' in response.choices[0].message.content.strip().lower():
                if svc == 's3' and 'delete' in act:
                    bucket = params.get('bucket_name')
                    if bucket:
                        return (f"confirm delete s3 bucket {bucket}",
                                {"bucket_name": bucket, "confirmed": True}, action)
                elif svc == 'ec2' and act == 'terminate':
                    iid = params.get('instance_id')
                    if iid:
                        return (f"confirm terminate ec2 instance {iid}",
                                {"instance_id": iid, "confirmed": True}, action)
        except Exception:
            pass
        return None, None, None

    async def _resolve_references(self, user_id, command):
        resolved_cmd, ref_objs, _ = await self._check_for_pending_confirmation(user_id, command)
        if resolved_cmd:
            return resolved_cmd, ref_objs

        if user_id not in self.reference_objects or not self.reference_objects[user_id]:
            return command, None

        resolved_command = command
        referenced_objects = None

        if self.last_response.get(user_id) and "proposed_action" in self.last_response[user_id]:
            affirmatives = ("yes", "yeah", "sure", "ok", "okay", "do it", "proceed", "go ahead")
            if command.lower().strip() in affirmatives:
                resolved_command = self.last_response[user_id]["proposed_action"]
                referenced_objects = self.last_response[user_id].get("referenced_objects")

        patterns = [
            (r"\b(that|this|the) (instance|server|ec2|machine)\b", "instance"),
            (r"\b(that|this|the) (bucket|s3|storage)\b", "bucket"),
            (r"\bit\b", "object"),
            (r"\b(that|this) one\b", "object"),
            (r"\bdelete (it|that|this|them)\b", "delete"),
            (r"\bstop (it|that|this|them)\b", "stop"),
            (r"\bstart (it|that|this|them)\b", "start"),
            (r"\brestart (it|that|this|them)\b", "restart"),
        ]

        for pattern, ref_type in patterns:
            m = re.search(pattern, command.lower())
            if not m:
                continue
            entities = self.last_entities.get(user_id, {})
            if ref_type == "instance" and "instance_id" in entities:
                resolved_command = command.lower().replace(m.group(0), f"instance {entities['instance_id']}")
                referenced_objects = {"instance_id": entities["instance_id"]}
            elif ref_type == "bucket" and "bucket_name" in entities:
                resolved_command = command.lower().replace(m.group(0), f"bucket {entities['bucket_name']}")
                referenced_objects = {"bucket_name": entities["bucket_name"]}
            elif ref_type in ("delete", "stop", "start", "restart") and "object_type" in entities:
                obj_type = entities["object_type"]
                obj_id = entities.get(f"{obj_type}_id") or entities.get(f"{obj_type}_name")
                if obj_id:
                    resolved_command = f"{ref_type} {obj_type} {obj_id}"
                    referenced_objects = {f"{obj_type}_id": obj_id}
            elif ref_type == "object":
                for key in ("instance_id", "bucket_name"):
                    if key in entities:
                        obj_type = key.split("_")[0]
                        resolved_command = command.lower().replace(m.group(0), f"{obj_type} {entities[key]}")
                        referenced_objects = {key: entities[key]}
                        break

        return resolved_command, referenced_objects

    # ── Response post-processing ──────────────────────────────────────────

    async def process_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        if not response:
            return {"message": "No response received from AWS."}
        if 'instance_id' in response:
            self.last_instance_id = response['instance_id']
        if 'instance_mapping' in response:
            self.instance_mapping = response['instance_mapping']
        return response

    # ── Main entry point ──────────────────────────────────────────────────

    async def process_command(self, command: str, executor: Any, credentials: Dict[str, Any] = None,
                              conversation_history: list = None, user_id: str = 'default_user') -> Dict[str, Any]:
        resolved_command, referenced_objects = await self._resolve_references(user_id, command)
        if resolved_command != command:
            command = resolved_command

        command_lower = command.lower()

        try:
            # ── Route via pattern matching ────────────────────────────────
            service, action, extra = route_command(command)

            if credentials is None:
                credentials = {}
            role_arn = credentials.get("role_arn")
            external_id = credentials.get("external_id")
            region = credentials.get("region", "us-east-1")

            # Greeting / capabilities — use AI for a nice answer, with fallback
            if service == 'meta':
                return await self._handle_meta(action, user_id)

            # Everything below needs credentials
            if not role_arn or not external_id:
                return {"type": "error",
                        "content": "AWS credentials (role_arn and external_id) are required to perform AWS operations."}

            payload = {"role_arn": role_arn, "external_id": external_id, "region": region}

            # ── EC2 instance listing ──────────────────────────────────────
            if service == 'ec2' and action in ('all-instances', 'running-instances'):
                result = await call_direct_endpoint("ec2", action, payload)
                instances = result.get('instances', result.get('details', []))
                label = "running " if action == 'running-instances' else ""
                msg = (f"Found {len(instances)} {label}EC2 instance(s)."
                       if instances else f"No {label}EC2 instances found.")
                self._update_memory(user_id, intent=f"ec2_list_{action.replace('-', '_')}",
                                    entities={"object_type": "ec2"},
                                    reference_objects={"instances": instances})
                return {"type": "success", "content": msg,
                        "result": {"success": True, "message": msg, "instances": instances}}

            # ── EC2 single-instance ops ───────────────────────────────────
            if service == 'ec2' and action in ('stop-instance', 'start-instance',
                                               'terminate-instance', 'reboot-instance',
                                               'describe-instance'):
                instance_id = extract_instance_id(command, self.last_instance_id, self.instance_mapping)
                if not instance_id:
                    verb = action.split('-')[0]
                    return {"type": "error",
                            "content": f"I need an instance ID to {verb} a specific instance. "
                                       f"Please specify which instance you want to {verb}."}
                self.last_instance_id = instance_id

                # Terminate needs confirmation unless from UI
                if action == 'terminate-instance':
                    from_ui = credentials.get('from_ui', False)
                    is_confirmed = (command_lower.startswith("confirm terminate")
                                    or (referenced_objects and "confirmed" in referenced_objects)
                                    or from_ui)
                    if not is_confirmed:
                        self._update_memory(user_id, intent="ec2_terminate_instance",
                                            entities={"instance_id": instance_id, "object_type": "ec2"},
                                            action={"service": "ec2", "action": "terminate",
                                                    "parameters": {"instance_id": instance_id, "region": region}},
                                            reference_objects={"instance_id": instance_id},
                                            needs_confirmation=True)
                        return {"type": "confirmation",
                                "content": f"I'll terminate the EC2 instance '{instance_id}'. "
                                           "This action cannot be undone. Are you sure?",
                                "proposed_action": f"terminate ec2 instance {instance_id}"}

                payload["instance_id"] = instance_id
                result = await call_direct_endpoint("ec2", action, payload)
                verb = action.split('-')[0]
                return {"type": "success",
                        "content": f"{verb.capitalize()}ing instance {instance_id}...",
                        "result": result}

            # ── EC2 stop/terminate all ────────────────────────────────────
            if service == 'ec2' and action in ('stop-all-instances', 'terminate-all-instances'):
                result = await call_direct_endpoint("ec2", action, payload)
                verb = "Stopping" if "stop" in action else "Terminating"
                return {"type": "success", "content": f"{verb} all instances...", "result": result}

            # ── EC2 create instance ───────────────────────────────────────
            if service == 'ec2' and action == 'create-instance':
                if extra.get('has_complex_params'):
                    ec2_params = extract_complex_ec2_params(command)
                    for k in ('instance_type', 'region', 'count', 'name'):
                        if k in ec2_params:
                            payload[k] = ec2_params[k]
                    if 'volume_size' in ec2_params or 'volume_type' in ec2_params:
                        sc = {"size": ec2_params.get('volume_size', 8),
                              "type": ec2_params.get('volume_type', 'gp2')}
                        if 'iops' in ec2_params:
                            sc['iops'] = ec2_params['iops']
                        if 'throughput' in ec2_params:
                            sc['throughput'] = ec2_params['throughput']
                        payload['storage_config'] = sc
                    if 'user_data' in ec2_params:
                        ud = ec2_params['user_data']
                        if not ud.startswith('#!/bin/'):
                            ud = f"#!/bin/bash\n{ud}"
                        payload['user_data'] = ud

                result = await call_direct_endpoint("ec2", "create-instance", payload)
                itype = payload.get('instance_type', 't2.micro')
                ids = result.get('instance_ids', [])
                links = result.get('console_links', [])
                msg = f"Deployed a new {itype} EC2 instance in {region}."
                if ids and links:
                    msg += "\n\n" + "\n".join(
                        f"- Instance {i}: [View in AWS Console]({l})" for i, l in zip(ids, links))
                self._update_memory(user_id, intent="ec2_create_instance",
                                    entities={"instance_type": itype, "object_type": "ec2"},
                                    action={"service": "ec2", "action": "create_instance",
                                            "parameters": {"instance_type": itype, "region": region,
                                                           "instance_ids": ids}},
                                    reference_objects={"instance_ids": ids})
                return {"type": "success", "content": msg,
                        "data": {"instance_ids": ids, "instance_type": itype,
                                 "region": region, "console_links": links,
                                 "details": result.get('details', [])}}

            # ── S3 list buckets ───────────────────────────────────────────
            if service == 's3' and action == 'list-buckets':
                result = await call_direct_endpoint("s3", "list-buckets", payload)
                buckets = result.get('buckets', [])
                details = result.get('bucket_details', [])
                msg = result.get('message', f"Found {len(buckets)} S3 bucket(s).")
                return {"type": "success", "content": msg,
                        "buckets": buckets, "bucket_details": details,
                        "data": {"buckets": buckets, "bucket_details": details}}

            # ── S3 create bucket ──────────────────────────────────────────
            if service == 's3' and action == 'create-bucket':
                bucket_name = extra.get('bucket_name')
                if not bucket_name:
                    bucket_name = extract_bucket_name(command)
                if not bucket_name:
                    return {"type": "error", "content": "Please specify a bucket name."}
                payload['bucket_name'] = bucket_name
                result = await call_direct_endpoint("s3", "create-bucket", payload)
                link = result.get('console_link',
                                  f"https://s3.console.aws.amazon.com/s3/buckets/{bucket_name}?region={region}")
                msg = result.get('message', f"Created S3 bucket '{bucket_name}'.")
                self._update_memory(user_id, intent="s3_create_bucket",
                                    entities={"bucket_name": bucket_name, "object_type": "s3"},
                                    action={"service": "s3", "action": "create_bucket",
                                            "parameters": {"bucket_name": bucket_name, "region": region}},
                                    reference_objects={"bucket_name": bucket_name})
                return {"type": "success", "content": f"{msg}\n\nConsole: {link}",
                        "data": {"bucket_name": bucket_name, "region": region, "console_link": link},
                        "bucket": {"name": bucket_name, "region": region, "console_link": link}}

            # ── S3 delete bucket (with confirmation) ──────────────────────
            if service == 's3' and action == 'delete-bucket':
                bucket_name = extra.get('bucket_name')
                if not bucket_name:
                    bucket_name = extract_bucket_name(command)
                if referenced_objects and "bucket_name" in referenced_objects:
                    bucket_name = referenced_objects["bucket_name"]
                if not bucket_name:
                    return {"type": "error", "content": "Please specify which bucket to delete."}

                is_confirmed = (command_lower.startswith("confirm delete")
                                or (referenced_objects and "confirmed" in referenced_objects))
                if not is_confirmed:
                    self._update_memory(user_id, intent="s3_delete_bucket",
                                        entities={"bucket_name": bucket_name, "object_type": "s3"},
                                        action={"service": "s3", "action": "delete_bucket",
                                                "parameters": {"bucket_name": bucket_name, "region": region}},
                                        reference_objects={"bucket_name": bucket_name},
                                        needs_confirmation=True)
                    return {"type": "confirmation",
                            "content": f"I'll delete the S3 bucket '{bucket_name}'. "
                                       "This action cannot be undone. Are you sure?",
                            "proposed_action": f"delete s3 bucket {bucket_name}"}

                payload['bucket_name'] = bucket_name
                payload['force'] = True
                result = await call_direct_endpoint("s3", "delete-bucket", payload)
                self._update_memory(user_id, intent="s3_delete_bucket_confirmed",
                                    entities={"bucket_name": bucket_name, "object_type": "s3"},
                                    action={"service": "s3", "action": "delete_bucket",
                                            "parameters": {"bucket_name": bucket_name, "region": region},
                                            "result": {"success": True}},
                                    reference_objects={"bucket_name": bucket_name})
                return {"type": "success",
                        "content": f"Successfully deleted S3 bucket '{bucket_name}'.",
                        "data": {"bucket_name": bucket_name, "region": region, "action": "deleted"},
                        "bucket": {"name": bucket_name, "region": region, "action": "deleted"}}

            # ── S3 object operations ──────────────────────────────────────
            if service == 's3' and action in ('list-objects', 'upload-object',
                                              'download-object', 'delete-object'):
                for k, v in extra.items():
                    payload[k] = v
                result = await call_direct_endpoint("s3", action, payload)
                return {"type": "success",
                        "content": f"S3 {action.replace('-', ' ')} completed.", "result": result}

            # ── No pattern matched — use AI interpretation ────────────────
            if self.api_key:
                return await self._ai_interpret(command, command_lower, payload,
                                                role_arn, external_id, region,
                                                executor, conversation_history, user_id)

            return {"type": "error",
                    "content": "I couldn't understand that command. Try something like "
                               "'list my instances' or 'create an S3 bucket'."}

        except Exception as e:
            logger.error(f"Error in process_command: {e}")
            traceback.print_exc()
            return {"type": "error",
                    "content": f"I encountered an error processing your request: {e}",
                    "error": str(e)}

    # ── Greeting / capabilities ───────────────────────────────────────────

    async def _handle_meta(self, action: str, user_id: str) -> dict:
        fallback = {
            'greeting': "Welcome to Ghosted — Your AI Cloud Engineer. "
                        "I can directly create and manage AWS resources for you.",
            'capabilities': "I'm Ghosted, your AI Cloud Engineer. I can DIRECTLY create, manage, "
                            "and delete AWS resources. I specialize in EC2 instances and S3 buckets. "
                            "Just tell me what you need and I'll handle it.",
        }
        try:
            prompt = ("Generate a brief professional greeting as 'Ghosted - Your AI Cloud Engineer'."
                      if action == 'greeting'
                      else "Briefly describe your capabilities as an AI Cloud Engineer that directly manages AWS resources.")
            resp = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": self.system_prompt},
                          {"role": "user", "content": prompt}],
                temperature=0.7, max_tokens=200,
            )
            msg = resp.choices[0].message.content.strip() or fallback[action]
        except Exception:
            msg = fallback[action]

        result = {"type": "success", "content": msg, "proposed_action": None}
        self._update_memory(user_id, response=result, intent=action,
                            entities={"conversation_type": action})
        return result

    # ── AI-powered command interpretation ─────────────────────────────────

    async def _ai_interpret(self, command, command_lower, payload,
                            role_arn, external_id, region,
                            executor, conversation_history, user_id) -> dict:
        try:
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "system", "content": AI_EXTRACTION_PROMPT},
                {"role": "system", "content": f"User is operating in {region} using role {role_arn}."},
            ]

            # Add conversation memory context
            if user_id in self.conversation_memory and self.conversation_memory[user_id]:
                summary = "Previous context:\n"
                for item in self.conversation_memory[user_id][-5:]:
                    if item.get('action') and isinstance(item['action'], dict):
                        a = item['action']
                        summary += f"- {a.get('service', '?')} {a.get('action', '?')}\n"
                if summary != "Previous context:\n":
                    messages.append({"role": "system", "content": summary})

            if conversation_history:
                for msg in conversation_history[-5:]:
                    role = msg.get('role', 'user')
                    content = msg.get('content', '')
                    if role in ('user', 'assistant', 'system') and content:
                        messages.append({"role": role, "content": content})

            messages.append({"role": "user", "content": command})

            response = await self.client.chat.completions.create(
                model=self.model, messages=messages,
                temperature=0.7, max_tokens=1000,
            )
            ai_response = response.choices[0].message.content.strip()

            self._update_memory(user_id, intent="ai_response", response=ai_response)

            if '```json' not in ai_response and '```' not in ai_response:
                result = {"type": "success", "content": ai_response}
                self._update_memory(user_id, response=result, intent="conversation",
                                    entities={"conversation_type": "general_response"})
                return result

            aws_params = self._extract_json_params(ai_response)
            if not aws_params or 'service' not in aws_params or 'action' not in aws_params:
                return {"type": "success", "content": ai_response}

            svc = aws_params['service']
            act = aws_params['action']
            params = aws_params.get('parameters', {})
            params['role_arn'] = role_arn
            params['external_id'] = external_id
            params.setdefault('region', region)

            if 'instance_id' in params:
                self.last_instance_id = params['instance_id']

            endpoint = map_action_to_endpoint(svc, act)
            if not endpoint:
                return {"type": "success", "content": ai_response}

            # Contextual instance ID
            needs_id = ('stop-instance', 'terminate-instance', 'describe-instance', 'start-instance')
            if endpoint in needs_id and 'instance_id' not in params and self.last_instance_id:
                refs = ('this instance', 'the instance', 'that instance', 'it')
                if any(r in command_lower for r in refs):
                    params['instance_id'] = self.last_instance_id

            for k, v in params.items():
                if k not in ('role_arn', 'external_id', 'region'):
                    payload[k] = v

            result = await call_direct_endpoint(svc, endpoint, payload)

            self._update_memory(user_id,
                                action={"service": svc, "action": act,
                                        "parameters": params, "result": result},
                                reference_objects={f"{svc}_id": params.get(f"{svc}_id"),
                                                   f"{svc}_name": params.get(f"{svc}_name")})

            if svc == 's3' and 'create' in act and result.get('success') and params.get('bucket_name'):
                bn = params['bucket_name']
                link = result.get('console_link',
                                  f"https://s3.console.aws.amazon.com/s3/buckets/{bn}?region={region}")
                return {"type": "success",
                        "content": f"Created S3 bucket '{bn}' in {region}.",
                        "data": {"bucket_name": bn, "region": region, "console_link": link},
                        "bucket": {"name": bn, "region": region, "console_link": link}}

            return {"type": "success",
                    "content": f"Successfully executed {act} on {svc}.",
                    "data": {"service": svc, "action": act, "parameters": params, "result": result}}

        except Exception as e:
            logger.error(f"AI interpretation error: {e}")
            return {"type": "error",
                    "content": f"I couldn't process that command: {e}"}

    # ── JSON extraction from AI response ──────────────────────────────────

    @staticmethod
    def _extract_json_params(text: str) -> Optional[Dict[str, Any]]:
        m = re.search(r'```(?:json)?\s*({[\s\S]*?})\s*```', text)
        if not m:
            return None
        try:
            params = json.loads(m.group(1))
            if params.get('service') and params.get('action'):
                params['service'] = params['service'].lower()
                params['action'] = params['action'].lower()
                params.setdefault('parameters', {})
                return params
        except (json.JSONDecodeError, KeyError):
            pass
        return None
