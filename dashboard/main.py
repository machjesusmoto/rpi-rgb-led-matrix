"""
TAYA-143: IoT RGB Matrix Dashboard — Main Entry Point

Ties together canvas, VFD emulation, widgets, config, data sources, and web UI.
On Orange Pi: uses hardware backend. On desktop: uses framebuffer + PPM export.
"""

import sys
import time
import json
import os
import threading
from canvas import MatrixCanvas, FramebufferBackend, draw_text
from vfd import VFDEmulator, VFDPalette
from widgets import (Dashboard, ClockWidget, TextWidget,
                     ProgressBarWidget, NotificationWidget)
from config import load_config, ConfigWatcher, DashboardConfig
from datasources import MQTTDataSource, RESTDataSource, StaticDataSource, DataManager


def create_widget_from_config(w_cfg) -> object:
    """Create a widget instance from WidgetConfig."""
    from config import WidgetConfig
    color = tuple(w_cfg.color) if w_cfg.color else (255, 255, 255)

    wtype = w_cfg.type.lower()
    if wtype == 'clock':
        return ClockWidget(x=w_cfg.x, y=w_cfg.y, color=color,
                           scale=w_cfg.scale, show_seconds=w_cfg.show_seconds,
                           use_24h=w_cfg.use_24h)
    elif wtype == 'text':
        return TextWidget(x=w_cfg.x, y=w_cfg.y, text=w_cfg.text,
                          color=color, scale=w_cfg.scale)
    elif wtype == 'progress':
        bg = tuple(w_cfg.bg_color) if w_cfg.bg_color else (10, 10, 10)
        return ProgressBarWidget(x=w_cfg.x, y=w_cfg.y,
                                 width=w_cfg.width, height=w_cfg.height,
                                 color=color, bg_color=bg, value=w_cfg.value)
    elif wtype == 'notification':
        return NotificationWidget(x=w_cfg.x, y=w_cfg.y,
                                  width=w_cfg.width, height=w_cfg.height,
                                  color=color, speed=w_cfg.speed)
    else:
        return TextWidget(x=w_cfg.x, y=w_cfg.y, text=f"[{wtype}]", color=color)


def create_dashboard(cfg: DashboardConfig) -> tuple:
    """Create dashboard from config."""
    canvas = MatrixCanvas(width=cfg.width, height=cfg.height)

    # VFD emulation
    vfd = None
    if cfg.vfd_enabled:
        palettes = {
            'amber': VFDPalette.AMBER,
            'green': VFDPalette.GREEN,
            'blue': VFDPalette.BLUE,
            'white': VFDPalette.WHITE,
        }
        palette = palettes.get(cfg.vfd_palette, VFDPalette.AMBER)
        vfd = VFDEmulator(canvas, palette=palette,
                          glow_radius=cfg.vfd_glow_radius)

    # Dashboard
    dashboard = Dashboard(canvas, fps=cfg.fps)

    # Create widgets from config
    for w_cfg in cfg.widgets:
        widget = create_widget_from_config(w_cfg)
        dashboard.add_widget(widget)

    return dashboard, canvas, vfd, cfg


def create_data_manager(cfg: DashboardConfig) -> DataManager:
    """Create data sources from config."""
    dm = DataManager()

    # Static values (lowest priority)
    static_source = StaticDataSource(cfg.data_sources.static_values)
    dm.add_source(static_source, priority=0)

    # REST endpoints
    if cfg.data_sources.rest_enabled and cfg.data_sources.rest_endpoints:
        rest = RESTDataSource(cfg.data_sources.rest_endpoints)
        rest.start()
        dm.add_source(rest, priority=1)

    # MQTT (highest priority)
    if cfg.data_sources.mqtt_enabled:
        mqtt = MQTTDataSource(
            broker=cfg.data_sources.mqtt_broker,
            port=cfg.data_sources.mqtt_port,
            topics=cfg.data_sources.mqtt_topics
        )
        mqtt.connect()
        dm.add_source(mqtt, priority=2)

    return dm


