"""Interface: fontes, texto, botões, menus, partículas e fundo dos menus."""
import math
import random

import pygame

from .config import SCREEN_W, SCREEN_H

WHITE = (240, 236, 255)
MUTED = (170, 160, 200)
GOLD = (255, 214, 120)
CYAN = (110, 235, 255)
VIOLET = (150, 110, 255)


class Fonts:
    def __init__(self):
        self.title = pygame.font.Font(None, 112)
        self.h1 = pygame.font.Font(None, 62)
        self.h2 = pygame.font.Font(None, 40)
        self.body = pygame.font.Font(None, 30)
        self.small = pygame.font.Font(None, 25)
        self.tiny = pygame.font.Font(None, 21)


def draw_text(surf, text, font, color, pos, anchor="topleft", shadow=True):
    img = font.render(text, True, color)
    rect = img.get_rect()
    setattr(rect, anchor, pos)
    if shadow:
        surf.blit(font.render(text, True, (0, 0, 0)), rect.move(2, 2))
    surf.blit(img, rect)
    return rect


def wrap_text(text, font, max_w):
    lines, cur = [], ""
    for word in text.split():
        test = (cur + " " + word).strip()
        if font.size(test)[0] <= max_w:
            cur = test
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


class Button:
    def __init__(self, rect, label, action, accent=VIOLET):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.action = action
        self.accent = accent

    def draw(self, surf, fonts, selected, t):
        base = (74, 52, 130) if selected else (36, 28, 66)
        pygame.draw.rect(surf, base, self.rect, border_radius=14)
        if selected:
            pulse = 3 + int(2 * math.sin(t * 6))
            pygame.draw.rect(surf, self.accent, self.rect.inflate(pulse, pulse), 3, border_radius=16)
        else:
            pygame.draw.rect(surf, self.accent, self.rect, 2, border_radius=14)
        draw_text(surf, self.label, fonts.h2, WHITE, self.rect.center, "center")


class CardButton(Button):
    """Cartão de dificuldade."""

    def __init__(self, rect, difficulty):
        super().__init__(rect, difficulty.name, difficulty.key, difficulty.color)
        self.d = difficulty

    def draw(self, surf, fonts, selected, t):
        base = (58, 42, 108) if selected else (30, 24, 56)
        pygame.draw.rect(surf, base, self.rect, border_radius=18)
        width = 4 if selected else 2
        r = self.rect.inflate(6, 6) if selected else self.rect
        pygame.draw.rect(surf, self.accent, r, width, border_radius=18)
        cx = self.rect.centerx
        draw_text(surf, self.d.name, fonts.h1, self.accent, (cx, self.rect.y + 45), "center")
        draw_text(surf, "%d cristais" % self.d.crystals, fonts.h2, CYAN, (cx, self.rect.y + 100), "center")
        draw_text(surf, "%d golpes por rocha" % self.d.rock_hits, fonts.body, GOLD,
                  (cx, self.rect.y + 138), "center")
        for i, line in enumerate(wrap_text(self.d.description, fonts.small, self.rect.w - 40)):
            draw_text(surf, line, fonts.small, MUTED, (cx, self.rect.y + 180 + i * 24), "center")


class Menu:
    def __init__(self, buttons):
        self.buttons = buttons
        self.sel = 0

    def update(self, inp):
        """Retorna a ação do botão ativado (mouse ou teclado) ou None."""
        if inp.mouse_moved:
            for i, b in enumerate(self.buttons):
                if b.rect.collidepoint(inp.mouse_pos):
                    self.sel = i
        if inp.nav:
            self.sel = (self.sel + inp.nav) % len(self.buttons)
        if inp.click:
            for i, b in enumerate(self.buttons):
                if b.rect.collidepoint(inp.click):
                    self.sel = i
                    return b.action
        if inp.confirm:
            return self.buttons[self.sel].action
        return None

    def draw(self, surf, fonts, t):
        for i, b in enumerate(self.buttons):
            b.draw(surf, fonts, i == self.sel, t)


