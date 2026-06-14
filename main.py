"""Ecosystem simulation main entry point — tile/sprite/camera edition."""

import sys
import os
import numpy as np
import pygame

from config import (
    WINDOW_WIDTH, WINDOW_HEIGHT,
    VIEWPORT_WIDTH, VIEWPORT_HEIGHT, PANEL_WIDTH, PANEL_HEIGHT,
    STATUS_BAR_HEIGHT, FPS,
    TerrainType, SpeciesKind, Season, SEASON_NAMES,
    SPECIES_PARAMS, GRASS_GROWTH_RATE, GRID_W, GRID_H, TILE_SIZE,
)
from ecs.world import World
from world_gen import generate_terrain, populate_initial
from systems.season import SeasonSystem
from systems.weather import WeatherSystem
from systems.grass import GrassSystem
from systems.fire import FireSystem
from systems.plague import PlagueSystem
from systems.ai import AISystem
from systems.human_ai import HumanAISystem
from systems.movement import MovementSystem
from systems.foraging import ForagingSystem
from systems.predation import PredationSystem
from systems.hydration import HydrationSystem
from systems.reproduction import ReproductionSystem
from systems.aging import AgingSystem
from systems.cleanup import CleanupSystem
from systems.gathering import GatheringSystem
from systems.building import BuildingSystem
from systems.research import ResearchSystem
from systems.crafting import CraftingSystem
from render.camera import Camera
from render.assets import generate_assets
from render.map_renderer import TileMapRenderer
from render.minimap import Minimap, MINI_W, MINI_H
from render.ui_panel import UIPanel
from render.toolbar import Toolbar
from input.god_mode import GodMode
from resources import TECH_TREE, RECIPE_REGISTRY, RESOURCE_REGISTRY, all_refined, res_name


PANEL_X = VIEWPORT_WIDTH
TAB_HEIGHT = 28
MINIMAP_Y = TAB_HEIGHT + 8
MINIMAP_X = PANEL_X + 8
PANEL_CONTENT_OFFSET = 0
TOOLBAR_Y = PANEL_HEIGHT - 280


