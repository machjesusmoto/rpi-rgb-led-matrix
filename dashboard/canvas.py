"""
TAYA-143: IoT RGB Matrix Dashboard — Canvas Abstraction Layer

Hardware-agnostic canvas that can be tested on desktop with framebuffer
simulator. When deployed on Orange Pi, swaps to real hardware backend.
"""

import time
from abc import ABC, abstractmethod
from typing import Tuple, List, Optional
import struct


class CanvasBackend(ABC):
    """Abstract backend for rendering pixels to hardware or simulator."""
    
    @abstractmethod
    def set_pixel(self, x: int, y: int, r: int, g: int, b: int) -> None:
        """Set a single pixel. r/g/b are 0-255."""
        pass
    
    @abstractmethod
    def get_pixel(self, x: int, y: int) -> Tuple[int, int, int]:
        """Get current pixel color."""
        pass
    
    @abstractmethod
    def flush(self) -> None:
        """Push the framebuffer to the display."""
        pass
    
    @abstractmethod
    def clear(self) -> None:
        """Clear the entire display."""
        pass
    
    @abstractmethod
    def width(self) -> int:
        pass
    
    @abstractmethod
    def height(self) -> int:
        pass


class FramebufferBackend(CanvasBackend):
    """In-memory framebuffer — for desktop testing and VFD effect preview."""
    
    def __init__(self, w: int = 128, h: int = 64):
        self._w = w
        self._h = h
        self._buf = bytearray(w * h * 3)  # RGB888
        self._dirty = False
    
    def set_pixel(self, x: int, y: int, r: int, g: int, b: int) -> None:
        if 0 <= x < self._w and 0 <= y < self._h:
            off = (y * self._w + x) * 3
            self._buf[off] = r & 0xFF
            self._buf[off + 1] = g & 0xFF
            self._buf[off + 2] = b & 0xFF
            self._dirty = True
    
    def get_pixel(self, x: int, y: int) -> Tuple[int, int, int]:
        if 0 <= x < self._w and 0 <= y < self._h:
            off = (y * self._w + x) * 3
            return (self._buf[off], self._buf[off + 1], self._buf[off + 2])
        return (0, 0, 0)
    
    def flush(self) -> None:
        self._dirty = False
    
    def clear(self) -> None:
        self._buf[:] = bytearray(self._w * self._h * 3)
        self._dirty = True
    
    def width(self) -> int:
        return self._w
    
    def height(self) -> int:
        return self._h
    
    def to_ppm(self) -> bytes:
        """Export framebuffer as PPM image (for preview/testing)."""
        header = f"P6\n{self._w} {self._h}\n255\n".encode()
        return header + bytes(self._buf)
    
    def to_png_bytes(self) -> bytes:
        """Export as PNG using minimal encoder (no PIL dependency)."""
        # Use PPM as fallback — convert externally if needed
        return self.to_ppm()


