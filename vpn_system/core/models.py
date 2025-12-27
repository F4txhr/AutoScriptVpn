from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
import uuid
import json
import os

@dataclass
class Host:
    hostname: str
    domain: str
    ip: str
    location: str
    status: str
    supported_protocols: List[str]
    health_score: float = 100.0
    host_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self):
        return asdict(self)

@dataclass
class ProtocolPreset:
    protocol_name: str
    transports: List[str]
    default_ports: Dict[str, int]
    paths: Dict[str, str]

    def to_dict(self):
        return asdict(self)

@dataclass
class Inbound:
    protocol: str
    transport: str
    port: int
    listen_address: str
    status: str
    bound_host: str
    tag: str = ""

    def to_dict(self):
        return asdict(self)

@dataclass
class UserAccount:
    username: str
    protocol: str
    host_id: str
    credentials: Dict[str, Any] # e.g., {'uuid': '...', 'key': '...'}
    quota: int = 0 # 0 means unlimited
    used_traffic: int = 0
    expiry_date: Optional[str] = None
    status: str = "active"
    last_active: Optional[str] = None
    user_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self):
        return asdict(self)

class Database:
    def __init__(self, db_path: str = "/usr/local/lib/vpn_system/configs/db.json"):
        self.db_path = db_path
        self.data = self._load()

    def _load(self) -> Dict[str, List[Dict]]:
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                pass
        return {"hosts": [], "users": [], "inbounds": []}

    def save(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with open(self.db_path, 'w') as f:
            json.dump(self.data, f, indent=4)

    def add_host(self, host: Host):
        self.data['hosts'].append(host.to_dict())
        self.save()

    def get_host(self, host_id: str) -> Optional[Dict]:
        for h in self.data['hosts']:
            if h['host_id'] == host_id:
                return h
        return None

    def add_user(self, user: UserAccount):
        self.data['users'].append(user.to_dict())
        self.save()

    def get_user(self, username: str, protocol: str) -> Optional[Dict]:
        for u in self.data['users']:
            if u['username'] == username and u['protocol'] == protocol:
                return u
        return None

    def add_inbound(self, inbound: Inbound):
        self.data['inbounds'].append(inbound.to_dict())
        self.save()

    def get_inbounds_for_host(self, host_id: str) -> List[Dict]:
        return [i for i in self.data['inbounds'] if i['bound_host'] == host_id]
