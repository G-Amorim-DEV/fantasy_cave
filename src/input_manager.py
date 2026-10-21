"""Unifica teclado, mouse e gestos em um único objeto FrameInput por quadro."""
from __future__ import annotations

from dataclasses import dataclass, field

import pygame


@dataclass
class FrameInput:
    move: tuple = (0.0, 0.0)
    hit: bool = False
    interact: bool = False
    click: tuple | None = None
    mouse_pos: tuple = (0, 0)
    mouse_moved: bool = False
    confirm: bool = False
    nav: int = 0
    pressed: set = field(default_factory=set)
    point: tuple | None = None
    gestures: list = field(default_factory=list)
    quit: bool = False


class InputManager:
    def __init__(self, hand=None):
        self.hand = hand

    def process(self, events):
        f = FrameInput()
        f.mouse_pos = pygame.mouse.get_pos()
        for e in events:
            if e.type == pygame.QUIT:
                f.quit = True
            elif e.type == pygame.KEYDOWN:
                f.pressed.add(e.key)
            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                f.click = e.pos
            elif e.type == pygame.MOUSEMOTION:
                f.mouse_moved = True
                f.mouse_pos = e.pos
        keys = pygame.key.get_pressed()
        mx = (keys[pygame.K_d] or keys[pygame.K_RIGHT]) - (keys[pygame.K_a] or keys[pygame.K_LEFT])
        my = (keys[pygame.K_s] or keys[pygame.K_DOWN]) - (keys[pygame.K_w] or keys[pygame.K_UP])
        f.move = (float(mx), float(my))
        p = f.pressed
        f.confirm = bool(p & {pygame.K_RETURN, pygame.K_KP_ENTER})
        f.hit = pygame.K_SPACE in p
        f.interact = pygame.K_e in p
        down = p & {pygame.K_DOWN, pygame.K_s, pygame.K_RIGHT, pygame.K_d}
        up = p & {pygame.K_UP, pygame.K_w, pygame.K_LEFT, pygame.K_a}
        f.nav = (1 if down else 0) - (1 if up else 0)

        if self.hand is not None:
            snap = self.hand.snapshot()
            if snap["status"] == "active":
                if f.move == (0.0, 0.0):
                    f.move = snap["move"]
                for ev in self.hand.pop_events():
                    if ev == "hammer":
                        f.hit = True
                        f.gestures.append("Gesto: martelada")
                    elif isinstance(ev, tuple) and ev[0] == "point":
                        f.point = (ev[1], ev[2])
                        f.gestures.append("Gesto: apontar")
                    elif ev == "interact":
                        f.interact = True
                        f.gestures.append("Gesto: mão fechada")
        return f
