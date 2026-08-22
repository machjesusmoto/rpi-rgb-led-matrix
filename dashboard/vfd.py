"""
TAYA-143: VFD (Vacuum Fluorescent Display) Emulation Layer

Applies retro VFD aesthetics to a MatrixCanvas:
- Scanline effect (horizontal beam scan)
- Phosphor glow (Gaussian blur on bright pixels)
- Color palette shift (warm amber/green phosphor tones)
- Flicker (subtle brightness oscillation)
- Character persistence (phosphor afterglow)
"""

import math
import time
from typing import Tuple, Optional
from canvas import MatrixCanvas, FramebufferBackend


class VFDPalette:
    """VFD color palettes — warm phosphor tones."""
    
    AMBER = {
        'name': 'amber',
        'bg': (2, 1, 0),
        'dim': (30, 15, 0),
        'mid': (180, 90, 0),
        'bright': (255, 180, 40),
        'glow': (255, 200, 60),
    }
    
    GREEN = {
        'name': 'green',
        'bg': (0, 2, 0),
        'dim': (0, 20, 5),
        'mid': (0, 120, 30),
        'bright': (40, 255, 80),
        'glow': (60, 255, 100),
    }
    
    BLUE = {
        'name': 'blue',
        'bg': (0, 1, 2),
        'dim': (5, 10, 30),
        'mid': (20, 60, 180),
        'bright': (60, 140, 255),
        'glow': (80, 160, 255),
    }
    
    WHITE = {
        'name': 'white',
        'bg': (1, 1, 1),
        'dim': (20, 20, 20),
        'mid': (140, 140, 140),
        'bright': (255, 255, 255),
        'glow': (200, 200, 220),
    }


def map_color_to_vfd(r: int, g: int, b: int, palette: dict) -> Tuple[int, int, int]:
    """Map an RGB color to VFD phosphor palette based on luminance."""
    luminance = (r * 0.299 + g * 0.587 + b * 0.114) / 255.0
    
    if luminance < 0.01:
        return palette['bg']
    elif luminance < 0.3:
        t = luminance / 0.3
        return _lerp_color(palette['dim'], palette['mid'], t)
    elif luminance < 0.7:
        t = (luminance - 0.3) / 0.4
        return _lerp_color(palette['mid'], palette['bright'], t)
    else:
        t = (luminance - 0.7) / 0.3
        return _lerp_color(palette['bright'], palette['glow'], t)


def _lerp_color(a: Tuple[int, int, int], b: Tuple[int, int, int], t: float) -> Tuple[int, int, int]:
    t = max(0.0, min(1.0, t))
    return (
        int(a[0] + (b[0] - a[0]) * t),
        int(a[1] + (b[1] - a[1]) * t),
        int(a[2] + (b[2] - a[2]) * t),
    )


