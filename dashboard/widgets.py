"""
TAYA-143: Dashboard Widget Framework

Base widget class and common widgets for the RGB matrix dashboard.
Widgets render to a MatrixCanvas and can be composed into layouts.
"""

import time
from abc import ABC, abstractmethod
from typing import Tuple, Optional, List
from canvas import MatrixCanvas, draw_text, text_width


class Widget(ABC):
    """Base widget interface."""
    
    def __init__(self, x: int = 0, y: int = 0, width: int = 0, height: int = 0):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.visible = True
    
    @abstractmethod
    def render(self, canvas: MatrixCanvas) -> None:
        """Render the widget to the canvas."""
        pass
    
    def update(self, data: dict = None) -> None:
        """Update widget state with new data. Override in subclasses."""
        pass
    
    def contains(self, px: int, py: int) -> bool:
        """Check if a point is within the widget bounds."""
        return (self.x <= px < self.x + self.width and
                self.y <= py < self.y + self.height)


class TextWidget(Widget):
    """Simple text display widget."""
    
    def __init__(self, x: int, y: int, text: str = "",
                 color: Tuple[int, int, int] = (255, 255, 255),
                 scale: int = 1, **kwargs):
        super().__init__(x, y, **kwargs)
        self.text = text
        self.color = color
        self.scale = scale
        if self.width == 0:
            self.width = max(1, len(text) * 6 * scale)
        if self.height == 0:
            self.height = 8 * scale
    
    def render(self, canvas: MatrixCanvas) -> None:
        if self.visible and self.text:
            draw_text(canvas, self.x, self.y, self.text,
                     *self.color, scale=self.scale)
    
    def set_text(self, text: str) -> None:
        self.text = text


class ClockWidget(Widget):
    """Digital clock widget with HH:MM format."""
    
    def __init__(self, x: int = 0, y: int = 0,
                 color: Tuple[int, int, int] = (255, 180, 40),
                 scale: int = 2, show_seconds: bool = False,
                 use_24h: bool = True, **kwargs):
        super().__init__(x, y, **kwargs)
        self.color = color
        self.scale = scale
        self.show_seconds = show_seconds
        self.use_24h = use_24h
        self._time_str = "00:00"
        self._colon_visible = True
        self._last_update = 0
        
        # Calculate dimensions
        if show_seconds:
            self.width = 8 * 6 * scale  # HH:MM:SS
        else:
            self.width = 5 * 6 * scale  # HH:MM
        self.height = 8 * scale
    
    def update(self, data: dict = None) -> None:
        now = time.time()
        t = time.localtime(now)
        
        if self.use_24h:
            hour = t.tm_hour
        else:
            hour = t.tm_hour % 12
            if hour == 0:
                hour = 12
        
        # Blink colon every second
        self._colon_visible = (int(now) % 2 == 0)
        
        if self.show_seconds:
            self._time_str = f"{hour:02d}:{t.tm_min:02d}:{t.tm_sec:02d}"
        else:
            self._time_str = f"{hour:02d}:{t.tm_min:02d}"
        
        self._last_update = now
    
    def render(self, canvas: MatrixCanvas) -> None:
        if not self.visible:
            return
        
        # Draw time with blinking colon
        display = self._time_str
        if not self._colon_visible:
            display = display.replace(':', ' ')
        
        draw_text(canvas, self.x, self.y, display,
                 *self.color, scale=self.scale)


class ProgressBarWidget(Widget):
    """Horizontal progress bar widget."""
    
    def __init__(self, x: int, y: int, width: int = 100, height: int = 6,
                 color: Tuple[int, int, int] = (0, 200, 50),
                 bg_color: Tuple[int, int, int] = (10, 10, 10),
                 value: float = 0.0, **kwargs):
        super().__init__(x, y, width, height, **kwargs)
        self.color = color
        self.bg_color = bg_color
        self.value = max(0.0, min(1.0, value))
    
    def update(self, data: dict = None) -> None:
        if data and 'value' in data:
            self.value = max(0.0, min(1.0, data['value']))
    
    def render(self, canvas: MatrixCanvas) -> None:
        if not self.visible:
            return
        
        # Background
        canvas.fill_rect(self.x, self.y, self.width, self.height, *self.bg_color)
        
        # Fill
        fill_width = int(self.width * self.value)
        if fill_width > 0:
            canvas.fill_rect(self.x, self.y, fill_width, self.height, *self.color)


