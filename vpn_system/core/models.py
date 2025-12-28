import json
import os
import uuid
import time
from typing import List, Dict, Optional

class UserAccount:
    def __init__(self, username: str, protocol: str, password: str = "", 
                 uuid_str: str = None, expires_at: int = None, 
                 ip_limit: int = 2, quota_gb: int = 0):
        self.username = username
        self.protocol = protocol
        self.password = password
        self.uuid = uuid_str or str(uuid.uuid4())
        self.created_at = int(time.time())
        self.expires_at = expires_at or (self.created_at + 30 * 86400)
        self.status = "active"
        self.ip_limit = ip_limit
        self.quota_gb = quota_gb
        self.used_bandwidth = 0 # In bytes

    def to_dict(self):
        return self.__dict__

class VortexDB:
    def __init__(self, db_path="/usr/local/etc/vortex-x/db.json"):
        self.db_path = db_path
        self.data = self._load()

    def _load(self):
        if os.path.exists(self.db_path):
            with open(self.db_path, "r") as f:
                return json.load(f)
        return {"users": [], "settings": {}, "hosts": []}

    def save(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with open(self.db_path, "w") as f:
            json.dump(self.data, f, indent=4)

    def add_user(self, user: UserAccount):
        self.data["users"].append(user.to_dict())
        self.save()

    def get_user(self, username):
        for u in self.data["users"]:
            if u["username"] == username:
                return u
        return None
