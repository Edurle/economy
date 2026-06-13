"""UI panel: population counts, trend chart, season/tick info, event log."""

import pygame
import numpy as np
from collections import deque

from config import (
    PANEL_WIDTH, PANEL_HEIGHT, VIEWPORT_WIDTH,
    SpeciesKind, SPECIES_PARAMS, SEASON_NAMES, Season,
)
from ecs.world import World
from render.minimap import MINI_W, MINI_H, MINI_RIGHT


class UIPanel:
    def __init__(self, font: pygame.font.Font, small_font: pygame.font.Font):
        self.font = font
        self.small_font = small_font
        self.chart_rect = pygame.Rect(8, 250, PANEL_WIDTH - 16, 120)
        self.top_margin = 0

    def render(self, world: World, top_margin: int = 0) -> pygame.Surface:
        surf = pygame.Surface((PANEL_WIDTH, PANEL_HEIGHT))
        surf.fill((30, 30, 35))

        # ---- Top section: two-column layout (minimap on left, stats on right) ----
        x_right = MINI_RIGHT  # content beside minimap starts here
        y = 8

        # Title (right column, beside minimap)
        title = self.font.render("生态系统监控", True, (255, 255, 255))
        surf.blit(title, (x_right, y))
        y += 24

        # Season + tick + speed
        season_name = SEASON_NAMES[Season(world.season)]
        state_str = "暂停" if world.paused else "运行"
        info = f"{season_name}  Tick:{world.tick}  {world.speed}x {state_str}"
        info_surf = self.small_font.render(info, True, (200, 200, 200))
        surf.blit(info_surf, (x_right, y))
        y += 16

        # Population counts (right column, beside minimap)
        header = self.small_font.render("--- 种群 ---", True, (150, 150, 150))
        surf.blit(header, (x_right, y))
        y += 15

        for kind in SpeciesKind:
            params = SPECIES_PARAMS[kind]
            count = world.count_species(kind)
            color = params["color"]
            pygame.draw.rect(surf, color, (x_right, y + 1, 10, 10))
            label = f"{params['name']}:{count}"
            text = self.small_font.render(label, True, (220, 220, 220))
            surf.blit(text, (x_right + 14, y))
            y += 14

        # ---- Below minimap: full-width chart + events ----
        minimap_bottom = 8 + MINI_H + 8
        y = minimap_bottom

        # Trend chart
        chart_title = self.small_font.render("--- 种群趋势 ---", True, (150, 150, 150))
        surf.blit(chart_title, (8, y))
        y += 15
        self.chart_rect = pygame.Rect(8, y, PANEL_WIDTH - 16, 120)
        self._draw_chart(surf, world, y)

        # Event log
        y = self.chart_rect.bottom + 6
        log_title = self.small_font.render("--- 事件日志 ---", True, (150, 150, 150))
        surf.blit(log_title, (8, y))
        y += 15
        recent = list(world.events_log)[-5:]
        for tick, msg in recent:
            log_surf = self.small_font.render(f"[{tick}] {msg}", True, (180, 180, 140))
            surf.blit(log_surf, (8, y))
            y += 15

        return surf

    def _draw_chart(self, surf: pygame.Surface, world: World, y_offset: int) -> None:
        rect = pygame.Rect(8, y_offset, PANEL_WIDTH - 16, 120)
        pygame.draw.rect(surf, (20, 20, 25), rect)
        pygame.draw.rect(surf, (60, 60, 70), rect, 1)

        max_pop = 1
        for kind in SpeciesKind:
            hist = world.population_history[int(kind)]
            if hist:
                max_pop = max(max_pop, max(hist))

        for kind in SpeciesKind:
            hist = world.population_history[int(kind)]
            if len(hist) < 2:
                continue
            color = SPECIES_PARAMS[kind]["color"]
            points = []
            n = len(hist)
            for i, val in enumerate(hist):
                px = rect.x + int(i / max(n - 1, 1) * rect.width)
                py = rect.bottom - int(val / max_pop * rect.height)
                points.append((px, py))
            if len(points) >= 2:
                pygame.draw.lines(surf, color, False, points, 2)