class NotificationWidget(Widget):
    """Scrolling notification/alert widget."""
    
    def __init__(self, x: int, y: int, width: int = 128, height: int = 8,
                 color: Tuple[int, int, int] = (255, 50, 50),
                 speed: float = 30.0, **kwargs):
        super().__init__(x, y, width, height, **kwargs)
        self.color = color
        self.speed = speed  # pixels per second
        self._messages: List[str] = []
        self._current_msg = ""
        self._scroll_x = 0.0
        self._last_time = 0.0
    
    def add_message(self, msg: str) -> None:
        self._messages.append(msg)
        if not self._current_msg:
            self._current_msg = msg
    
    def update(self, data: dict = None) -> None:
        if data and 'message' in data:
            self.add_message(data['message'])
        
        now = time.time()
        if self._last_time == 0:
            self._last_time = now
        
        dt = now - self._last_time
        self._last_time = now
        
        if self._current_msg:
            msg_width = text_width(self._current_msg)
            self._scroll_x -= self.speed * dt
            
            # Reset scroll when message has fully passed
            if self._scroll_x < -msg_width:
                self._scroll_x = self.width
                # Advance to next message
                if self._messages:
                    idx = self._messages.index(self._current_msg) if self._current_msg in self._messages else -1
                    idx = (idx + 1) % len(self._messages)
                    self._current_msg = self._messages[idx]
    
    def render(self, canvas: MatrixCanvas) -> None:
        if not self.visible or not self._current_msg:
            return
        
        # Clip to widget bounds (simple: only draw if within x range)
        msg_width = text_width(self._current_msg)
        start_x = int(self._scroll_x)
        
        # Draw text at scroll position
        draw_text(canvas, start_x, self.y + 1, self._current_msg, *self.color)
        
        # Wrap around if needed
        if start_x < 0:
            draw_text(canvas, start_x + msg_width + 20, self.y + 1,
                     self._current_msg, *self.color)


class Dashboard:
    """
    Dashboard manager — composes widgets and handles rendering loop.
    """
    
    def __init__(self, canvas: MatrixCanvas, fps: float = 10.0):
        self._canvas = canvas
        self._fps = fps
        self._widgets: List[Widget] = []
        self._running = False
    
    def add_widget(self, widget: Widget) -> None:
        self._widgets.append(widget)
    
    def remove_widget(self, widget: Widget) -> None:
        self._widgets.remove(widget)
    
    def update_all(self) -> None:
        """Update all widget states."""
        for w in self._widgets:
            w.update()
    
    def render_all(self) -> None:
        """Render all widgets to canvas."""
        self._canvas.clear()
        for w in self._widgets:
            if w.visible:
                w.render(self._canvas)
        self._canvas.flush()
    
    def frame(self) -> None:
        """Single frame: update + render."""
        self.update_all()
        self.render_all()
    
    def run(self, duration: float = None) -> None:
        """Run the dashboard for a duration (seconds) or indefinitely."""
        import sys
        self._running = True
        start = time.time()
        interval = 1.0 / self._fps
        
        try:
            while self._running:
                self.frame()
                
                if duration and (time.time() - start) >= duration:
                    break
                
                # Sleep to maintain FPS
                elapsed = time.time() - start
                target = (int(elapsed / interval) + 1) * interval
                sleep_time = target - time.time()
                if sleep_time > 0:
                    time.sleep(sleep_time)
        except KeyboardInterrupt:
            pass
        finally:
            self._running = False
    
    def stop(self) -> None:
        self._running = False
    
    def export_frame(self, path: str) -> None:
        """Export current frame as PPM."""
        with open(path, 'wb') as f:
            f.write(self._canvas._backend.to_ppm())


# --- Test ---

if __name__ == '__main__':
    canvas = MatrixCanvas(width=128, height=64)
    dashboard = Dashboard(canvas, fps=10)
    
    # Clock widget (large, centered)
    clock = ClockWidget(x=14, y=4, scale=2, color=(255, 180, 40))
    dashboard.add_widget(clock)
    
    # Status text
    status = TextWidget(x=4, y=24, text="SYS OK", color=(40, 200, 80))
    dashboard.add_widget(status)
    
    # Temperature
    temp = TextWidget(x=80, y=24, text="42.0C", color=(255, 120, 40))
    dashboard.add_widget(temp)
    
    # Progress bar
    bar = ProgressBarWidget(x=4, y=36, width=120, height=6,
                           color=(0, 180, 60), value=0.65)
    dashboard.add_widget(bar)
    
    # Notification
    notif = NotificationWidget(x=0, y=50, width=128, height=8,
                              color=(255, 80, 80))
    notif.add_message(">>> SYSTEM DASHBOARD ONLINE <<<")
    notif.add_message("TAYA-143 IoT RGB Matrix Dashboard")
    dashboard.add_widget(notif)
    
    # Run for 3 seconds and export
    dashboard.run(duration=3.0)
    dashboard.export_frame('/tmp/dashboard_test.ppm')
    print("Dashboard test OK — exported to /tmp/dashboard_test.ppm")