class MatrixCanvas:
    """
    High-level drawing canvas for the RGB matrix.
    
    Provides drawing primitives on top of a CanvasBackend.
    Coordinate system: (0,0) = top-left, x increases right, y increases down.
    Colors are (r, g, b) tuples with values 0-255.
    """
    
    def __init__(self, backend: Optional[CanvasBackend] = None, 
                 width: int = 128, height: int = 64):
        self._backend = backend or FramebufferBackend(width, height)
        self._w = self._backend.width()
        self._h = self._backend.height()
    
    @property
    def width(self) -> int:
        return self._w
    
    @property
    def height(self) -> int:
        return self._h
    
    def set_pixel(self, x: int, y: int, r: int, g: int, b: int) -> None:
        self._backend.set_pixel(x, y, r, g, b)
    
    def get_pixel(self, x: int, y: int) -> Tuple[int, int, int]:
        return self._backend.get_pixel(x, y)
    
    def clear(self) -> None:
        self._backend.clear()
    
    def fill(self, r: int, g: int, b: int) -> None:
        for y in range(self._h):
            for x in range(self._w):
                self._backend.set_pixel(x, y, r, g, b)
    
    def flush(self) -> None:
        self._backend.flush()
    
    # --- Drawing primitives ---
    
    def hline(self, x: int, y: int, length: int, r: int, g: int, b: int) -> None:
        for i in range(length):
            self.set_pixel(x + i, y, r, g, b)
    
    def vline(self, x: int, y: int, length: int, r: int, g: int, b: int) -> None:
        for i in range(length):
            self.set_pixel(x, y + i, r, g, b)
    
    def rect(self, x: int, y: int, w: int, h: int, r: int, g: int, b: int) -> None:
        self.hline(x, y, w, r, g, b)
        self.hline(x, y + h - 1, w, r, g, b)
        self.vline(x, y, h, r, g, b)
        self.vline(x + w - 1, y, h, r, g, b)
    
    def fill_rect(self, x: int, y: int, w: int, h: int, r: int, g: int, b: int) -> None:
        for dy in range(h):
            self.hline(x, y + dy, w, r, g, b)
    
    def circle(self, cx: int, cy: int, radius: int, r: int, g: int, b: int) -> None:
        """Midpoint circle algorithm."""
        x = radius
        y = 0
        err = 1 - radius
        while x >= y:
            self.set_pixel(cx + x, cy + y, r, g, b)
            self.set_pixel(cx + y, cy + x, r, g, b)
            self.set_pixel(cx - y, cy + x, r, g, b)
            self.set_pixel(cx - x, cy + y, r, g, b)
            self.set_pixel(cx - x, cy - y, r, g, b)
            self.set_pixel(cx - y, cy - x, r, g, b)
            self.set_pixel(cx + y, cy - x, r, g, b)
            self.set_pixel(cx + x, cy - y, r, g, b)
            y += 1
            if err < 0:
                err += 2 * y + 1
            else:
                x -= 1
                err += 2 * (y - x) + 1
    
    def blit(self, x: int, y: int, pixels: List[List[Tuple[int, int, int]]]) -> None:
        """Copy a 2D pixel array to position (x, y)."""
        for dy, row in enumerate(pixels):
            for dx, color in enumerate(row):
                if color:
                    self.set_pixel(x + dx, y + dy, *color)


# --- Bitmap font (5x7 VFD-style) ---

