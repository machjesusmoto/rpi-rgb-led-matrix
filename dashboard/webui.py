"""
TAYA-143: Web Configuration UI

Flask-based web panel for runtime dashboard configuration.
"""

import json
import os
from typing import Optional

# Flask is optional — degrade gracefully
try:
    from flask import Flask, jsonify, request, send_from_directory
    HAS_FLASK = True
except ImportError:
    HAS_FLASK = False

from config import DashboardConfig, save_config


def create_app(config: DashboardConfig) -> Optional[object]:
    """Create Flask app for the web config UI."""
    if not HAS_FLASK:
        print("Web UI: Flask not installed. Run: pip install flask")
        return None

    app = Flask(__name__, static_folder="web_static")
    app.config["JSON_SORT_KEYS"] = False

    # --- API Routes ---

    @app.route("/api/config")
    def get_config():
        return jsonify(config.to_dict())

    @app.route("/api/config", methods=["PUT"])
    def update_config():
        """Full config replacement."""
        data = request.get_json()
        new_cfg = DashboardConfig.from_dict(data)
        new_cfg.config_path = config.config_path
        # Preserve internal state
        new_cfg._last_modified = config._last_modified
        save_config(new_cfg)
        return jsonify({"status": "ok", "config": new_cfg.to_dict()})

    @app.route("/api/config/<path:section>", methods=["PATCH"])
    def patch_section(section: str):
        """Partial update of a config section."""
        data = request.get_json()
        full = config.to_dict()
        if section in full:
            if isinstance(full[section], dict):
                full[section].update(data)
            else:
                full[section] = data
        else:
            full[section] = data

        new_cfg = DashboardConfig.from_dict(full)
        new_cfg.config_path = config.config_path
        save_config(new_cfg)
        return jsonify({"status": "ok", "section": section, "value": full[section]})

    @app.route("/api/widgets")
    def list_widgets():
        from dataclasses import asdict
        return jsonify([asdict(w) for w in config.widgets])

    @app.route("/api/widgets", methods=["POST"])
    def add_widget():
        from config import WidgetConfig
        data = request.get_json()
        widget = WidgetConfig.from_dict(data)
        config.widgets.append(widget)
        save_config(config)
        return jsonify({"status": "ok", "widget": data})

    @app.route("/api/widgets/<widget_id>", methods=["DELETE"])
    def remove_widget(widget_id: str):
        config.widgets = [w for w in config.widgets if w.id != widget_id]
        save_config(config)
        return jsonify({"status": "ok", "removed": widget_id})

    @app.route("/api/widgets/<widget_id>/data", methods=["POST"])
    def update_widget_data(widget_id: str):
        """Push data to a widget (for testing/external triggers)."""
        data = request.get_json()
        for w in config.widgets:
            if w.id == widget_id:
                return jsonify({"status": "ok", "binding": w.data_binding, "data": data})
        return jsonify({"error": f"Widget {widget_id} not found"}), 404

    @app.route("/api/themes")
    def list_themes():
        themes = {
            "amber": {"primary": [255, 180, 40], "name": "amber"},
            "green": {"primary": [0, 255, 80], "name": "green"},
            "blue": {"primary": [40, 120, 255], "name": "blue"},
            "white": {"primary": [255, 255, 255], "name": "white"},
            "red": {"primary": [255, 40, 40], "name": "red"}
        }
        return jsonify(themes)

    @app.route("/api/themes/<name>", methods=["POST"])
    def set_theme(name: str):
        config.vfd_palette = name
        save_config(config)
        return jsonify({"status": "ok", "palette": name})

    @app.route("/api/data")
    def get_data():
        """Get all current data source values."""
        from datasources import DataManager
        return jsonify({"note": "Data manager must be injected at runtime"})

    @app.route("/api/status")
    def status():
        return jsonify({
            "uptime": "ok",
            "config_path": config.config_path,
            "widget_count": len(config.widgets),
            "vfd_enabled": config.vfd_enabled,
            "palette": config.vfd_palette,
            "display": f"{config.width}x{config.height}",
            "fps": config.fps
        })

    @app.route("/api/health")
    def health():
        return jsonify({"status": "healthy"})

    # --- Frontend ---

    @app.route("/")
    def index():
        static_dir = os.path.join(os.path.dirname(__file__), "web_static")
        if os.path.exists(os.path.join(static_dir, "index.html")):
            return send_from_directory(static_dir, "index.html")
        return jsonify({
            "message": "RGB Matrix Dashboard Config API",
            "version": "1.0.0",
            "endpoints": [
                "GET  /api/config",
                "PUT  /api/config",
                "PATCH /api/config/<section>",
                "GET  /api/widgets",
                "POST /api/widgets",
                "DELETE /api/widgets/<id>",
                "GET  /api/themes",
                "POST /api/themes/<name>",
                "GET  /api/status",
                "GET  /api/health"
            ]
        })

    return app


def run_web_ui(config: DashboardConfig, host: str = "0.0.0.0", port: int = 8080):
    """Start the web UI server."""
    app = create_app(config)
    if app is None:
        return
    print(f"Web UI: http://{host}:{port}")
    app.run(host=host, port=port, debug=False, use_reloader=False)
