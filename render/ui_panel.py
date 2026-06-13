"""UI panel: population counts, trend chart, season/tick info, event log."""

import pygame
import numpy as np
from collections import deque

from config import (
    PANEL_WIDTH, PANEL_HEIGHT, VIEWPORT_WIDTH,
    SpeciesKind, SPECIES_PARAMS, SEASON_NAMES, Season,
)
from ecs.world import World


class UIPanel:
    def __init__(self, font: pygame.font.Font, small_font: pygame.font.Font):
        self.font = font
        self.small_font = small_font
        self.chart_rect = pygame.Rect(8, 250, PANEL_WIDTH - 16, 160)
        self.top_margin = 0

    def render(self, world: World, top_margin: int = 0) -> pygame.Surface:
        surf = pygame.Surface((PANEL_WIDTH, PANEL_HEIGHT))
        surf.fill((30, 30, 35))
        self.top_margin = top_margin

        y = 8 + top_margin
        # Title
        title = self.font.render("生态系统监控", True, (255, 255, 255))
        surf.blit(title, (8, y))
        y += 28

        # Season and tick
        season_name = SEASON_NAMES[Season(world.season)]
        info = f"季节: {season_name}  Tick: {world.tick}"
        info_surf = self.small_font.render(info, True, (200, 200, 200))
        surf.blit(info_surf, (8, y))
        y += 18

        speed_text = f"速度: {world.speed}x  {'暂停' if world.paused else '运行'}"
        speed_surf = self.small_font.render(speed_text, True, (180, 180, 180))
        surf.blit(speed_surf, (8, y))
        y += 20

        # Population counts
        header = self.small_font.render("--- 种群数量 ---", True, (150, 150, 150))
        surf.blit(header, (8, y))
        y += 18

        for kind in SpeciesKind:
            params = SPECIES_PARAMS[kind]
            count = world.count_species(kind)
            color = params["color"]
            # Color swatch
            pygame.draw.rect(surf, color, (8, y + 2, 12, 12))
            label = f"{params['name']}: {count}/{params['population_cap']}"
            text = self.small_font.render(label, True, (220, 220, 220))
            surf.blit(text, (26, y))
            y += 18

        # Trend chart
        y += 4
        chart_title = self.small_font.render("--- 种群趋势 ---", True, (150, 150, 150))
        surf.blit(chart_title, (8, y))
        self.chart_rect = pygame.Rect(8, y + 18, PANEL_WIDTH - 16, 160)
        self._draw_chart(surf, world, y + 18)

        # Event log
        y = self.chart_rect.bottom + 8
        log_title = self.small_font.render("--- 事件日志 ---", True, (150, 150, 150))
        surf.blit(log_title, (8, y))
        y += 18
        recent = list(world.events_log)[-6:]
        for tick, msg in recent:
            log_surf = self.small_font.render(f"[{tick}] {msg}", True, (180, 180, 140))
            surf.blit(log_surf, (8, y))
            y += 16

        return surf

    def _draw_chart(self, surf: pygame.Surface, world: World, y_offset: int) -> None:
        rect = pygame.Rect(8, y_offset, PANEL_WIDTH - 16, 160)
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
