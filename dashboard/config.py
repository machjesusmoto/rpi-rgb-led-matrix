"""
TAYA-143: Dashboard Configuration System

JSON-based configuration for themes, widgets, and data sources.
Supports hot-reload and runtime reconfiguration.
"""

import json
import os
import time
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field, asdict


DEFAULT_CONFIG = {
    "version": 1,
    "display": {
        "width": 128,
        "height": 64,
        "fps": 10,
    },
    "vfd": {
        "enabled": True,
        "palette": "amber",
        "scanline_strength": 0.3,
        "glow_radius": 1,
        "glow_strength": 0.4,
        "flicker_amount": 0.05,
        "afterglow_decay": 0.85,
    },
    "widgets": [
        {
            "type": "clock",
            "x": 14, "y": 4,
            "scale": 2,
            "color": [255, 180, 40],
            "show_seconds": False,
            "use_24h": True,
        },
        {
            "type": "text",
            "id": "status",
            "x": 4, "y": 24,
            "text": "SYS OK",
            "color": [40, 200, 80],
        },
        {
            "type": "text",
            "id": "temp",
            "x": 80, "y": 24,
            "text": "--.-C",
            "color": [255, 120, 40],
        },
        {
            "type": "progress",
            "id": "cpu",
            "x": 4, "y": 36,
            "width": 120, "height": 6,
            "color": [0, 180, 60],
            "value": 0.5,
        },
        {
            "type": "notification",
            "x": 0, "y": 50,
            "width": 128, "height": 8,
            "color": [255, 80, 80],
            "messages": ["TAYA-143 IoT RGB Matrix Dashboard v0.1"],
        },
    ],
    "mqtt": {
        "broker_host": "localhost",
        "broker_port": 1883,
        "topics": {
            "temperature": "home/temperature",
            "humidity": "home/humidity",
            "notifications": "home/notifications",
        },
    },
    "web_ui": {
        "enabled": True,
        "host": "0.0.0.0",
        "port": 8080,
    },
}


class DashboardConfig:
    """
    Manages dashboard configuration with hot-reload support.
    """
    
    def __init__(self, config_path: str = None):
        self._path = config_path
        self._data: Dict[str, Any] = {}
        self._last_modified: float = 0
        self._callbacks: List[callable] = []
        
        if config_path and os.path.exists(config_path):
            self.load(config_path)
        else:
            self._data = DEFAULT_CONFIG.copy()
    
    def load(self, path: str = None) -> None:
        """Load config from JSON file."""
        path = path or self._path
        if not path:
            return
        
        try:
            with open(path, 'r') as f:
                self._data = json.load(f)
            self._last_modified = os.path.getmtime(path)
            self._path = path
            self._notify_callbacks()
        except Exception as e:
            print(f"[Config] Load error: {e}")
    
    def save(self, path: str = None) -> None:
        """Save config to JSON file."""
        path = path or self._path
        if not path:
            return
        
        os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
        with open(path, 'w') as f:
            json.dump(self._data, f, indent=2)
        self._last_modified = os.path.getmtime(path)
    
    def check_reload(self) -> bool:
        """Check if file changed and reload if needed. Returns True if reloaded."""
        if not self._path or not os.path.exists(self._path):
            return False
        
        mtime = os.path.getmtime(self._path)
        if mtime > self._last_modified:
            self.load()
            return True
        return False
    
    def get(self, key: str, default=None) -> Any:
        """Get a config value using dot notation (e.g. 'vfd.palette')."""
        keys = key.split('.')
        val = self._data
        for k in keys:
            if isinstance(val, dict) and k in val:
                val = val[k]
            else:
                return default
        return val
    
    def set(self, key: str, value: Any) -> None:
        """Set a config value using dot notation."""
        keys = key.split('.')
        d = self._data
        for k in keys[:-1]:
            if k not in d or not isinstance(d[k], dict):
                d[k] = {}
            d = d[k]
        d[keys[-1]] = value
        self._notify_callbacks()
    
    def on_change(self, callback: callable) -> None:
        """Register a callback for config changes."""
        self._callbacks.append(callback)
    
    def _notify_callbacks(self) -> None:
        for cb in self._callbacks:
            try:
                cb(self._data)
            except Exception as e:
                print(f"[Config] Callback error: {e}")
    
    @property
    def data(self) -> Dict[str, Any]:
        return self._data
    
    def to_json(self) -> str:
        return json.dumps(self._data, indent=2)
    
    def update_from_dict(self, updates: Dict[str, Any]) -> None:
        """Deep merge updates into config."""
        def merge(base, override):
            for k, v in override.items():
                if isinstance(v, dict) and isinstance(base.get(k), dict):
                    merge(base[k], v)
                else:
                    base[k] = v
        merge(self._data, updates)
        self._notify_callbacks()


# --- Test ---

if __name__ == '__main__':
    import tempfile
    
    # Test default config
    cfg = DashboardConfig()
    assert cfg.get('display.width') == 128
    assert cfg.get('vfd.palette') == 'amber'
    assert len(cfg.get('widgets')) == 5
    print("Default config OK")
    
    # Test save/load
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        tmppath = f.name
    
    cfg._path = tmppath
    cfg.save()
    
    cfg2 = DashboardConfig(tmppath)
    assert cfg2.get('display.width') == 128
    assert cfg2.get('vfd.palette') == 'amber'
    print("Save/load OK")
    
    # Test set/get
    cfg.set('vfd.palette', 'green')
    assert cfg.get('vfd.palette') == 'green'
    cfg.set('widgets.0.color', [0, 255, 0])
    assert cfg.get('widgets.0.color') == [0, 255, 0]
    print("Set/get OK")
    
    # Test callback
    changed = []
    cfg.on_change(lambda d: changed.append(True))
    cfg.set('test.key', 'value')
    assert len(changed) == 1
    print("Callback OK")
    
    # Test update_from_dict
    cfg.update_from_dict({'vfd': {'glow_radius': 3}})
    assert cfg.get('vfd.glow_radius') == 3
    assert cfg.get('vfd.palette') == 'green'  # preserved
    print("Deep merge OK")
    
    os.unlink(tmppath)
    print("\nConfig system test OK")