class ParticleSystem:
    def __init__(self):
        self.p = []
        self.texts = []

    def emit(self, x, y, color, n=12, speed=120, life=0.7, size=3, gravity=200):
        for _ in range(n):
            a = random.uniform(0, math.tau)
            s = random.uniform(0.3, 1.0) * speed
            self.p.append([x, y, math.cos(a) * s, math.sin(a) * s - speed * 0.3,
                           life * random.uniform(0.6, 1.0), life, color, size, gravity])

    def text(self, x, y, text, color=WHITE):
        self.texts.append([x, y, text, color, 1.0])

    def update(self, dt):
        for q in self.p:
            q[0] += q[2] * dt
            q[1] += q[3] * dt
            q[3] += q[8] * dt
            q[4] -= dt
        self.p = [q for q in self.p if q[4] > 0]
        for tx in self.texts:
            tx[1] -= 30 * dt
            tx[4] -= dt
        self.texts = [t for t in self.texts if t[4] > 0]

    def draw(self, surf, fonts):
        for x, y, _, _, life, maxlife, color, size, _ in self.p:
            k = max(0.0, life / maxlife)
            c = tuple(int(v * (0.35 + 0.65 * k)) for v in color)
            pygame.draw.circle(surf, c, (int(x), int(y)), max(1, int(size * k + 0.5)))

    def draw_texts(self, surf, fonts):
        for x, y, text, color, life in self.texts:
            c = tuple(int(v * min(1.0, life * 1.5)) for v in color)
            draw_text(surf, text, fonts.small, c, (int(x), int(y)), "center")


def build_menu_background():
    """Fundo de caverna para os menus (gerado uma vez)."""
    bg = pygame.Surface((SCREEN_W, SCREEN_H))
    for y in range(SCREEN_H):
        k = y / SCREEN_H
        pygame.draw.line(bg, (int(10 + 26 * k), int(8 + 12 * k), int(26 + 40 * k)), (0, y), (SCREEN_W, y))
    rng = random.Random(7)
    x = -20
    while x < SCREEN_W + 20:                     # estalactites
        w = rng.randint(40, 90)
        h = rng.randint(40, 150)
        pygame.draw.polygon(bg, (22, 16, 40), [(x, 0), (x + w, 0), (x + w // 2, h)])
        pygame.draw.polygon(bg, (60, 44, 98), [(x, 0), (x + w, 0), (x + w // 2, h)], 2)
        x += w - rng.randint(0, 20)
    x = 0
    while x < SCREEN_W:                           # estalagmites + cristais no chão
        w = rng.randint(50, 110)
        h = rng.randint(30, 110)
        pygame.draw.polygon(bg, (24, 18, 44), [(x, SCREEN_H), (x + w, SCREEN_H), (x + w // 2, SCREEN_H - h)])
        if rng.random() < 0.5:
            cx, cy = x + w // 2, SCREEN_H - h - 4
            col = rng.choice([(90, 230, 255), (230, 120, 255), (120, 255, 190)])
            pygame.draw.polygon(bg, col, [(cx, cy - 26), (cx + 10, cy), (cx, cy + 12), (cx - 10, cy)])
            pygame.draw.polygon(bg, WHITE, [(cx, cy - 26), (cx + 10, cy), (cx, cy + 12), (cx - 10, cy)], 1)
        x += w
    return bg


class MenuAmbience:
    """Vagalumes flutuando nos menus."""

    def __init__(self):
        rng = random.Random(3)
        self.flies = [[rng.uniform(0, SCREEN_W), rng.uniform(100, SCREEN_H - 100),
                       rng.uniform(0, 6.28), rng.uniform(10, 30)] for _ in range(40)]

    def draw(self, surf, t):
        for f in self.flies:
            x = f[0] + math.sin(t * 0.5 + f[2]) * f[3]
            y = f[1] + math.cos(t * 0.4 + f[2]) * f[3]
            b = 0.5 + 0.5 * math.sin(t * 2 + f[2])
            pygame.draw.circle(surf, (int(120 + 100 * b), int(110 + 100 * b), 255), (int(x), int(y)), 2)
