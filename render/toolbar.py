"""Toolbar: tool selection buttons + parameter sliders for God Mode."""

import pygame
import numpy as np

from config import (
    PANEL_WIDTH, PANEL_HEIGHT,
    SpeciesKind, SPECIES_PARAMS, TerrainType, TERRAIN_COLORS,
    GRASS_GROWTH_RATE, PLAGUE_TRIGGER_RATIO,
)


# Tool categories
TOOL_NONE = 0
TOOL_PLACE_ANIMAL = 1
TOOL_CHANGE_TERRAIN = 2
TOOL_RAIN = 3
TOOL_FIRE = 4
TOOL_PLAGUE = 5
TOOL_CLEAR = 6
TOOL_PLACE_HUMAN = 7
TOOL_PLACE_CAMP = 8

TOOL_LABELS = {
    TOOL_PLACE_ANIMAL: "放动物",
    TOOL_CHANGE_TERRAIN: "改地形",
    TOOL_RAIN: "降雨",
    TOOL_FIRE: "引火",
    TOOL_PLAGUE: "瘟疫",
    TOOL_CLEAR: "清除",
    TOOL_PLACE_HUMAN: "放人类",
    TOOL_PLACE_CAMP: "放营地",
}

TERRAIN_LABELS = {
    TerrainType.GRASSLAND: "草地",
    TerrainType.FOREST: "森林",
    TerrainType.WATER: "水",
    TerrainType.DESERT: "沙漠",
    TerrainType.MOUNTAIN: "山地",
    TerrainType.SNOW: "雪地",
}


