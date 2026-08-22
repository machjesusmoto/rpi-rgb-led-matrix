"""
TAYA-143: Web Configuration UI

Flask-based web interface for runtime dashboard configuration.
Accessible at http://<host>:8080
"""

import json
import os
import sys
import time
from typing import Optional

# Flask is optional — gracefully degrade if not installed
try:
    from flask import Flask, render_template_string, request, jsonify
    HAS_FLASK = True
except ImportError:
    HAS_FLASK = False

from config import DashboardConfig


DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>TAYA-143 Dashboard Config</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: monospace; background: #1a1a2e; color: #e0e0e0; padding: 20px; }
        h1 { color: #ffb828; margin-bottom: 20px; }
        .section { background: #16213e; border: 1px solid #0f3460; border-radius: 8px; padding: 16px; margin-bottom: 16px; }
        .section h2 { color: #ffb828; font-size: 14px; margin-bottom: 12px; text-transform: uppercase; }
        label { display: block; margin-bottom: 8px; font-size: 12px; color: #a0a0a0; }
        input, select { background: #0f3460; border: 1px solid #1a4080; color: #e0e0e0; padding: 6px 10px; border-radius: 4px; font-family: monospace; font-size: 12px; width: 100%; }
        input[type="range"] { width: 200px; }
        .row { display: flex; gap: 16px; margin-bottom: 8px; flex-wrap: wrap; }
        .row > div { flex: 1; min-width: 200px; }
        button { background: #e94560; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; font-family: monospace; }
        button:hover { background: #ff6b81; }
        .val { color: #ffb828; font-weight: bold; }
        .status { padding: 8px; border-radius: 4px; margin-top: 10px; }
        .ok { background: #1a4020; color: #40ff80; }
        .err { background: #401a1a; color: #ff4040; }
    </style>
</head>
<body>
    <h1>TAYA-143 RGB Matrix Dashboard</h1>

    <div class="section">
        <h2>Display</h2>
        <div class="row">
            <div><label>FPS</label><input type="number" id="fps" value="10" min="1" max="60"></div>
            <div><label>Width</label><input type="number" id="width" value="128" readonly></div>
            <div><label>Height</label><input type="number" id="height" value="64" readonly></div>
        </div>
    </div>

    <div class="section">
        <h2>VFD Emulation</h2>
        <div class="row">
            <div><label>Palette</label>
                <select id="palette">
                    <option value="amber" selected>Amber</option>
                    <option value="green">Green</option>
                    <option value="blue">Blue</option>
                    <option value="white">White</option>
                </select>
            </div>
            <div><label>Scanline <span class="val" id="scanline_val">0.3</span></label>
                <input type="range" id="scanline" min="0" max="1" step="0.05" value="0.3"></div>
            <div><label>Glow Radius <span class="val" id="glow_r_val">1</span></label>
                <input type="range" id="glow_r" min="0" max="5" step="1" value="1"></div>
            <div><label>Glow Strength <span class="val" id="glow_s_val">0.4</span></label>
                <input type="range" id="glow_s" min="0" max="1" step="0.05" value="0.4"></div>
            <div><label>Flicker <span class="val" id="flicker_val">0.05</span></label>
                <input type="range" id="flicker" min="0" max="0.5" step="0.01" value="0.05"></div>
        </div>
    </div>

    <div class="section">
        <h2>MQTT</h2>
        <div class="row">
            <div><label>Broker Host</label><input type="text" id="mqtt_host" value="localhost"></div>
            <div><label>Broker Port</label><input type="number" id="mqtt_port" value="1883"></div>
        </div>
    </div>

    <div class="section">
        <h2>Actions</h2>
        <button onclick="saveConfig()">Save Config</button>
        <button onclick="loadConfig()" style="background:#0f3460">Reload</button>
        <div id="status" class="status ok" style="display:none"></div>
    </div>

    <script>
        function updateSliders() {
            document.querySelectorAll('input[type=range]').forEach(el => {
                const valEl = document.getElementById(el.id + '_val');
                if (valEl) valEl.textContent = el.value;
                el.oninput = () => { if (valEl) valEl.textContent = el.value; };
            });
        }

        async function saveConfig() {
            const cfg = {
                display: { fps: parseInt(document.getElementById('fps').value) },
                vfd: {
                    palette: document.getElementById('palette').value,
                    scanline_strength: parseFloat(document.getElementById('scanline').value),
                    glow_radius: parseInt(document.getElementById('glow_r').value),
                    glow_strength: parseFloat(document.getElementById('glow_s').value),
                    flicker_amount: parseFloat(document.getElementById('flicker').value),
                },
                mqtt: {
                    broker_host: document.getElementById('mqtt_host').value,
                    broker_port: parseInt(document.getElementById('mqtt_port').value),
                }
            };
            const res = await fetch('/api/config', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(cfg)
            });
            const data = await res.json();
            showStatus(data.ok ? 'Saved!' : 'Error: ' + data.error, data.ok);
        }

        async function loadConfig() {
            const res = await fetch('/api/config');
            const cfg = await res.json();
            if (cfg.display) document.getElementById('fps').value = cfg.display.fps || 10;
            if (cfg.vfd) {
                document.getElementById('palette').value = cfg.vfd.palette || 'amber';
                document.getElementById('scanline').value = cfg.vfd.scanline_strength || 0.3;
                document.getElementById('glow_r').value = cfg.vfd.glow_radius || 1;
                document.getElementById('glow_s').value = cfg.vfd.glow_strength || 0.4;
                document.getElementById('flicker').value = cfg.vfd.flicker_amount || 0.05;
            }
            if (cfg.mqtt) {
                document.getElementById('mqtt_host').value = cfg.mqtt.broker_host || 'localhost';
                document.getElementById('mqtt_port').value = cfg.mqtt.broker_port || 1883;
            }
            updateSliders();
            showStatus('Config loaded', true);
        }

        function showStatus(msg, ok) {
            const el = document.getElementById('status');
            el.textContent = msg;
            el.className = 'status ' + (ok ? 'ok' : 'err');
            el.style.display = 'block';
            setTimeout(() => el.style.display = 'none', 3000);
        }

        updateSliders();
        loadConfig();
    </script>
</body>
</html>
"""


class WebUI:
    """Flask web interface for dashboard configuration."""
    
    def __init__(self, config: DashboardConfig, host: str = '0.0.0.0', port: int = 8080):
        self._config = config
        self._host = host
        self._port = port
        self._app: Optional[Flask] = None
    
    def create_app(self) -> Flask:
        app = Flask('dashboard')
        config = self._config
        
        @app.route('/')
        def index():
            return render_template_string(DASHBOARD_HTML)
        
        @app.route('/api/config', methods=['GET'])
        def get_config():
            return jsonify(config.data)
        
        @app.route('/api/config', methods=['POST'])
        def set_config():
            try:
                updates = request.get_json()
                config.update_from_dict(updates)
                config.save()
                return jsonify({'ok': True})
            except Exception as e:
                return jsonify({'ok': False, 'error': str(e)}), 400
        
        @app.route('/api/health')
        def health():
            return jsonify({'status': 'ok', 'version': '0.1.0'})
        
        self._app = app
        return app
    
    def run(self) -> None:
        if not HAS_FLASK:
            print("[WebUI] Flask not installed. Install with: pip install flask")
            return
        
        app = self.create_app()
        print(f"[WebUI] Starting on http://{self._host}:{self._port}")
        app.run(host=self._host, port=self._port, debug=False)
    
    def run_background(self) -> None:
        """Run in background thread."""
        import threading
        if not HAS_FLASK:
            print("[WebUI] Flask not installed")
            return
        
        app = self.create_app()
        thread = threading.Thread(
            target=lambda: app.run(host=self._host, port=self._port, debug=False),
            daemon=True
        )
        thread.start()
        print(f"[WebUI] Background on http://{self._host}:{self._port}")


# --- Test ---

if __name__ == '__main__':
    if not HAS_FLASK:
        print("Flask not installed. Testing without web server.")
        print("Install: pip install flask")
        
        # Test config endpoints manually
        cfg = DashboardConfig()
        webui = WebUI(cfg)
        print("WebUI class OK (Flask not available)")
        sys.exit(0)
    
    cfg = DashboardConfig()
    webui = WebUI(cfg, port=8081)  # Use 8081 for test
    app = webui.create_app()
    
    # Test with Flask test client
    with app.test_client() as client:
        # Health
        r = client.get('/api/health')
        assert r.status_code == 200
        assert r.get_json()['status'] == 'ok'
        print("Health endpoint OK")
        
        # Get config
        r = client.get('/api/config')
        assert r.status_code == 200
        data = r.get_json()
        assert data['display']['width'] == 128
        print("Get config OK")
        
        # Set config
        r = client.post('/api/config', json={'vfd': {'palette': 'green'}})
        assert r.status_code == 200
        assert r.get_json()['ok'] is True
        assert cfg.get('vfd.palette') == 'green'
        print("Set config OK")
        
        # Verify persistence
        r = client.get('/api/config')
        assert r.get_json()['vfd']['palette'] == 'green'
        print("Config persisted OK")
        
        # HTML page
        r = client.get('/')
        assert r.status_code == 200
        assert 'TAYA-143' in r.data.decode()
        print("HTML page OK")
    
    print("\nWebUI test OK")
