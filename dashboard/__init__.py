"""
TAYA-143: IoT RGB Matrix Dashboard
"""

from .canvas import MatrixCanvas, FramebufferBackend, draw_text, text_width
from .vfd import VFDEmulator, VFDPalette
from .widgets import Dashboard, ClockWidget, TextWidget, ProgressBarWidget, NotificationWidget
from .config import DashboardConfig
from .mqtt_connector import MQTTConnector, RESTPoller, MQTTMessage
