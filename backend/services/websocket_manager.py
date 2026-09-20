import json
import logging
from typing import Dict, List, Set, Any
from fastapi import WebSocket

logger = logging.getLogger("websocket_manager")

class ConnectionManager:
    def __init__(self):
        # Map of active connections: connection -> metadata
        self.active_connections: Set[WebSocket] = set()
        # User id to websockets mapping
        self.user_connections: Dict[str, Set[WebSocket]] = {}
        # Role to websockets mapping
        self.role_connections: Dict[str, Set[WebSocket]] = {}
        # District to websockets mapping
        self.district_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str = "anonymous", role: str = "GUEST", district: str = "ALL"):
        await websocket.accept()
        self.active_connections.add(websocket)
        
        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(websocket)
        
        if role not in self.role_connections:
            self.role_connections[role] = set()
        self.role_connections[role].add(websocket)
        
        if district not in self.district_connections:
            self.district_connections[district] = set()
        self.district_connections[district].add(websocket)
        
        # Send initial connection ack
        await websocket.send_json({
            "type": "CONNECTION_ESTABLISHED",
            "status": "CONNECTED",
            "user_id": user_id,
            "role": role,
            "district": district
        })

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        
        # Remove from user connections
        for u_id in list(self.user_connections.keys()):
            self.user_connections[u_id].discard(websocket)
            if not self.user_connections[u_id]:
                del self.user_connections[u_id]
                
        # Remove from role connections
        for r in list(self.role_connections.keys()):
            self.role_connections[r].discard(websocket)
            if not self.role_connections[r]:
                del self.role_connections[r]
                
        # Remove from district connections
        for d in list(self.district_connections.keys()):
            self.district_connections[d].discard(websocket)
            if not self.district_connections[d]:
                del self.district_connections[d]

    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast event to all connected clients."""
        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                dead_connections.append(connection)
        for dc in dead_connections:
            self.disconnect(dc)

    async def send_to_user(self, user_id: str, message: Dict[str, Any]):
        """Send event to a specific user's active devices."""
        if user_id in self.user_connections:
            dead_connections = []
            for connection in self.user_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    dead_connections.append(connection)
            for dc in dead_connections:
                self.disconnect(dc)

    async def send_to_role(self, role: str, message: Dict[str, Any]):
        """Send event to all users with a specific role."""
        if role in self.role_connections:
            dead_connections = []
            for connection in self.role_connections[role]:
                try:
                    await connection.send_json(message)
                except Exception:
                    dead_connections.append(connection)
            for dc in dead_connections:
                self.disconnect(dc)

    async def send_to_district(self, district: str, message: Dict[str, Any]):
        """Send event to users in a specific district."""
        if district in self.district_connections:
            dead_connections = []
            for connection in self.district_connections[district]:
                try:
                    await connection.send_json(message)
                except Exception:
                    dead_connections.append(connection)
            for dc in dead_connections:
                self.disconnect(dc)

ws_manager = ConnectionManager()