class VFDEmulator:
    """
    VFD emulation filter that wraps a MatrixCanvas.
    
    Applies visual effects to simulate a vacuum fluorescent display:
    - Scanlines: alternating bright/dim rows
    - Phosphor glow: spread light from bright pixels
    - Flicker: subtle per-frame brightness variation
    - Afterglow: pixels fade slowly (persistence)
    """
    
    def __init__(self, canvas: MatrixCanvas, palette: Optional[dict] = None,
                 scanline_strength: float = 0.3,
                 glow_radius: int = 1,
                 glow_strength: float = 0.4,
                 flicker_amount: float = 0.05,
                 afterglow_decay: float = 0.85):
        self._canvas = canvas
        self._palette = palette or VFDPalette.AMBER
        self._w = canvas.width
        self._h = canvas.height
        
        # Effect parameters
        self._scanline_strength = scanline_strength
        self._glow_radius = glow_radius
        self._glow_strength = glow_strength
        self._flicker_amount = flicker_amount
        self._afterglow_decay = afterglow_decay
        
        # Afterglow buffer (previous frame)
        self._afterglow = [[(0, 0, 0)] * self._w for _ in range(self._h)]
        
        # Flicker state
        self._flicker_offset = 0.0
        self._frame_count = 0
    
    def render(self, source_pixels: list = None) -> list:
        """
        Render the VFD effect and return the final pixel buffer.
        
        source_pixels: 2D list of (r,g,b) tuples (from canvas).
                       If None, reads from the canvas backend.
        """
        # Read source pixels
        if source_pixels is None:
            source_pixels = self._read_canvas()
        
        # Apply effects in order
        result = source_pixels
        
        # 1. Afterglow blending
        result = self._apply_afterglow(result)
        
        # 2. VFD palette mapping
        result = self._apply_palette(result)
        
        # 3. Phosphor glow
        result = self._apply_glow(result)
        
        # 4. Scanlines
        result = self._apply_scanlines(result)
        
        # 5. Flicker
        result = self._apply_flicker(result)
        
        # Update afterglow buffer
        self._update_afterglow(source_pixels)
        self._frame_count += 1
        
        return result
    
    def render_to_canvas(self, source_pixels: list = None) -> None:
        """Render VFD effects directly to the canvas backend."""
        result = self.render(source_pixels)
        for y in range(self._h):
            for x in range(self._w):
                r, g, b = result[y][x]
                self._canvas.set_pixel(x, y, r, g, b)
    
    def _read_canvas(self) -> list:
        """Read pixels from the canvas backend."""
        pixels = []
        for y in range(self._h):
            row = []
            for x in range(self._w):
                row.append(self._canvas.get_pixel(x, y))
            pixels.append(row)
        return pixels
    
    def _apply_afterglow(self, pixels: list) -> list:
        """Blend current frame with decaying previous frame."""
        result = []
        for y in range(self._h):
            row = []
            for x in range(self._w):
                curr = pixels[y][x]
                prev = self._afterglow[y][x]
                # Blend: current + decayed previous
                r = max(curr[0], int(prev[0] * self._afterglow_decay))
                g = max(curr[1], int(prev[1] * self._afterglow_decay))
                b = max(curr[2], int(prev[2] * self._afterglow_decay))
                row.append((min(255, r), min(255, g), min(255, b)))
            result.append(row)
        return result
    
    def _apply_palette(self, pixels: list) -> list:
        """Map RGB colors to VFD phosphor palette."""
        result = []
        for y in range(self._h):
            row = []
            for x in range(self._w):
                r, g, b = pixels[y][x]
                row.append(map_color_to_vfd(r, g, b, self._palette))
            result.append(row)
        return result
    
    def _apply_glow(self, pixels: list) -> list:
        """Apply phosphor glow (simple box blur on bright pixels)."""
        if self._glow_radius <= 0:
            return pixels
        
        result = [row[:] for row in pixels]
        radius = self._glow_radius
        
        for y in range(self._h):
            for x in range(self._w):
                r_sum, g_sum, b_sum = 0, 0, 0
                count = 0
                
                for dy in range(-radius, radius + 1):
                    for dx in range(-radius, radius + 1):
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < self._h and 0 <= nx < self._w:
                            pr, pg, pb = pixels[ny][nx]
                            lum = (pr + pg + pb) / 3.0
                            # Only spread glow from bright pixels
                            if lum > 50:
                                r_sum += pr
                                g_sum += pg
                                b_sum += pb
                                count += 1
                
                if count > 0:
                    # Blend original with glow
                    orig = pixels[y][x]
                    glow_r = r_sum // count
                    glow_g = g_sum // count
                    glow_b = b_sum // count
                    s = self._glow_strength
                    result[y][x] = (
                        min(255, int(orig[0] * (1 - s) + glow_r * s)),
                        min(255, int(orig[1] * (1 - s) + glow_g * s)),
                        min(255, int(orig[2] * (1 - s) + glow_b * s)),
                    )
        
        return result
    
    def _apply_scanlines(self, pixels: list) -> list:
        """Apply horizontal scanline effect."""
        result = []
        for y in range(self._h):
            # Odd rows slightly dimmer (scanline gap)
            dim = 1.0 - self._scanline_strength if y % 2 == 1 else 1.0
            row = []
            for x in range(self._w):
                r, g, b = pixels[y][x]
                row.append((
                    min(255, int(r * dim)),
                    min(255, int(g * dim)),
                    min(255, int(b * dim)),
                ))
            result.append(row)
        return result
    
    def _apply_flicker(self, pixels: list) -> list:
        """Apply subtle brightness flicker (60Hz hum simulation)."""
        # Sinusoidal flicker based on frame count
        self._flicker_offset = math.sin(self._frame_count * 0.3) * self._flicker_amount
        factor = 1.0 + self._flicker_offset
        
        result = []
        for y in range(self._h):
            row = []
            for x in range(self._w):
                r, g, b = pixels[y][x]
                row.append((
                    min(255, max(0, int(r * factor))),
                    min(255, max(0, int(g * factor))),
                    min(255, max(0, int(b * factor))),
                ))
            result.append(row)
        return result
    
    def _update_afterglow(self, pixels: list) -> None:
        """Update the afterglow buffer with current frame."""
        for y in range(self._h):
            for x in range(self._w):
                self._afterglow[y][x] = pixels[y][x]
    
    def set_palette(self, palette: dict) -> None:
        self._palette = palette
    
    def set_scanline_strength(self, val: float) -> None:
        self._scanline_strength = max(0.0, min(1.0, val))
    
    def set_glow_radius(self, val: int) -> None:
        self._glow_radius = max(0, val)
    
    def set_flicker_amount(self, val: float) -> None:
        self._flicker_amount = max(0.0, min(0.5, val))


# --- Test ---

if __name__ == '__main__':
    from canvas import draw_text, text_width
    
    canvas = MatrixCanvas(width=128, height=64)
    vfd = VFDEmulator(canvas, palette=VFDPalette.AMBER, glow_radius=1)
    
    # Draw a test scene
    canvas.clear()
    
    # Title bar
    canvas.fill_rect(0, 0, 128, 10, 80, 40, 0)
    draw_text(canvas, 4, 2, "VFD TEST", 255, 200, 60)
    
    # Time display (large)
    draw_text(canvas, 24, 18, "12:34", 255, 180, 40, scale=2)
    
    # Status bar
    canvas.fill_rect(0, 52, 128, 12, 40, 20, 0)
    draw_text(canvas, 4, 54, "SYS OK  42.0C", 200, 120, 20)
    
    # Render VFD effect
    vfd.render_to_canvas()
    
    # Export
    with open('/tmp/vfd_test.ppm', 'wb') as f:
        f.write(canvas._backend.to_ppm())
    
    print("VFD emulation test OK — exported to /tmp/vfd_test.ppm")
    
    # Test multiple palettes
    for name, pal in [('green', VFDPalette.GREEN), ('blue', VFDPalette.BLUE)]:
        canvas.clear()
        canvas.fill_rect(0, 0, 128, 64, 80, 80, 80)
        draw_text(canvas, 10, 26, f"PALETTE", 255, 255, 255)
        draw_text(canvas, 24, 40, name.upper(), 255, 255, 255)
        vfd.set_palette(pal)
        vfd.render_to_canvas()
        with open(f'/tmp/vfd_{name}.ppm', 'wb') as f:
            f.write(canvas._backend.to_ppm())
        print(f"  {name} palette: /tmp/vfd_{name}.ppm")