# Minimal ASCII font starting from space (0x20)
FONT_5X7 = {
    ' ': [0x00, 0x00, 0x00, 0x00, 0x00],
    '!': [0x00, 0x00, 0x5F, 0x00, 0x00],
    '"': [0x00, 0x07, 0x00, 0x07, 0x00],
    '#': [0x14, 0x7F, 0x14, 0x7F, 0x14],
    '$': [0x24, 0x2A, 0x7F, 0x2A, 0x12],
    '%': [0x23, 0x13, 0x08, 0x64, 0x62],
    '&': [0x36, 0x49, 0x55, 0x22, 0x50],
    "'": [0x00, 0x05, 0x03, 0x00, 0x00],
    '(': [0x00, 0x1C, 0x22, 0x41, 0x00],
    ')': [0x00, 0x41, 0x22, 0x1C, 0x00],
    '*': [0x08, 0x2A, 0x1C, 0x2A, 0x08],
    '+': [0x08, 0x08, 0x3E, 0x08, 0x08],
    ',': [0x00, 0x50, 0x30, 0x00, 0x00],
    '-': [0x08, 0x08, 0x08, 0x08, 0x08],
    '.': [0x00, 0x60, 0x60, 0x00, 0x00],
    '/': [0x20, 0x10, 0x08, 0x04, 0x02],
    '0': [0x3E, 0x51, 0x49, 0x45, 0x3E],
    '1': [0x00, 0x42, 0x7F, 0x40, 0x00],
    '2': [0x42, 0x61, 0x51, 0x49, 0x46],
    '3': [0x21, 0x41, 0x45, 0x4B, 0x31],
    '4': [0x18, 0x14, 0x12, 0x7F, 0x10],
    '5': [0x27, 0x45, 0x45, 0x45, 0x39],
    '6': [0x3C, 0x4A, 0x49, 0x49, 0x30],
    '7': [0x01, 0x71, 0x09, 0x05, 0x03],
    '8': [0x36, 0x49, 0x49, 0x49, 0x36],
    '9': [0x06, 0x49, 0x49, 0x29, 0x1E],
    ':': [0x00, 0x36, 0x36, 0x00, 0x00],
    ';': [0x00, 0x56, 0x36, 0x00, 0x00],
    '<': [0x00, 0x08, 0x14, 0x22, 0x41],
    '=': [0x14, 0x14, 0x14, 0x14, 0x14],
    '>': [0x41, 0x22, 0x14, 0x08, 0x00],
    '?': [0x02, 0x01, 0x51, 0x09, 0x06],
    '@': [0x32, 0x49, 0x79, 0x41, 0x3E],
    'A': [0x7E, 0x11, 0x11, 0x11, 0x7E],
    'B': [0x7F, 0x49, 0x49, 0x49, 0x36],
    'C': [0x3E, 0x41, 0x41, 0x41, 0x22],
    'D': [0x7F, 0x41, 0x41, 0x22, 0x1C],
    'E': [0x7F, 0x49, 0x49, 0x49, 0x41],
    'F': [0x7F, 0x09, 0x09, 0x01, 0x01],
    'G': [0x3E, 0x41, 0x41, 0x51, 0x32],
    'H': [0x7F, 0x08, 0x08, 0x08, 0x7F],
    'I': [0x00, 0x41, 0x7F, 0x41, 0x00],
    'J': [0x20, 0x40, 0x41, 0x3F, 0x01],
    'K': [0x7F, 0x08, 0x14, 0x22, 0x41],
    'L': [0x7F, 0x40, 0x40, 0x40, 0x40],
    'M': [0x7F, 0x02, 0x04, 0x02, 0x7F],
    'N': [0x7F, 0x04, 0x08, 0x10, 0x7F],
    'O': [0x3E, 0x41, 0x41, 0x41, 0x3E],
    'P': [0x7F, 0x09, 0x09, 0x09, 0x06],
    'Q': [0x3E, 0x41, 0x51, 0x21, 0x5E],
    'R': [0x7F, 0x09, 0x19, 0x29, 0x46],
    'S': [0x46, 0x49, 0x49, 0x49, 0x31],
    'T': [0x01, 0x01, 0x7F, 0x01, 0x01],
    'U': [0x3F, 0x40, 0x40, 0x40, 0x3F],
    'V': [0x1F, 0x20, 0x40, 0x20, 0x1F],
    'W': [0x7F, 0x20, 0x18, 0x20, 0x7F],
    'X': [0x63, 0x14, 0x08, 0x14, 0x63],
    'Y': [0x03, 0x04, 0x78, 0x04, 0x03],
    'Z': [0x61, 0x51, 0x49, 0x45, 0x43],
    '[': [0x00, 0x00, 0x7F, 0x41, 0x41],
    '\\': [0x02, 0x04, 0x08, 0x10, 0x20],
    ']': [0x41, 0x41, 0x7F, 0x00, 0x00],
    '^': [0x04, 0x02, 0x01, 0x02, 0x04],
    '_': [0x40, 0x40, 0x40, 0x40, 0x40],
    'a': [0x20, 0x54, 0x54, 0x54, 0x78],
    'b': [0x7F, 0x48, 0x44, 0x44, 0x38],
    'c': [0x38, 0x44, 0x44, 0x44, 0x20],
    'd': [0x38, 0x44, 0x44, 0x48, 0x7F],
    'e': [0x38, 0x54, 0x54, 0x54, 0x18],
    'f': [0x08, 0x7E, 0x09, 0x01, 0x02],
    'g': [0x08, 0x14, 0x54, 0x54, 0x3C],
    'h': [0x7F, 0x08, 0x04, 0x04, 0x78],
    'i': [0x00, 0x44, 0x7D, 0x40, 0x00],
    'j': [0x20, 0x40, 0x44, 0x3D, 0x00],
    'k': [0x00, 0x7F, 0x10, 0x28, 0x44],
    'l': [0x00, 0x41, 0x7F, 0x40, 0x00],
    'm': [0x7C, 0x04, 0x18, 0x04, 0x78],
    'n': [0x7C, 0x08, 0x04, 0x04, 0x78],
    'o': [0x38, 0x44, 0x44, 0x44, 0x38],
    'p': [0x7C, 0x14, 0x14, 0x14, 0x08],
    'q': [0x08, 0x14, 0x14, 0x18, 0x7C],
    'r': [0x7C, 0x08, 0x04, 0x04, 0x08],
    's': [0x48, 0x54, 0x54, 0x54, 0x20],
    't': [0x04, 0x3F, 0x44, 0x40, 0x20],
    'u': [0x3C, 0x40, 0x40, 0x20, 0x7C],
    'v': [0x1C, 0x20, 0x40, 0x20, 0x1C],
    'w': [0x3C, 0x40, 0x30, 0x40, 0x3C],
    'x': [0x44, 0x28, 0x10, 0x28, 0x44],
    'y': [0x0C, 0x50, 0x50, 0x50, 0x3C],
    'z': [0x44, 0x64, 0x54, 0x4C, 0x44],
    '{': [0x00, 0x08, 0x36, 0x41, 0x00],
    '|': [0x00, 0x00, 0x7F, 0x00, 0x00],
    '}': [0x00, 0x41, 0x36, 0x08, 0x00],
    '~': [0x08, 0x04, 0x08, 0x10, 0x08],
}