class Toolbar:
    def __init__(self, font: pygame.font.Font, small_font: pygame.font.Font):
        self.font = font
        self.small_font = small_font

        self.current_tool = TOOL_PLACE_ANIMAL
        self.selected_species = SpeciesKind.SHEEP
        self.selected_terrain = TerrainType.GRASSLAND

        # Parameter values
        self.grass_growth = GRASS_GROWTH_RATE
        self.breed_mult = 1.0
        self.lifespan_mult = 1.0
        self.fire_mult = 1.0
        self.plague_threshold = PLAGUE_TRIGGER_RATIO

        self._tool_buttons: list[list] = []      # [rect, tool_id, label]
        self._species_buttons: list[list] = []    # [rect, species_kind]
        self._terrain_buttons: list[list] = []    # [rect, terrain_type]
        self._sliders: list[list] = []            # [rect, name, min, max, getter, setter]

    def render(self, y_start: int) -> pygame.Surface:
        surf = pygame.Surface((PANEL_WIDTH, PANEL_HEIGHT - y_start))
        surf.fill((25, 25, 30))
        y = 4

        # --- Tools ---
        header = self.small_font.render("--- 工具 ---", True, (150, 150, 150))
        surf.blit(header, (8, y))
        y += 20

        self._tool_buttons.clear()
        x = 8
        for tid, label in TOOL_LABELS.items():
            btn_rect = pygame.Rect(x, y, 56, 24)
            color = (80, 120, 80) if self.current_tool == tid else (50, 50, 55)
            pygame.draw.rect(surf, color, btn_rect)
            pygame.draw.rect(surf, (100, 100, 110), btn_rect, 1)
            text = self.small_font.render(label, True, (220, 220, 220))
            surf.blit(text, (x + 4, y + 4))
            self._tool_buttons.append([btn_rect, tid, label])
            x += 62
            if x + 56 > PANEL_WIDTH - 8:
                x = 8
                y += 28
        y += 20

        # --- Species selector (for place animal tool) ---
        if self.current_tool == TOOL_PLACE_ANIMAL:
            header = self.small_font.render("选择物种:", True, (150, 150, 150))
            surf.blit(header, (8, y))
            y += 22
            self._species_buttons.clear()
            x = 8
            for kind in SpeciesKind:
                params = SPECIES_PARAMS[kind]
                btn_rect = pygame.Rect(x, y, 56, 26)
                selected = self.selected_species == kind
                color = params["color"] if selected else (50, 50, 55)
                pygame.draw.rect(surf, color, btn_rect)
                pygame.draw.rect(surf, (100, 100, 110), btn_rect, 1)
                text = self.small_font.render(params["name"], True, (20, 20, 20) if selected else (220, 220, 220))
                surf.blit(text, (x + 4, y + 5))
                self._species_buttons.append([btn_rect, kind])
                x += 62
                if x + 56 > PANEL_WIDTH - 8:
                    x = 8
                    y += 30
            y += 20

        # --- Terrain selector (for change terrain tool) ---
        if self.current_tool == TOOL_CHANGE_TERRAIN:
            header = self.small_font.render("选择地形:", True, (150, 150, 150))
            surf.blit(header, (8, y))
            y += 22
            self._terrain_buttons.clear()
            x = 8
            for t_val in TerrainType:
                btn_rect = pygame.Rect(x, y, 56, 26)
                selected = self.selected_terrain == t_val
                color = TERRAIN_COLORS[t_val] if selected else (50, 50, 55)
                pygame.draw.rect(surf, color, btn_rect)
                pygame.draw.rect(surf, (100, 100, 110), btn_rect, 1)
                label = TERRAIN_LABELS[t_val]
                text_color = (20, 20, 20) if selected else (220, 220, 220)
                text = self.small_font.render(label, True, text_color)
                surf.blit(text, (x + 4, y + 5))
                self._terrain_buttons.append([btn_rect, t_val])
                x += 62
                if x + 56 > PANEL_WIDTH - 8:
                    x = 8
                    y += 30
            y += 20

        # --- Sliders ---
        header = self.small_font.render("--- 全局参数 ---", True, (150, 150, 150))
        surf.blit(header, (8, y))
        y += 20

        self._sliders.clear()
        sliders_def = [
            ("草生长率", 0, 5, lambda: self.grass_growth, lambda v: setattr(self, 'grass_growth', v)),
            ("繁殖倍率", 0, 3, lambda: self.breed_mult, lambda v: setattr(self, 'breed_mult', v)),
            ("寿命倍率", 0.5, 3, lambda: self.lifespan_mult, lambda v: setattr(self, 'lifespan_mult', v)),
            ("火灾倍率", 0, 5, lambda: self.fire_mult, lambda v: setattr(self, 'fire_mult', v)),
            ("瘟疫阈值", 0.5, 1.0, lambda: self.plague_threshold, lambda v: setattr(self, 'plague_threshold', v)),
        ]
        for name, vmin, vmax, getter, setter in sliders_def:
            label = self.small_font.render(f"{name}: {getter():.1f}", True, (180, 180, 180))
            surf.blit(label, (8, y))
            y += 16
            track = pygame.Rect(8, y, PANEL_WIDTH - 16, 8)
            pygame.draw.rect(surf, (40, 40, 45), track)
            ratio = (getter() - vmin) / (vmax - vmin)
            fill = pygame.Rect(8, y, int(track.width * ratio), 8)
            pygame.draw.rect(surf, (80, 140, 80), fill)
            knob_x = 8 + int(track.width * ratio)
            pygame.draw.circle(surf, (200, 200, 200), (knob_x, y + 4), 6)
            self._sliders.append([track, name, vmin, vmax, getter, setter])
            y += 18

        return surf, y_start

    def handle_click(self, mx: int, my: int, panel_y_offset: int) -> bool:
        """Handle a click within the panel area. Returns True if consumed."""
        # Adjust y for panel offset
        local_y = my - panel_y_offset
        if local_y < 0:
            return False

        # Tool buttons
        for rect, tid, label in self._tool_buttons:
            if rect.collidepoint(mx, local_y):
                self.current_tool = tid
                return True

        # Species buttons
        for rect, kind in self._species_buttons:
            if rect.collidepoint(mx, local_y):
                self.selected_species = kind
                return True

        # Terrain buttons
        for rect, t_val in self._terrain_buttons:
            if rect.collidepoint(mx, local_y):
                self.selected_terrain = t_val
                return True

        # Sliders
        for track, name, vmin, vmax, getter, setter in self._sliders:
            expanded = track.inflate(0, 16)
            if expanded.collidepoint(mx, local_y):
                ratio = (mx - track.x) / max(track.width, 1)
                ratio = max(0, min(1, ratio))
                setter(vmin + ratio * (vmax - vmin))
                return True

        return False

    def handle_drag_slider(self, mx: int, my: int, panel_y_offset: int) -> None:
        """Drag a slider knob."""
        local_y = my - panel_y_offset
        for track, name, vmin, vmax, getter, setter in self._sliders:
            expanded = track.inflate(0, 20)
            if expanded.collidepoint(mx, local_y):
                ratio = (mx - track.x) / max(track.width, 1)
                ratio = max(0, min(1, ratio))
                setter(vmin + ratio * (vmax - vmin))
