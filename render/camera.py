"""Camera system: viewport panning, zoom, and coordinate transforms."""

import pygame
import numpy as np

from config import (
    GRID_W, GRID_H, TILE_SIZE,
    VIEWPORT_WIDTH, VIEWPORT_HEIGHT,
    CAMERA_PAN_SPEED, CAMERA_MIN_ZOOM, CAMERA_MAX_ZOOM,
)


class Camera:
    """Manages a scrollable, zoomable viewport over the tile world.

    Internal state:
      offset_x, offset_y : top-left of viewport in world-pixel space (float)
      zoom               : multiplier on TILE_SIZE (1.0 = native)
    """

    def __init__(self):
        self.world_pw = GRID_W * TILE_SIZE   # world pixel width
        self.world_ph = GRID_H * TILE_SIZE   # world pixel height
        self.zoom = 1.0
        self._target_offset = np.array([0.0, 0.0], dtype=np.float64)
        self.offset = np.array([0.0, 0.0], dtype=np.float64)

        # Centre camera on world initially
        self._centre_on_world()
        self._target_offset[:] = self.offset

        # Smooth pan velocity (for keyboard / drag)
        self._velocity = np.array([0.0, 0.0], dtype=np.float64)

    # ----------------------------------------------------------------
    # Public transforms
    # ----------------------------------------------------------------
    def world_to_screen(self, gx: float, gy: float) -> tuple[int, int]:
        """Convert grid coords (float) to screen pixel coords."""
        wx = gx * TILE_SIZE
        wy = gy * TILE_SIZE
        sx = (wx - self.offset[0]) * self.zoom
        sy = (wy - self.offset[1]) * self.zoom
        return int(sx), int(sy)

    def screen_to_grid(self, sx: int, sy: int) -> tuple[int, int]:
        """Convert screen pixel coords to integer grid coords."""
        wx = sx / self.zoom + self.offset[0]
        wy = sy / self.zoom + self.offset[1]
        return int(wx // TILE_SIZE), int(wy // TILE_SIZE)

    def screen_to_world_float(self, sx: float, sy: float) -> tuple[float, float]:
        """Convert screen pixels to world-pixel floats."""
        wx = sx / self.zoom + self.offset[0]
        wy = sy / self.zoom + self.offset[1]
        return wx, wy

    @property
    def visible_tiles(self) -> tuple[int, int, int, int]:
        """Return (x0, y0, x1, y1) — inclusive tile range visible in viewport."""
        x0 = max(0, int(self.offset[0] / TILE_SIZE))
        y0 = max(0, int(self.offset[1] / TILE_SIZE))
        vis_w = VIEWPORT_WIDTH / self.zoom
        vis_h = VIEWPORT_HEIGHT / self.zoom
        x1 = min(GRID_W, int((self.offset[0] + vis_w) / TILE_SIZE) + 1)
        y1 = min(GRID_H, int((self.offset[1] + vis_h) / TILE_SIZE) + 1)
        return x0, y0, x1, y1

    @property
    def tile_pixel_size(self) -> float:
        """Size of one tile on screen in pixels."""
        return TILE_SIZE * self.zoom

    @property
    def viewport_rect(self) -> pygame.Rect:
        return pygame.Rect(0, 0, VIEWPORT_WIDTH, VIEWPORT_HEIGHT)

    # ----------------------------------------------------------------
    # Movement
    # ----------------------------------------------------------------
    def pan_direction(self, dx: float, dy: float, dt: float) -> None:
        """Pan camera by a direction vector (normalised) * speed * dt."""
        self._target_offset[0] += dx * CAMERA_PAN_SPEED * dt / self.zoom
        self._target_offset[1] += dy * CAMERA_PAN_SPEED * dt / self.zoom
        self._clamp()

    def pan_pixels(self, dx: float, dy: float) -> None:
        """Pan by raw world-pixel delta (e.g. from mouse drag)."""
        self._target_offset[0] -= dx / self.zoom
        self._target_offset[1] -= dy / self.zoom
        self._clamp()

    def zoom_at(self, screen_x: int, screen_y: int, factor: float) -> None:
        """Zoom by *factor* while keeping the world point under (screen_x, screen_y) fixed."""
        # World point under cursor before zoom
        wx_before = screen_x / self.zoom + self.offset[0]
        wy_before = screen_y / self.zoom + self.offset[1]

        new_zoom = self.zoom * factor
        new_zoom = max(CAMERA_MIN_ZOOM, min(CAMERA_MAX_ZOOM, new_zoom))
        if abs(new_zoom - self.zoom) < 1e-6:
            return

        self.zoom = new_zoom

        # Adjust offset to keep cursor world point fixed
        self.offset[0] = wx_before - screen_x / self.zoom
        self.offset[1] = wy_before - screen_y / self.zoom
        self._target_offset[:] = self.offset
        self._clamp()

    def centre_on(self, gx: float, gy: float) -> None:
        """Centre the camera on grid coords (gx, gy)."""
        wx = gx * TILE_SIZE
        wy = gy * TILE_SIZE
        vis_w = VIEWPORT_WIDTH / self.zoom
        vis_h = VIEWPORT_HEIGHT / self.zoom
        self._target_offset[0] = wx - vis_w / 2
        self._target_offset[1] = wy - vis_h / 2
        self._clamp()

    def update(self, dt: float) -> None:
        """Smoothly lerp offset toward target each frame."""
        rate = 1.0 - (0.001 ** dt)   # frame-rate independent lerp
        self.offset += (self._target_offset - self.offset) * rate

    # ----------------------------------------------------------------
    # Internals
    # ----------------------------------------------------------------
    def _clamp(self) -> None:
        """Clamp offset so the camera doesn't show beyond world edges."""
        vis_w = VIEWPORT_WIDTH / self.zoom
        vis_h = VIEWPORT_HEIGHT / self.zoom

        if vis_w >= self.world_pw:
            self._target_offset[0] = (self.world_pw - vis_w) / 2
        else:
            self._target_offset[0] = max(0, min(self.world_pw - vis_w, self._target_offset[0]))

        if vis_h >= self.world_ph:
            self._target_offset[1] = (self.world_ph - vis_h) / 2
        else:
            self._target_offset[1] = max(0, min(self.world_ph - vis_h, self._target_offset[1]))

    def _centre_on_world(self) -> None:
        vis_w = VIEWPORT_WIDTH / self.zoom
        vis_h = VIEWPORT_HEIGHT / self.zoom
        self.offset[0] = (self.world_pw - vis_w) / 2
        self.offset[1] = (self.world_ph - vis_h) / 2
        self._clamp()
