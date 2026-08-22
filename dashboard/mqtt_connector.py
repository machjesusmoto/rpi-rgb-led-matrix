"""
TAYA-143: IoT Data Integration — MQTT Connector

Subscribes to MQTT topics and feeds data to dashboard widgets.
Supports wildcard topic matching and JSON payload parsing.
"""

import json
import time
import threading
from typing import Callable, Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class MQTTMessage:
    """Parsed MQTT message."""
    topic: str
    payload: str
    qos: int = 0
    timestamp: float = field(default_factory=time.time)
    
    def parse_json(self) -> Optional[dict]:
        """Try to parse payload as JSON."""
        try:
            return json.loads(self.payload)
        except (json.JSONDecodeError, TypeError):
            return None


class TopicRouter:
    """Routes MQTT messages to callbacks based on topic patterns."""
    
    def __init__(self):
        self._routes: List[tuple] = []  # (pattern, callback)
        self._exact: Dict[str, List[Callable]] = {}
        self._wildcard: List[tuple] = []  # (segments, callback)
    
    def subscribe(self, topic: str, callback: Callable[[MQTTMessage], None]) -> None:
        """Subscribe to a topic pattern. Supports + and # wildcers."""
        if '#' in topic or '+' in topic:
            segments = topic.split('/')
            self._wildcard.append((segments, callback))
        else:
            if topic not in self._exact:
                self._exact[topic] = []
            self._exact[topic].append(callback)
    
    def route(self, msg: MQTTMessage) -> None:
        """Route a message to matching callbacks."""
        # Exact match first
        if msg.topic in self._exact:
            for cb in self._exact[msg.topic]:
                try:
                    cb(msg)
                except Exception as e:
                    print(f"[MQTT] Callback error on {msg.topic}: {e}")
        
        # Wildcard match
        for pattern_segs, cb in self._wildcard:
            if self._topic_matches(pattern_segs, msg.topic):
                try:
                    cb(msg)
                except Exception as e:
                    print(f"[MQTT] Callback error on {msg.topic}: {e}")
    
    def _topic_matches(self, pattern_segs: List[str], topic: str) -> bool:
        """Check if a topic matches a pattern with + and # wildcards."""
        topic_segs = topic.split('/')
        
        for i, pat_seg in enumerate(pattern_segs):
            if pat_seg == '#':
                return True  # # matches everything remaining
            if i >= len(topic_segs):
                return False
            if pat_seg != '+' and pat_seg != topic_segs[i]:
                return False
        
        return len(pattern_segs) == len(topic_segs)


class MQTTConnector:
    """
    MQTT client wrapper for dashboard data feeds.
    
    Provides a simple interface for subscribing to topics
    and routing messages to widget updates.
    
    Can run in connected mode (real MQTT broker) or
    simulated mode (for desktop testing).
    """
    
    def __init__(self, broker_host: str = 'localhost', broker_port: int = 1883,
                 client_id: str = 'dashboard'):
        self._broker_host = broker_host
        self._broker_port = broker_port
        self._client_id = client_id
        self._router = TopicRouter()
        self._connected = False
        self._running = False
        self._thread: Optional[threading.Thread] = None
        
        # Data store — latest values per topic
        self._data: Dict[str, Any] = {}
        self._data_lock = threading.Lock()
    
    def subscribe(self, topic: str, callback: Callable[[MQTTMessage], None] = None) -> None:
        """Subscribe to a topic. If no callback, stores value in data dict."""
        if callback is None:
            callback = lambda msg: self._store_value(msg)
        self._router.subscribe(topic, callback)
    
    def subscribe_json(self, topic: str, key: str = None) -> None:
        """Subscribe and store parsed JSON value under key."""
        def handler(msg: MQTTMessage):
            data = msg.parse_json()
            if data:
                store_key = key or msg.topic.split('/')[-1]
                with self._data_lock:
                    self._data[store_key] = data
        self._router.subscribe(topic, handler)
    
    def get(self, key: str, default=None):
        """Get latest value for a key."""
        with self._data_lock:
            return self._data.get(key, default)
    
    def get_all(self) -> Dict[str, Any]:
        """Get all stored values."""
        with self._data_lock:
            return dict(self._data)
    
    def _store_value(self, msg: MQTTMessage) -> None:
        """Store a message value by topic name."""
        key = msg.topic.split('/')[-1]
        with self._data_lock:
            self._data[key] = msg.payload
    
    def simulate_message(self, topic: str, payload: str) -> None:
        """Simulate an incoming MQTT message (for testing)."""
        msg = MQTTMessage(topic=topic, payload=payload)
        self._router.route(msg)
    
    def simulate_json(self, topic: str, data: dict) -> None:
        """Simulate a JSON MQTT message."""
        self.simulate_message(topic, json.dumps(data))
    
    def connect(self) -> bool:
        """Connect to MQTT broker. Returns True if successful."""
        try:
            # Try paho-mqtt if available
            import paho.mqtt.client as mqtt
            self._client = mqtt.Client(client_id=self._client_id)
            self._client.on_connect = self._on_connect
            self._client.on_message = self._on_message
            self._client.connect(self._broker_host, self._broker_port, 60)
            self._connected = True
            return True
        except ImportError:
            print("[MQTT] paho-mqtt not installed — running in simulated mode")
            return False
        except Exception as e:
            print(f"[MQTT] Connection failed: {e}")
            return False
    
    def _on_connect(self, client, userdata, flags, rc):
        print(f"[MQTT] Connected to {self._broker_host}:{self._broker_port}")
        self._connected = True
    
    def _on_message(self, client, userdata, msg):
        try:
            payload = msg.payload.decode('utf-8')
            mqtt_msg = MQTTMessage(
                topic=msg.topic,
                payload=payload,
                qos=msg.qos
            )
            self._router.route(mqtt_msg)
        except Exception as e:
            print(f"[MQTT] Message processing error: {e}")
    
    def start_loop(self) -> None:
        """Start the MQTT network loop in a background thread."""
        if self._connected and hasattr(self, '_client'):
            self._running = True
            self._client.loop_start()
    
    def stop(self) -> None:
        """Stop the MQTT client."""
        self._running = False
        if hasattr(self, '_client'):
            self._client.loop_stop()
            self._client.disconnect()
        self._connected = False


