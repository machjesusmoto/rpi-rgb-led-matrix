"""
TAYA-143: MQTT Data Source Integration

Subscribes to MQTT topics and feeds data into widget bindings.
"""

import json
import threading
import time
from typing import Any, Callable, Dict, Optional, Dict


class MQTTDataSource:
    """MQTT client that feeds data to widget bindings."""

    def __init__(self, broker: str = "localhost", port: int = 1883,
                 topics: Optional[Dict[str, str]] = None):
        self._broker = broker
        self._port = port
        self._topics = topics or {}  # binding_name -> mqtt_topic
        self._data: Dict[str, Any] = {}
        self._callbacks: Dict[str, list] = {}
        self._client = None
        self._connected = False
        self._thread: Optional[threading.Thread] = None
        self._running = False

    def connect(self) -> bool:
        """Connect to MQTT broker. Returns True if successful."""
        try:
            import paho.mqtt.client as mqtt
            self._client = mqtt.Client(
                client_id="rgb-dashboard",
                protocol=mqtt.MQTTv311
            )
            self._client.on_connect = self._on_connect
            self._client.on_message = self._on_message
            self._client.on_disconnect = self._on_disconnect

            self._client.connect(self._broker, self._port, keepalive=60)
            self._running = True
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()
            return True
        except ImportError:
            print("MQTT: paho-mqtt not installed. Run: pip install paho-mqtt")
            return False
        except Exception as e:
            print(f"MQTT: Connection failed: {e}")
            return False

    def disconnect(self) -> None:
        self._running = False
        if self._client:
            try:
                self._client.disconnect()
            except Exception:
                pass
        if self._thread:
            self._thread.join(timeout=5)

    def get(self, binding: str, default: Any = None) -> Any:
        """Get latest value for a data binding."""
        return self._data.get(binding, default)

    def get_all(self) -> Dict[str, Any]:
        """Get all current values."""
        return dict(self._data)

    def on_data(self, binding: str, callback: Callable[[str, Any], None]) -> None:
        """Register callback for when a binding gets new data."""
        self._callbacks.setdefault(binding, []).append(callback)

    def publish(self, topic: str, value: Any) -> None:
        """Publish a value to an MQTT topic."""
        if self._client and self._connected:
            payload = json.dumps(value) if isinstance(value, (dict, list)) else str(value)
            self._client.publish(topic, payload)

    # --- Internal ---

    def _loop(self) -> None:
        while self._running and self._client:
            try:
                self._client.loop(timeout=1.0)
            except Exception:
                time.sleep(1)

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self._connected = True
            print(f"MQTT: Connected to {self._broker}:{self._port}")
            for binding, topic in self._topics.items():
                client.subscribe(topic)
                print(f"MQTT: Subscribed {topic} -> {binding}")
        else:
            print(f"MQTT: Connection failed with code {rc}")

    def _on_message(self, client, userdata, msg):
        topic = msg.topic
        try:
            payload = json.loads(msg.payload.decode())
        except (json.JSONDecodeError, UnicodeDecodeError):
            payload = msg.payload.decode()

        # Find binding for this topic
        for binding, t in self._topics.items():
            if t == topic:
                old = self._data.get(binding)
                self._data[binding] = payload
                if old != payload:
                    for cb in self._callbacks.get(binding, []):
                        try:
                            cb(binding, payload)
                        except Exception as e:
                            print(f"MQTT callback error: {e}")
                break

    def _on_disconnect(self, client, userdata, rc):
        self._connected = False
        if rc != 0:
            print(f"MQTT: Unexpected disconnect (rc={rc}). Reconnecting...")
            try:
                client.reconnect()
            except Exception:
                pass


class RESTDataSource:
    """HTTP poller that periodically fetches data from REST endpoints."""

    def __init__(self, endpoints: Optional[Dict[str, dict]] = None):
        self._endpoints = endpoints or {}
        self._data: Dict[str, Any] = {}
        self._callbacks: Dict[str, list] = {}
        self._thread: Optional[threading.Thread] = None
        self._running = False

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=10)

    def get(self, binding: str, default: Any = None) -> Any:
        return self._data.get(binding, default)

    def get_all(self) -> Dict[str, Any]:
        return dict(self._data)

    def on_data(self, binding: str, callback: Callable[[str, Any], None]) -> None:
        self._callbacks.setdefault(binding, []).append(callback)

    def _poll_loop(self) -> None:
        import urllib.request
        last_poll = {}

        while self._running:
            now = time.time()
            for binding, endpoint in self._endpoints.items():
                interval = endpoint.get("interval", 30)
                if binding not in last_poll or (now - last_poll[binding]) >= interval:
                    self._fetch(binding, endpoint)
                    last_poll[binding] = now
            time.sleep(1)

    def _fetch(self, binding: str, endpoint: dict) -> None:
        import urllib.request
        url = endpoint.get("url", "")
        json_path = endpoint.get("json_path", "")

        try:
            req = urllib.request.Request(url, headers={"User-Agent": "rgb-dashboard/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())

            # Extract nested value if json_path specified
            if json_path:
                for key in json_path.split("."):
                    if isinstance(data, dict):
                        data = data.get(key, data)

            old = self._data.get(binding)
            self._data[binding] = data
            if old != data:
                for cb in self._callbacks.get(binding, []):
                    try:
                        cb(binding, data)
                    except Exception:
                        pass
        except Exception as e:
            pass  # Silently retry on next interval


class StaticDataSource:
    """Static values from config."""

    def __init__(self, values: Optional[Dict[str, Any]] = None):
        self._data = values or {}

    def get(self, binding: str, default: Any = None) -> Any:
        return self._data.get(binding, default)

    def get_all(self) -> Dict[str, Any]:
        return dict(self._data)

    def update(self, values: Dict[str, Any]) -> None:
        self._data.update(values)


class DataManager:
    """Unified data manager that queries all sources with priority."""

    def __init__(self):
        self._sources = []
        self._data: Dict[str, Any] = {}

    def add_source(self, source, priority: int = 0) -> None:
        """Add a data source. Higher priority = checked first."""
        self._sources.append((priority, source))
        self._sources.sort(key=lambda x: -x[0])

    def get(self, binding: str, default: Any = None) -> Any:
        """Get value for a binding, checking sources in priority order."""
        for _, source in self._sources:
            val = source.get(binding)
            if val is not None:
                return val
        return default

    def get_all(self) -> Dict[str, Any]:
        """Merge all sources (highest priority wins)."""
        result = {}
        for _, source in reversed(self._sources):
            result.update(source.get_all())
        return result