class Simulation:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("生态模拟 - Ecosystem Simulation")
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.clock = pygame.time.Clock()

        # Fonts
        font_path = os.path.join(os.path.dirname(__file__), "fonts", "noto_sc.otf")
        if os.path.exists(font_path):
            self.font = pygame.font.Font(font_path, 20)
            self.small_font = pygame.font.Font(font_path, 15)
        else:
            self.font = pygame.font.SysFont("Arial", 20)
            self.small_font = pygame.font.SysFont("Arial", 15)

        # World
        self.world = World()
        generate_terrain(self.world, seed=np.random.randint(0, 99999))
        populate_initial(self.world)

        # Systems
        self.season_sys = SeasonSystem()
        self.weather_sys = WeatherSystem()
        self.grass_sys = GrassSystem()
        self.fire_sys = FireSystem()
        self.plague_sys = PlagueSystem()
        self.ai_sys = AISystem()
        self.human_ai_sys = HumanAISystem()
        self.movement_sys = MovementSystem()
        self.foraging_sys = ForagingSystem()
        self.predation_sys = PredationSystem()
        self.hydration_sys = HydrationSystem()
        self.reproduction_sys = ReproductionSystem()
        self.aging_sys = AgingSystem()
        self.cleanup_sys = CleanupSystem()
        self.gathering_sys = GatheringSystem()
        self.building_sys = BuildingSystem()
        self.research_sys = ResearchSystem()
        self.crafting_sys = CraftingSystem()

        # Rendering
        self.assets = generate_assets()
        self.camera = Camera()
        self.map_renderer = TileMapRenderer()
        self.minimap = Minimap()
        self.ui_panel = UIPanel(self.font, self.small_font)
        self.toolbar = Toolbar(self.font, self.small_font)

        # Input
        self.god_mode = GodMode()
        self.mouse_down = False
        self.dragging_slider = False
        self.dragging_camera = False
        self.dragging_minimap = False
        self.hover_info: list[str] = []

        # Tab state
        self.current_tab = 0   # 0=监控, 1=工具
        self._tab_rects: list[pygame.Rect] = []

        # Camera keys
        self._cam_keys = {"up": False, "down": False, "left": False, "right": False}

    def run(self) -> None:
        running = True
        tick_accumulator = 0.0

        while running:
            dt = self.clock.tick(FPS) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    self._handle_key_down(event.key)
                elif event.type == pygame.KEYUP:
                    self._handle_key_up(event.key)
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    self._handle_mouse_down(event)
                elif event.type == pygame.MOUSEBUTTONUP:
                    self._handle_mouse_up(event)
                elif event.type == pygame.MOUSEMOTION:
                    self._handle_mouse_motion(event)
                elif event.type == pygame.MOUSEWHEEL:
                    self._handle_mouse_wheel(event)

            # Camera keyboard panning
            dx = (1 if self._cam_keys["right"] else 0) - (1 if self._cam_keys["left"] else 0)
            dy = (1 if self._cam_keys["down"] else 0) - (1 if self._cam_keys["up"] else 0)
            if dx or dy:
                self.camera.pan_direction(dx, dy, dt)

            self.camera.update(dt)

            # Simulation tick
            if not self.world.paused:
                ticks_per_second = {1: 2, 2: 5, 5: 12, 10: 25}[self.world.speed]
                tick_accumulator += dt * ticks_per_second
                while tick_accumulator >= 1.0:
                    tick_accumulator -= 1.0
                    self._tick()

            self._render()
            pygame.display.flip()

        pygame.quit()

    def _tick(self) -> None:
        w = self.world
        self.season_sys.update(w)
        self.weather_sys.update(w)
        self.grass_sys.update(w)
        self.fire_sys.update(w)
        self.plague_sys.update(w)
        self.human_ai_sys.update(w)
        self.ai_sys.update(w)
        self.movement_sys.update(w)
        self.foraging_sys.update(w)
        self.gathering_sys.update(w)
        self.research_sys.update(w)
        self.crafting_sys.update(w)
        self.predation_sys.update(w)
        self.hydration_sys.update(w)
        self.building_sys.update(w)
        self.reproduction_sys.update(w)
        self.aging_sys.update(w)
        self.cleanup_sys.update(w)
        w.rebuild_camp_positions()
        w.tick += 1

    # ----------------------------------------------------------------
    # Input handling
    # ----------------------------------------------------------------
    def _handle_key_down(self, key: int) -> None:
        if key == pygame.K_SPACE:
            self.world.paused = not self.world.paused
        elif key == pygame.K_1:
            self.world.speed = 1
        elif key == pygame.K_2:
            self.world.speed = 2
        elif key == pygame.K_5:
            self.world.speed = 5
        elif key == pygame.K_0:
            self.world.speed = 10
        elif key == pygame.K_s and self.world.paused:
            self._tick()
        elif key == pygame.K_r:
            self._reset_world()
        elif key == pygame.K_TAB:
            self.current_tab = 1 - self.current_tab
        elif key in (pygame.K_w, pygame.K_UP):
            self._cam_keys["up"] = True
        elif key in (pygame.K_s, pygame.K_DOWN):
            if key == pygame.K_DOWN:
                self._cam_keys["down"] = True
            # K_S is already used for step; don't pan with S
        elif key == pygame.K_a or key == pygame.K_LEFT:
            self._cam_keys["left"] = True
        elif key == pygame.K_d or key == pygame.K_RIGHT:
            self._cam_keys["right"] = True
        elif key == pygame.K_EQUALS or key == pygame.K_PLUS:
            self.camera.zoom_at(VIEWPORT_WIDTH // 2, VIEWPORT_HEIGHT // 2, 1.25)
        elif key == pygame.K_MINUS:
            self.camera.zoom_at(VIEWPORT_WIDTH // 2, VIEWPORT_HEIGHT // 2, 0.8)

    def _handle_key_up(self, key: int) -> None:
        if key in (pygame.K_w, pygame.K_UP):
            self._cam_keys["up"] = False
        elif key == pygame.K_DOWN:
            self._cam_keys["down"] = False
        elif key in (pygame.K_a, pygame.K_LEFT):
            self._cam_keys["left"] = False
        elif key in (pygame.K_d, pygame.K_RIGHT):
            self._cam_keys["right"] = False

    def _handle_mouse_down(self, event) -> None:
        mx, my = event.pos
        self.mouse_down = True

        # Tab bar clicks
        for i, rect in enumerate(self._tab_rects):
            if rect.collidepoint(mx, my):
                self.current_tab = i
                return

        # Monitor tab: minimap click
        if self.current_tab == 0:
            mini_rect = pygame.Rect(MINIMAP_X, MINIMAP_Y, MINI_W, MINI_H)
            if mini_rect.collidepoint(mx, my):
                gx, gy = self.minimap.screen_to_grid(mx - MINIMAP_X, my - MINIMAP_Y)
                self.camera.centre_on(gx, gy)
                self.dragging_minimap = True
                return

        # Tools tab: toolbar clicks
        if self.current_tab == 1 and mx >= PANEL_X:
            if self.toolbar.handle_click(mx - PANEL_X, my, TAB_HEIGHT + 4):
                self.dragging_slider = True
                return

        # Viewport area (works on both tabs)
        if mx < VIEWPORT_WIDTH and my < VIEWPORT_HEIGHT:
            if event.button == 3:  # right-click: drag camera
                self.dragging_camera = True
            else:
                gx, gy = self.camera.screen_to_grid(mx, my)
                self.god_mode.apply_click(
                    self.world, self.toolbar.current_tool,
                    self.toolbar.selected_species, self.toolbar.selected_terrain,
                    gx, gy,
                    weather_sys=self.weather_sys,
                    fire_sys=self.fire_sys,
                    plague_sys=self.plague_sys,
                )

    def _handle_mouse_up(self, event) -> None:
        self.mouse_down = False
        self.dragging_slider = False
        self.dragging_camera = False
        self.dragging_minimap = False

    def _handle_mouse_motion(self, event) -> None:
        mx, my = event.pos

        # Minimap drag
        if self.dragging_minimap:
            gx, gy = self.minimap.screen_to_grid(mx - MINIMAP_X, my - MINIMAP_Y)
            self.camera.centre_on(gx, gy)
            return

        # Camera drag (right mouse button)
        if self.dragging_camera:
            self.camera.pan_pixels(event.rel[0], event.rel[1])
            return

        # Slider drag (tools tab only)
        if self.dragging_slider and self.current_tab == 1 and mx >= PANEL_X:
            self.toolbar.handle_drag_slider(mx - PANEL_X, my, TAB_HEIGHT + 4)
            return

        # Continuous god-mode painting on viewport
        if self.mouse_down and mx < VIEWPORT_WIDTH and my < VIEWPORT_HEIGHT:
            gx, gy = self.camera.screen_to_grid(mx, my)
            self.god_mode.apply_click(
                self.world, self.toolbar.current_tool,
                self.toolbar.selected_species, self.toolbar.selected_terrain,
                gx, gy,
                weather_sys=self.weather_sys,
                fire_sys=self.fire_sys,
                plague_sys=self.plague_sys,
            )

        # Hover tooltip
        if mx < VIEWPORT_WIDTH and my < VIEWPORT_HEIGHT:
            self.hover_info = self.map_renderer.render_cell_info(
                self.world, self.camera, mx, my)
        else:
            self.hover_info = []

    def _handle_mouse_wheel(self, event) -> None:
        mx, my = pygame.mouse.get_pos()
        if mx < VIEWPORT_WIDTH and my < VIEWPORT_HEIGHT:
            factor = 1.2 if event.y > 0 else 0.83
            self.camera.zoom_at(mx, my, factor)

    def _reset_world(self) -> None:
        self.world = World()
        generate_terrain(self.world, seed=np.random.randint(0, 99999))
        populate_initial(self.world)
        self.world.rebuild_camp_positions()
        self.minimap._terrain_dirty = True

    # ----------------------------------------------------------------
    # Rendering
    # ----------------------------------------------------------------
    def _render(self) -> None:
        # 1. Viewport (tile map)
        viewport_surf = self.map_renderer.render(self.world, self.camera, self.assets)
        self.screen.blit(viewport_surf, (0, 0))

        # 2. Panel background
        pygame.draw.rect(self.screen, (30, 30, 35),
                         (PANEL_X, 0, PANEL_WIDTH, PANEL_HEIGHT))

        # 3. Tab bar
        self._draw_tabs()

        # 4. Tab content
        if self.current_tab == 0:
            self._render_monitor_tab()
        elif self.current_tab == 1:
            self._render_tools_tab()
        else:
            self._render_tech_tab()

        # 5. Status bar
        pygame.draw.rect(self.screen, (20, 20, 25),
                         (0, VIEWPORT_HEIGHT, WINDOW_WIDTH, STATUS_BAR_HEIGHT))
        pygame.draw.line(self.screen, (60, 60, 70),
                         (0, VIEWPORT_HEIGHT), (WINDOW_WIDTH, VIEWPORT_HEIGHT))
        season_name = SEASON_NAMES[Season(self.world.season)]
        total = sum(self.world.count_species(k) for k in SpeciesKind)
        status = (f"  {season_name}  |  Tick: {self.world.tick}  |  "
                  f"速度: {self.world.speed}x  |  {'暂停' if self.world.paused else '运行'}  |  "
                  f"生物: {total}  |  缩放: {self.camera.zoom:.1f}x")
        hint = "  WASD=移动  滚轮=缩放  空格=暂停  Tab=切页  R=重置"
        status_surf = self.small_font.render(status + hint, True, (180, 180, 180))
        self.screen.blit(status_surf, (8, VIEWPORT_HEIGHT + 8))

        # 6. Hover tooltip
        if self.hover_info:
            mouse_pos = pygame.mouse.get_pos()
            tx = min(mouse_pos[0] + 15, WINDOW_WIDTH - 160)
            ty = min(mouse_pos[1] + 15, VIEWPORT_HEIGHT - len(self.hover_info) * 16 - 10)
            for i, line in enumerate(self.hover_info):
                ts = self.small_font.render(line, True, (255, 255, 200))
                bg = pygame.Surface((ts.get_width() + 6, ts.get_height() + 2))
                bg.fill((0, 0, 0))
                bg.set_alpha(180)
                self.screen.blit(bg, (tx, ty + i * 16))
                self.screen.blit(ts, (tx + 3, ty + i * 16 + 1))

    def _draw_tabs(self) -> None:
        self._tab_rects.clear()
        tab_names = ["监控", "工具", "科技"]
        tab_w = (PANEL_WIDTH - 4) // len(tab_names)
        for i, name in enumerate(tab_names):
            tx = PANEL_X + 2 + i * tab_w
            rect = pygame.Rect(tx, 2, tab_w - 2, TAB_HEIGHT - 2)
            color = (60, 80, 60) if i == self.current_tab else (40, 40, 45)
            pygame.draw.rect(self.screen, color, rect)
            pygame.draw.rect(self.screen, (80, 80, 90), rect, 1)
            text = self.small_font.render(name, True, (220, 220, 220))
            self.screen.blit(text, (tx + (tab_w - text.get_width()) // 2, 8))
            self._tab_rects.append(rect)

    def _render_monitor_tab(self) -> None:
        # UI Panel (stats beside minimap + chart + events)
        panel_surf = self.ui_panel.render(self.world, top_margin=TAB_HEIGHT)
        self.screen.blit(panel_surf, (PANEL_X, 0))

        # Minimap (on top of UI panel background)
        mini_surf = self.minimap.render(self.world, self.camera, PANEL_X, MINIMAP_Y)
        self.screen.blit(mini_surf, (MINIMAP_X, MINIMAP_Y))
        pygame.draw.rect(self.screen, (100, 100, 110),
                         (MINIMAP_X - 1, MINIMAP_Y - 1, MINI_W + 2, MINI_H + 2), 1)
        mini_label = self.small_font.render("小地图 (点击跳转)", True, (150, 150, 150))
        self.screen.blit(mini_label, (MINIMAP_X, MINIMAP_Y + MINI_H + 2))

    def _render_tools_tab(self) -> None:
        toolbar_surf, _ = self.toolbar.render(TAB_HEIGHT + 4)
        self.screen.blit(toolbar_surf, (PANEL_X, TAB_HEIGHT + 4))

    def _render_tech_tab(self) -> None:
        from config import Role as RoleEnum
        from ecs.components import Structure as StructComp, Tribe as TribeComp

        x = PANEL_X + 8
        y = TAB_HEIGHT + 12

        # Get first camp
        camps = self.world.get_camps()
        struct = camps[0][2] if camps else None

        # Count scholars
        scholar_count = sum(
            1 for eid, tribe in self.world.query(TribeComp)
            if eid in self.world.entities and tribe.role == RoleEnum.SCHOLAR
        )

        # --- Header ---
        title = self.font.render("科技进度", True, (255, 255, 255))
        self.screen.blit(title, (x, y))
        y += 34

        if struct is None:
            info = self.small_font.render("无营地", True, (150, 150, 150))
            self.screen.blit(info, (x, y))
            return

        # Current era
        researched = struct.researched_tech
        if researched:
            best_tier = max(TECH_TREE[k].tier for k in researched if k in TECH_TREE)
            era_name = next((TECH_TREE[k].name for k in researched if TECH_TREE[k].tier == best_tier), "—")
        else:
            era_name = "原始时代"
        era_surf = self.small_font.render(f"当前时代: {era_name}", True, (200, 200, 200))
        self.screen.blit(era_surf, (x, y))
        y += 24

        # Find next available tech
        next_tech = None
        for tech_key, tech in sorted(TECH_TREE.items(), key=lambda x: x[1].tier):
            if tech_key not in researched and all(req in researched for req in tech.requires):
                next_tech = tech
                break

        # Research points + progress bar
        if next_tech:
            rp_text = f"研究点数: {int(struct.research_points)}/{next_tech.research_cost}"
            rp_color = (100, 200, 255)
        else:
            rp_text = f"研究点数: {int(struct.research_points)}"
            rp_color = (150, 150, 150)
        rp_surf = self.small_font.render(rp_text, True, rp_color)
        self.screen.blit(rp_surf, (x, y))
        y += 22

        # Progress bar
        bar_w = PANEL_WIDTH - 16
        bar_h = 10
        pygame.draw.rect(self.screen, (40, 40, 45), (x, y, bar_w, bar_h))
        if next_tech and next_tech.research_cost > 0:
            ratio = min(1.0, struct.research_points / next_tech.research_cost)
            pygame.draw.rect(self.screen, (80, 140, 200), (x, y, int(bar_w * ratio), bar_h))
        pygame.draw.rect(self.screen, (60, 60, 70), (x, y, bar_w, bar_h), 1)
        y += 18

        sc_surf = self.small_font.render(f"学者数量: {scholar_count}", True, (200, 180, 220))
        self.screen.blit(sc_surf, (x, y))
        y += 28

        # --- Tech tree ---
        header = self.small_font.render("--- 科技树 ---", True, (150, 150, 150))
        self.screen.blit(header, (x, y))
        y += 24

        for tech_key, tech in sorted(TECH_TREE.items(), key=lambda x: x[1].tier):
            is_done = tech_key in researched
            is_available = not is_done and all(req in researched for req in tech.requires)
            is_researching = is_available and next_tech and tech.key == next_tech.key

            if is_done:
                mark = "[\u2713]"
                mark_color = (80, 200, 80)
                name_color = (180, 220, 180)
            elif is_researching:
                mark = "[\u25cf]"
                mark_color = (100, 200, 255)
                name_color = (200, 220, 255)
            else:
                mark = "[ ]"
                mark_color = (100, 100, 100)
                name_color = (120, 120, 120)

            mark_surf = self.small_font.render(mark, True, mark_color)
            self.screen.blit(mark_surf, (x, y))
            name_surf = self.small_font.render(tech.name, True, name_color)
            self.screen.blit(name_surf, (x + 30, y))

            # Status text
            if is_done:
                status = "已解锁"
                status_color = (100, 160, 100)
            elif is_researching:
                status = f"{int(struct.research_points)}/{tech.research_cost}"
                status_color = (100, 200, 255)
            elif is_available:
                status = f"{tech.research_cost}\u7814\u7a76\u70b9"
                status_color = (150, 150, 150)
            else:
                prereq_names = ", ".join(TECH_TREE[r].name for r in tech.requires if r in TECH_TREE)
                status = f"\u9700: {prereq_names}" if prereq_names else ""
                status_color = (100, 100, 100)
            if status:
                st_surf = self.small_font.render(status, True, status_color)
                self.screen.blit(st_surf, (x + PANEL_WIDTH - 16 - st_surf.get_width() - 8, y))

            y += 22

            # Show unlocked recipes
            recipe_names = [RECIPE_REGISTRY[rk].name for rk in tech.unlocks_recipes if rk in RECIPE_REGISTRY]
            if recipe_names:
                rec_text = "    \u914d\u65b9: " + ", ".join(recipe_names)
                rec_surf = self.small_font.render(rec_text, True, (130, 130, 130))
                self.screen.blit(rec_surf, (x, y))
            y += 20
        y += 8

        # --- Refined stockpile ---
        header = self.small_font.render("--- \u7cbe\u70bc\u5e93\u5b58 ---", True, (150, 150, 150))
        self.screen.blit(header, (x, y))
        y += 24

        col_x = x
        col_y = y
        for res_key in all_refined():
            amount = struct.get_res(res_key)
            color = RESOURCE_REGISTRY[res_key].color
            pygame.draw.rect(self.screen, color, (col_x, col_y + 3, 10, 10))
            text = f"{res_name(res_key)}:{amount}"
            text_surf = self.small_font.render(text, True, (200, 200, 200))
            self.screen.blit(text_surf, (col_x + 14, col_y))
            col_x += 130
            if col_x + 120 > PANEL_X + PANEL_WIDTH - 8:
                col_x = x
                col_y += 24


def main():
    sim = Simulation()
    sim.run()
    sys.exit(0)


if __name__ == "__main__":
    main()
