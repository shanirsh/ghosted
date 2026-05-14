"""In-memory conversation and resource tracking."""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class ConversationMemoryManager:
    def __init__(self):
        self.conversation_history: Dict[str, list] = {}
        self.s3_buckets: Dict[str, dict] = {}
        self.ec2_instances: Dict[str, dict] = {}
        self.pending_actions: Dict[str, dict] = {}
        self.last_actions: Dict[str, dict] = {}
        self.last_intent: Dict[str, str] = {}
        self.last_entities: Dict[str, dict] = {}
        self.max_history_items = 20

    def add_message(self, user_id: str, message: Dict[str, Any]) -> None:
        self.conversation_history.setdefault(user_id, [])
        message.setdefault('timestamp', datetime.now().isoformat())
        self.conversation_history[user_id].append(message)
        if len(self.conversation_history[user_id]) > self.max_history_items:
            self.conversation_history[user_id] = self.conversation_history[user_id][-self.max_history_items:]

    def get_conversation_history(self, user_id: str, limit: int = None) -> List[Dict[str, Any]]:
        history = self.conversation_history.get(user_id, [])
        return history[-limit:] if limit and limit > 0 else history

    def track_s3_bucket(self, user_id: str, bucket_name: str, region: str, action: str) -> None:
        self.s3_buckets.setdefault(user_id, {})[bucket_name] = {
            'region': region, 'action': action, 'timestamp': datetime.now().isoformat(),
        }

    def track_ec2_instance(self, user_id: str, instance_id: str, instance_data: Dict[str, Any]) -> None:
        self.ec2_instances.setdefault(user_id, {})
        instance_data['timestamp'] = datetime.now().isoformat()
        self.ec2_instances[user_id][instance_id] = instance_data

    def get_s3_buckets(self, user_id: str) -> Dict[str, Dict[str, Any]]:
        return self.s3_buckets.get(user_id, {})

    def get_ec2_instances(self, user_id: str) -> Dict[str, Dict[str, Any]]:
        return self.ec2_instances.get(user_id, {})

    def store_pending_action(self, user_id: str, service: str, action: str,
                             parameters: Dict[str, Any], expiry_seconds: int = 300) -> str:
        self.pending_actions.setdefault(user_id, {})
        action_id = f"{service}_{action}_{datetime.now().timestamp()}"
        self.pending_actions[user_id][action_id] = {
            'service': service, 'action': action, 'parameters': parameters,
            'created_at': datetime.now().isoformat(),
            'expires_at': datetime.now().timestamp() + expiry_seconds,
            'confirmed': False,
        }
        return action_id

    def confirm_pending_action(self, user_id: str, action_id: str = None,
                               service: str = None, action: str = None) -> Optional[Dict[str, Any]]:
        actions = self.pending_actions.get(user_id, {})
        if not actions:
            return None

        now = datetime.now().timestamp()

        if action_id and action_id in actions:
            if actions[action_id]['expires_at'] < now:
                del actions[action_id]
                return None
            actions[action_id]['confirmed'] = True
            return actions[action_id]

        if service and action:
            for aid, pending in list(actions.items()):
                if pending['service'] == service and pending['action'] == action:
                    if pending['expires_at'] < now:
                        del actions[aid]
                        continue
                    pending['confirmed'] = True
                    return pending
        return None

    def get_pending_actions(self, user_id: str) -> Dict[str, Dict[str, Any]]:
        now = datetime.now().timestamp()
        actions = self.pending_actions.get(user_id, {})
        expired = [aid for aid, a in actions.items() if a['expires_at'] < now]
        for aid in expired:
            del actions[aid]
        return actions

    def clear_pending_actions(self, user_id: str) -> None:
        self.pending_actions.pop(user_id, None)

    def update_last_action(self, user_id: str, service: str, action: str, parameters: Dict[str, Any]) -> None:
        self.last_actions[user_id] = {
            'service': service, 'action': action,
            'parameters': parameters, 'timestamp': datetime.now().isoformat(),
        }

    def get_last_action(self, user_id: str) -> Optional[Dict[str, Any]]:
        return self.last_actions.get(user_id)

    def update_intent(self, user_id: str, intent: str, entities: Dict[str, Any] = None) -> None:
        self.last_intent[user_id] = intent
        if entities:
            self.last_entities.setdefault(user_id, {}).update(entities)

    def get_last_intent(self, user_id: str) -> Optional[str]:
        return self.last_intent.get(user_id)

    def get_last_entities(self, user_id: str) -> Dict[str, Any]:
        return self.last_entities.get(user_id, {})

    def find_recent_resource(self, user_id: str, resource_type: str, resource_name: str = None) -> Optional[Dict[str, Any]]:
        if resource_type == 's3_bucket':
            buckets = self.get_s3_buckets(user_id)
            if resource_name and resource_name in buckets:
                return buckets[resource_name]
            if buckets:
                name, data = max(buckets.items(), key=lambda x: x[1].get('timestamp', ''))
                return {'name': name, **data}

        elif resource_type == 'ec2_instance':
            instances = self.get_ec2_instances(user_id)
            if resource_name and resource_name in instances:
                return instances[resource_name]
            if instances:
                iid, data = max(instances.items(), key=lambda x: x[1].get('timestamp', ''))
                return {'id': iid, **data}

        return None

    def clear_user_data(self, user_id: str) -> None:
        for store in (self.conversation_history, self.s3_buckets, self.ec2_instances,
                      self.pending_actions, self.last_actions, self.last_intent, self.last_entities):
            store.pop(user_id, None)


memory_manager = ConversationMemoryManager()