def draw_text(canvas: MatrixCanvas, x: int, y: int, text: str,
              r: int = 255, g: int = 255, b: int = 255,
              scale: int = 1) -> int:
    """
    Draw text on canvas using 5x7 bitmap font.
    Returns the x position after the last character.
    """
    cursor_x = x
    for ch in text.upper():
        glyph = FONT_5X7.get(ch, FONT_5X7.get(' '))
        if glyph is None:
            cursor_x += 6 * scale
            continue
        for col_idx, col_bits in enumerate(glyph):
            for row_idx in range(7):
                if col_bits & (1 << row_idx):
                    for sx in range(scale):
                        for sy in range(scale):
                            canvas.set_pixel(
                                cursor_x + col_idx * scale + sx,
                                y + row_idx * scale + sy,
                                r, g, b
                            )
        cursor_x += 6 * scale
    return cursor_x


def text_width(text: str, scale: int = 1) -> int:
    """Calculate pixel width of text string."""
    return len(text) * 6 * scale


# --- Simple test ---

if __name__ == '__main__':
    canvas = MatrixCanvas(width=128, height=64)
    
    # Draw test pattern
    canvas.fill(0, 0, 0)
    
    # Red border
    canvas.rect(0, 0, 128, 64, 255, 0, 0)
    
    # Green inner rect
    canvas.fill_rect(4, 4, 120, 56, 0, 40, 0)
    
    # Blue circle
    canvas.circle(64, 32, 20, 0, 0, 255)
    
    # White text
    draw_text(canvas, 20, 28, "HELLO", 255, 255, 255)
    
    # Export PPM
    with open('/tmp/matrix_test.ppm', 'wb') as f:
        f.write(canvas._backend.to_ppm())
    
    print("Canvas test OK — 128x64, exported to /tmp/matrix_test.ppm")
    print(f"Font: {len(FONT_5X7)} glyphs defined")