class RESTPoller:
    """
    Periodic HTTP poller for non-MQTT data sources.
    """
    
    def __init__(self, poll_interval: float = 60.0):
        self._poll_interval = poll_interval
        self._sources: List[dict] = []
        self._data: Dict[str, Any] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None
    
    def add_source(self, name: str, url: str, 
                   parser: Callable = None,
                   interval: float = None) -> None:
        """Add a REST data source."""
        self._sources.append({
            'name': name,
            'url': url,
            'parser': parser or self._default_json_parser,
            'interval': interval or self._poll_interval,
            'last_poll': 0,
        })
    
    def _default_json_parser(self, text: str) -> Any:
        try:
            return json.loads(text)
        except:
            return text
    
    def get(self, name: str, default=None):
        return self._data.get(name, default)
    
    def poll_once(self) -> None:
        """Poll all sources once."""
        import urllib.request
        now = time.time()
        
        for source in self._sources:
            if now - source['last_poll'] < source['interval']:
                continue
            
            try:
                req = urllib.request.Request(source['url'], headers={
                    'User-Agent': 'Dashboard/1.0'
                })
                resp = urllib.request.urlopen(req, timeout=10)
                text = resp.read().decode('utf-8')
                self._data[source['name']] = source['parser'](text)
                source['last_poll'] = now
            except Exception as e:
                print(f"[REST] Poll error for {source['name']}: {e}")
    
    def start(self) -> None:
        """Start polling in background thread."""
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()
    
    def _poll_loop(self) -> None:
        while self._running:
            self.poll_once()
            time.sleep(1)
    
    def stop(self) -> None:
        self._running = False


# --- Test ---

if __name__ == '__main__':
    # Test MQTT connector in simulated mode
    mqtt = MQTTConnector()
    
    # Subscribe to topics
    mqtt.subscribe('home/temperature', lambda msg: print(f"Temp: {msg.payload}"))
    mqtt.subscribe('home/humidity', lambda msg: print(f"Humidity: {msg.payload}"))
    mqtt.subscribe_json('home/sensors/#')
    
    # Simulate messages
    mqtt.simulate_message('home/temperature', '23.5')
    mqtt.simulate_message('home/humidity', '65')
    mqtt.simulate_json('home/sensors/living_room', {'temp': 22.1, 'humidity': 58})
    mqtt.simulate_json('home/sensors/bedroom', {'temp': 20.3, 'humidity': 62})
    
    # Check stored values
    print(f"\nStored values: {mqtt.get_all()}")
    
    # Test topic matching
    router = TopicRouter()
    matched = []
    router.subscribe('home/+/temp', lambda msg: matched.append(msg.topic))
    router.subscribe('home/#', lambda msg: matched.append(f"hash:{msg.topic}"))
    
    router.route(MQTTMessage(topic='home/living_room/temp', payload='22'))
    router.route(MQTTMessage(topic='home/bedroom/temp', payload='20'))
    router.route(MQTTMessage(topic='home/status', payload='ok'))
    router.route(MQTTMessage(topic='home/living_room/humidity', payload='58'))
    
    print(f"\nMatched topics: {matched}")
    assert 'home/living_room/temp' in matched
    assert 'home/bedroom/temp' in matched
    assert 'hash:home/status' in matched
    assert 'hash:home/living_room/humidity' in matched
    
    print("\nMQTT connector test OK")
