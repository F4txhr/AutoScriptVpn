import uuid
import json
import os
import time
from typing import List, Dict, Any, Optional

# Manual implementation for Python < 3.7 compatibility instead of dataclasses
class Host:
    def __init__(self, hostname, domain, ip, location, status, supported_protocols, health_score=100.0, host_id=None):
        self.hostname = hostname
        self.domain = domain
        self.ip = ip
        self.location = location
        self.status = status
        self.supported_protocols = supported_protocols
        self.health_score = health_score
        self.host_id = host_id if host_id else str(uuid.uuid4())

    def to_dict(self):
        return {
            "hostname": self.hostname,
            "domain": self.domain,
            "ip": self.ip,
            "location": self.location,
            "status": self.status,
            "supported_protocols": self.supported_protocols,
            "health_score": self.health_score,
            "host_id": self.host_id
        }

class Inbound:
    def __init__(self, protocol, transport, port, listen_address, status, bound_host, tag):
        self.protocol = protocol
        self.transport = transport
        self.port = port
        self.listen_address = listen_address
        self.status = status
        self.bound_host = bound_host
        self.tag = tag

    def to_dict(self):
        return {
            "protocol": self.protocol,
            "transport": self.transport,
            "port": self.port,
            "listen_address": self.listen_address,
            "status": self.status,
            "bound_host": self.bound_host,
            "tag": self.tag
        }

class UserAccount:
    def __init__(self, username, protocol, host_id, credentials, user_id=None, created_at=None, expires_at=None, status="active"):
        self.username = username
        self.protocol = protocol
        self.host_id = host_id
        self.credentials = credentials
        self.user_id = user_id if user_id else str(uuid.uuid4())
        self.created_at = created_at if created_at else int(time.time())
        self.expires_at = expires_at if expires_at else self.created_at + (30 * 86400) # Default 30 days
        self.status = status

    def to_dict(self):
        return {
            "username": self.username,
            "protocol": self.protocol,
            "host_id": self.host_id,
            "credentials": self.credentials,
            "user_id": self.user_id,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "status": self.status
        }

class Database:
    def __init__(self, db_path="/usr/local/lib/vpn_system/db.json"):
        self.db_path = db_path
        self.data = self._load()

    def _load(self):
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, "r") as f:
                    content = f.read()
                    if not content:
                        return {"hosts": [], "users": [], "inbounds": []}
                    return json.loads(content)
            except json.JSONDecodeError:
                return {"hosts": [], "users": [], "inbounds": []}
        return {"hosts": [], "users": [], "inbounds": []}

    def _save(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with open(self.db_path, "w") as f:
            json.dump(self.data, f, indent=4)

    def add_host(self, host):
        if "hosts" not in self.data: self.data["hosts"] = []
        self.data["hosts"].append(host.to_dict())
        self._save()

    def get_host(self, host_id):
        for h in self.data.get("hosts", []):
            if h["host_id"] == host_id:
                return h
        return None

    def add_inbound(self, inbound):
        if "inbounds" not in self.data: self.data["inbounds"] = []
        self.data["inbounds"].append(inbound.to_dict())
        self._save()

    def get_hosts(self):
        return self.data.get("hosts", [])

    def add_user(self, user):
        if "users" not in self.data: self.data["users"] = []
        if hasattr(user, 'to_dict'):
            self.data["users"].append(user.to_dict())
        else:
            self.data["users"].append(user)
        self._save()

    def get_user(self, username, protocol):
        for u in self.data.get("users", []):
            if u["username"] == username and u["protocol"] == protocol:
                return u
        return None

    def get_users(self):
        return self.data.get("users", [])
