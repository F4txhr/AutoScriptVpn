from dataclasses import dataclass, field
from typing import List, Dict
import uuid

@dataclass
class Host:
    hostname: str
    domain: str
    ip: str
    location: str
    status: str
    supported_protocols: List[str]
    health_score: float
    host_id: str = field(default_factory=lambda: str(uuid.uuid4()))

@dataclass
class ProtocolPreset:
    protocol_name: str
    transports: List[str]
    default_ports: Dict[str, int]
    paths: Dict[str, str]

@dataclass
class Inbound:
    protocol: str
    transport: str
    port: int
    listen_address: str
    status: str
    bound_host: str

@dataclass
class UserAccount:
    username: str
    protocol: str
    host_id: str
    credentials: Dict[str, str] # e.g., {'uuid': '...', 'key': '...'}
    quota: int
    used_traffic: int
    expiry_date: str
    status: str
    last_active: str
    user_id: str = field(default_factory=lambda: str(uuid.uuid4()))