def update_widget_data(widget, data_mgr: DataManager):
    """Push data from DataManager to a widget via its data_binding."""
    if hasattr(widget, 'data_binding') and widget.data_binding:
        val = data_mgr.get(widget.data_binding)
        if val is not None:
            if isinstance(widget, TextWidget):
                if isinstance(val, (int, float)):
                    widget.set_text(f"{val}")
                else:
                    widget.set_text(str(val))
            elif isinstance(widget, ProgressBarWidget):
                if isinstance(val, (int, float)):
                    widget.update({'value': float(val) / 100.0})
            elif isinstance(widget, NotificationWidget):
                widget.update({'message': str(val)})


def run_demo(duration: float = 5.0, export_path: str = '/tmp/dashboard_final.ppm',
             config_path: str = None):
    """Run dashboard demo and export final frame."""
    cfg = load_config(config_path)
    dashboard, canvas, vfd, cfg = create_dashboard(cfg)
    data_mgr = create_data_manager(cfg)

    start = time.time()
    try:
        while (time.time() - start) < duration:
            dashboard.frame()

            # Update widgets from data sources
            for widget in dashboard._widgets:
                update_widget_data(widget, data_mgr)

            if vfd:
                vfd.render_to_canvas()

            elapsed = time.time() - start
            if int(elapsed) > int(elapsed - 0.1):
                dashboard.export_frame(f'/tmp/dashboard_t{int(elapsed)}.ppm')

            time.sleep(1.0 / cfg.fps)
    except KeyboardInterrupt:
        pass

    dashboard.export_frame(export_path)
    print(f"Dashboard demo complete — {duration}s, exported to {export_path}")


def run_interactive(config_path: str = None):
    """Interactive mode — reads data from MQTT/REST, renders, and runs web UI."""
    cfg = load_config(config_path)
    dashboard, canvas, vfd, cfg = create_dashboard(cfg)
    data_mgr = create_data_manager(cfg)

    # Start config watcher
    def on_reload(new_cfg):
        nonlocal cfg, dashboard, vfd
        cfg = new_cfg
        dashboard, canvas, vfd, cfg = create_dashboard(new_cfg)
        print("Config reloaded.")

    watcher = ConfigWatcher(cfg, on_reload=on_reload)
    watcher.start()

    # Start web UI in a thread if enabled
    web_thread = None
    if cfg.web_ui_enabled:
        try:
            from webui import run_web_ui
            web_thread = threading.Thread(
                target=run_web_ui,
                args=(cfg, cfg.web_ui_host, cfg.web_ui_port),
                daemon=True
            )
            web_thread.start()
        except ImportError:
            print("Web UI: Flask not available")

    print(f"Dashboard running at {cfg.fps} FPS ({cfg.width}x{cfg.height})...")
    if cfg.web_ui_enabled:
        print(f"Web UI: http://{cfg.web_ui_host}:{cfg.web_ui_port}")
    print("Ctrl+C to stop.")

    try:
        while True:
            dashboard.frame()

            # Update widgets from data sources
            for widget in dashboard._widgets:
                update_widget_data(widget, data_mgr)

            if vfd:
                vfd.render_to_canvas()

            time.sleep(1.0 / cfg.fps)
    except KeyboardInterrupt:
        pass
    finally:
        watcher.stop()
        print("\nStopped.")


if __name__ == '__main__':
    config_path = None
    args = sys.argv[1:]

    # Parse args
    if '--config' in args:
        idx = args.index('--config')
        if idx + 1 < len(args):
            config_path = args[idx + 1]

    if '--interactive' in args or '--web' in args:
        run_interactive(config_path)
    elif '--demo' in args:
        duration = 5.0
        for a in args:
            try:
                duration = float(a)
            except ValueError:
                pass
        run_demo(duration=duration, config_path=config_path)
    else:
        # Default: demo mode
        duration = float(sys.argv[1]) if len(sys.argv) > 1 and not sys.argv[1].startswith('--') else 5.0
        run_demo(duration=duration, config_path=config_path)