"""Desenho do mundo: caverna, rochas, cristais, saída, explorador e iluminação."""
import math
import random

import pygame

from .config import TILE, COLS, ROWS, MAP_W, MAP_H
from .ui import GOLD

WALL = (34, 26, 54)
FLOOR = (96, 84, 118)
RIM = (150, 120, 205)
DARK_ALPHA = 125
CRYSTAL_COLORS = [(90, 230, 255), (235, 120, 255), (120, 255, 190)]


def make_light(radius, max_alpha):
    s = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    steps = max(8, radius // 3)
    for i in range(steps):
        rad = int(radius * (1 - i / steps))
        a = int(max_alpha * ((i + 1) / steps) ** 0.8)
        pygame.draw.circle(s, (0, 0, 0, a), (radius, radius), rad)
    return s


def make_glow(radius, color):
    s = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    for i in range(radius, 0, -2):
        a = int(150 * (1 - i / radius) ** 2)
        pygame.draw.circle(s, (*color, a), (radius, radius), i)
    return s


class Renderer:
    def __init__(self, level):
        self.level = level
        self.bg = self._build_background()
        self.dark = pygame.Surface((MAP_W, MAP_H), pygame.SRCALPHA)
        self.player_lights = [make_light(int(TILE * r), DARK_ALPHA) for r in (6.0, 6.3, 6.6)]
        self.crystal_light = make_light(int(TILE * 1.7), 85)
        self.exit_light = make_light(int(TILE * 2.6), 115)
        self.glows = [make_glow(int(TILE * 0.9), c) for c in CRYSTAL_COLORS]
        rng = random.Random(11)
        self.motes = [[rng.uniform(0, MAP_W), rng.uniform(0, MAP_H), rng.uniform(0, 6.28)] for _ in range(45)]

    # ---------- fundo estático ----------
    def _build_background(self):
        lv = self.level
        rng = random.Random(lv.key)
        bg = pygame.Surface((MAP_W, MAP_H))
        special = lv.special_tiles()
        for r in range(ROWS):
            for c in range(COLS):
                x, y = c * TILE, r * TILE
                n = rng.randint(-7, 7)
                if lv.is_wall(c, r):
                    pygame.draw.rect(bg, (WALL[0] + n, WALL[1] + n, WALL[2] + n), (x, y, TILE, TILE))
                    pygame.draw.rect(bg, (24, 18, 40), (x, y, TILE, TILE), 1)
                    if rng.random() < 0.05:
                        col = rng.choice(CRYSTAL_COLORS)
                        pygame.draw.circle(bg, tuple(v // 2 for v in col),
                                           (x + rng.randint(8, TILE - 8), y + rng.randint(8, TILE - 8)), 3)
                else:
                    pygame.draw.rect(bg, (FLOOR[0] + n, FLOOR[1] + n, FLOOR[2] + n), (x, y, TILE, TILE))
                    pygame.draw.rect(bg, (FLOOR[0] - 14, FLOOR[1] - 14, FLOOR[2] - 12), (x, y, TILE, TILE), 1)
        for r in range(ROWS):
            for c in range(COLS):
                if not lv.is_wall(c, r):
                    continue
                x, y = c * TILE, r * TILE
                for dc, dr, line in ((0, -1, ((x, y), (x + TILE, y))),
                                     (0, 1, ((x, y + TILE - 1), (x + TILE, y + TILE - 1))),
                                     (-1, 0, ((x, y), (x, y + TILE))),
                                     (1, 0, ((x + TILE - 1, y), (x + TILE - 1, y + TILE)))):
                    nc, nr = c + dc, r + dr
                    if 0 <= nc < COLS and 0 <= nr < ROWS and not lv.is_wall(nc, nr):
                        pygame.draw.line(bg, RIM, line[0], line[1], 3)
        for r in range(ROWS):               # decoração: cogumelos e estalagmites
            for c in range(COLS):
                if lv.is_wall(c, r) or (c, r) in special:
                    continue
                roll = rng.random()
                x = c * TILE + rng.randint(6, TILE - 12)
                y = r * TILE + rng.randint(14, TILE - 6)
                if roll < 0.05:
                    col = rng.choice([(255, 120, 200), (120, 200, 255), (255, 200, 90)])
                    pygame.draw.rect(bg, (220, 215, 200), (x, y - 5, 3, 7))
                    pygame.draw.ellipse(bg, col, (x - 4, y - 10, 11, 7))
                    pygame.draw.circle(bg, (255, 255, 255), (x, y - 7), 1)
                elif roll < 0.09:
                    pygame.draw.polygon(bg, (70, 60, 92), [(x - 5, y), (x + 5, y), (x, y - 12)])
        return bg

    # ---------- elementos ----------
    def draw_rock(self, surf, rock, t, focus=False, hover=False):
        cx, cy = rock.col * TILE + TILE / 2, rock.row * TILE + TILE / 2
        if rock.shake > 0:
            cx += math.sin(t * 90) * 3 * (rock.shake / 0.25)
        rng = random.Random(rock.col * 131 + rock.row * 17)
        dmg = rock.damage_fraction
        pts = []
        for i in range(9):
            a = i / 9 * math.tau
            rad = TILE * rng.uniform(0.38, 0.48)
            pts.append((cx + math.cos(a) * rad, cy + math.sin(a) * rad))
        base = (int(150 + 60 * dmg), int(122 - 30 * dmg), int(96 - 30 * dmg))
        pygame.draw.polygon(surf, (base[0] // 2, base[1] // 2, base[2] // 2), [(x + 2, y + 3) for x, y in pts])
        pygame.draw.polygon(surf, base, pts)
        pygame.draw.polygon(surf, tuple(min(255, v + 45) for v in base),
                            [(cx + (x - cx) * 0.55 - 3, cy + (y - cy) * 0.55 - 4) for x, y in pts])
        outline = (255, 255, 255) if (focus or hover) else (255, 180, 80)
        width = 3 if (focus or hover) else 2
        pygame.draw.polygon(surf, outline, pts, width)
        cracks = int(dmg * 6 + 0.5) if dmg > 0 else 0
        crng = random.Random(rock.col * 7 + rock.row)
        for _ in range(cracks):
            a = crng.uniform(0, math.tau)
            l1 = TILE * crng.uniform(0.2, 0.4)
            p1 = (cx + math.cos(a) * l1, cy + math.sin(a) * l1)
            p2 = (p1[0] + math.cos(a + 0.7) * 7, p1[1] + math.sin(a + 0.7) * 7)
            pygame.draw.lines(surf, (40, 25, 20), False, [(cx, cy), p1, p2], 2)
        if dmg > 0:                       # barra de resistência
            w = int(TILE * 0.8)
            bx, by = int(cx - w / 2), int(cy - TILE * 0.5 - 4)
            pygame.draw.rect(surf, (20, 10, 10), (bx, by, w, 5))
            pygame.draw.rect(surf, (230, 90, 60), (bx, by, int(w * (1 - dmg)), 5))

    def draw_crystal(self, surf, cr, t, hover=False):
        bob = math.sin(t * 3 + cr.phase) * 2
        x, y = cr.x, cr.y + bob
        col = CRYSTAL_COLORS[cr.color_index]
        pulse = 0.6 + 0.4 * math.sin(t * 4 + cr.phase)
        glow = self.glows[cr.color_index]
        glow.set_alpha(int(255 * pulse))
        surf.blit(glow, (x - glow.get_width() / 2, y - glow.get_height() / 2))
        big = [(x, y - 15), (x + 9, y - 2), (x + 5, y + 13), (x - 5, y + 13), (x - 9, y - 2)]
        pygame.draw.polygon(surf, col, big)
        pygame.draw.polygon(surf, tuple(min(255, v + 90) for v in col),
                            [(x, y - 15), (x + 9, y - 2), (x, y + 2)])
        pygame.draw.polygon(surf, (255, 255, 255), big, 2)
        small = [(x + 12, y + 2), (x + 17, y + 8), (x + 14, y + 14), (x + 9, y + 10)]
        pygame.draw.polygon(surf, tuple(int(v * 0.8) for v in col), small)
        if hover:
            pygame.draw.circle(surf, (255, 255, 255), (int(x), int(y)), 24, 2)

    def draw_exit(self, surf, t, hover=False):
        lv = self.level
        c, r = lv.exit_tile
        x, y = c * TILE, r * TILE
        rect = pygame.Rect(x + 3, y + 3, TILE - 6, TILE - 6)
        if lv.exit_open:
            pulse = 0.5 + 0.5 * math.sin(t * 4)
            pygame.draw.rect(surf, (20, 60, 40), (x, y, TILE, TILE))
            for i in range(4):
                rad = int(TILE * (0.48 - i * 0.1) + pulse * 2)
                col = (int(120 + 30 * i), 255 - 20 * i, int(160 + 20 * i))
                pygame.draw.circle(surf, col, rect.center, max(2, rad), 3 if i < 3 else 0)
            ang = t * 2
            for i in range(8):
                a = ang + i * math.tau / 8
                pygame.draw.line(surf, (200, 255, 210),
                                 (rect.centerx + math.cos(a) * 10, rect.centery + math.sin(a) * 10),
                                 (rect.centerx + math.cos(a) * 20, rect.centery + math.sin(a) * 20), 2)
        else:
            pygame.draw.rect(surf, (52, 40, 70), (x, y, TILE, TILE))
            pygame.draw.rect(surf, (140, 40, 60), rect, 3)
            for i in range(1, 5):
                pygame.draw.line(surf, (160, 160, 175), (rect.x + i * rect.w // 5, rect.y),
                                 (rect.x + i * rect.w // 5, rect.bottom), 3)
            pygame.draw.rect(surf, (230, 190, 70), (rect.centerx - 7, rect.centery - 1, 14, 11), border_radius=2)
            pygame.draw.arc(surf, (230, 190, 70), (rect.centerx - 5, rect.centery - 9, 10, 14), 0, math.pi, 3)
        if hover:
            pygame.draw.rect(surf, (255, 255, 255), (x, y, TILE, TILE), 3, border_radius=4)

    def draw_player(self, surf, p, t):
        x, y = int(p.x), int(p.y)
        bob = math.sin(p.anim * 12) * 1.5 if p.moving else 0
        fx, fy = p.facing
        pygame.draw.ellipse(surf, (25, 20, 35), (x - 11, y + 8, 22, 9))
        # picareta atrás do corpo quando virado para cima
        def pick():
            hx, hy = x + fx * 24, y + 2 + fy * 24
            pygame.draw.line(surf, (120, 80, 40), (x + fx * 6, y + 2 + fy * 6), (hx, hy), 4)
            px, py = -fy, fx
            pygame.draw.line(surf, (200, 205, 215), (hx - px * 7, hy - py * 7), (hx + px * 7, hy + py * 7), 4)
        if fy < -0.3:
            pick()
        pygame.draw.rect(surf, (60, 110, 200), (x - 9, y - 5 + bob, 18, 16), border_radius=4)
        pygame.draw.rect(surf, (120, 80, 40), (x - 9, y + 3 + bob, 18, 3))
        pygame.draw.circle(surf, (240, 200, 160), (x, int(y - 11 + bob)), 8)
        pygame.draw.ellipse(surf, (150, 95, 45), (x - 13, y - 19 + bob, 26, 8))
        pygame.draw.rect(surf, (170, 110, 55), (x - 7, y - 26 + bob, 14, 9), border_radius=4)
        pygame.draw.circle(surf, (255, 240, 170), (x, int(y - 22 + bob)), 3)   # lanterna do chapéu
        if fy >= -0.3:
            pick()
        # seta de direção
        ax, ay = x + fx * 30, y + fy * 30
        px, py = -fy, fx
        pygame.draw.polygon(surf, GOLD, [(ax + fx * 6, ay + fy * 6), (ax + px * 5, ay + py * 5),
                                         (ax - px * 5, ay - py * 5)])

    # ---------- quadro completo ----------
    def draw(self, surf, player, t, focus_rock, hover, particles, fonts):
        lv = self.level
        surf.blit(self.bg, (0, 0))
        for m in self.motes:
            b = 0.5 + 0.5 * math.sin(t * 2 + m[2])
            mx = (m[0] + math.sin(t * 0.3 + m[2]) * 14) % MAP_W
            my = (m[1] + math.cos(t * 0.25 + m[2]) * 14) % MAP_H
            pygame.draw.circle(surf, (int(90 + 110 * b), int(90 + 110 * b), 255), (int(mx), int(my)), 1)
        self.draw_exit(surf, t, hover and hover[0] == "exit")
        for cr in lv.crystals:
            if not cr.collected:
                self.draw_crystal(surf, cr, t, hover is not None and hover[0] == "crystal" and hover[1] is cr)
        for tile, rock in lv.rocks.items():
            self.draw_rock(surf, rock, t, focus_rock == tile, hover is not None and hover == ("rock", tile))
        self.draw_player(surf, player, t)
        particles.draw(surf, fonts)
        # iluminação: escurece tudo e "fura" a escuridão com luzes
        self.dark.fill((6, 4, 16, DARK_ALPHA))
        light = self.player_lights[int(t * 7) % 3]
        self.dark.blit(light, (player.x - light.get_width() / 2, player.y - light.get_height() / 2),
                       special_flags=pygame.BLEND_RGBA_SUB)
        for cr in lv.crystals:
            if not cr.collected:
                self.dark.blit(self.crystal_light, (cr.x - self.crystal_light.get_width() / 2,
                                                    cr.y - self.crystal_light.get_height() / 2),
                               special_flags=pygame.BLEND_RGBA_SUB)
        if lv.exit_open:
            ex, ey = lv.tile_center(*lv.exit_tile)
            self.dark.blit(self.exit_light, (ex - self.exit_light.get_width() / 2,
                                             ey - self.exit_light.get_height() / 2),
                           special_flags=pygame.BLEND_RGBA_SUB)
        surf.blit(self.dark, (0, 0))
        particles.draw_texts(surf, fonts)
        # realces por cima da escuridão (objeto sob o mouse / rocha em foco)
        if focus_rock is not None:
            pygame.draw.rect(surf, (255, 255, 255), (focus_rock[0] * TILE + 2, focus_rock[1] * TILE + 2,
                                                     TILE - 4, TILE - 4), 2, border_radius=8)
        if hover and hover[0] == "rock":
            c, r = hover[1]
            pygame.draw.rect(surf, (255, 230, 150), (c * TILE + 1, r * TILE + 1, TILE - 2, TILE - 2), 3,
                             border_radius=8)
        elif hover and hover[0] == "crystal":
            pygame.draw.circle(surf, (255, 255, 255), (int(hover[1].x), int(hover[1].y)), 24, 2)
        elif hover and hover[0] == "exit":
            c, r = hover[1]
            pygame.draw.rect(surf, (255, 255, 255), (c * TILE, r * TILE, TILE, TILE), 3, border_radius=4)
        # marcador do chão sob o mouse
        if hover and hover[0] == "floor":
            c, r = hover[1]
            pygame.draw.rect(surf, (255, 255, 255), (c * TILE + 6, r * TILE + 6, TILE - 12, TILE - 12), 2,
                             border_radius=6)
