"""Explorador: movimento com colisão por eixo, direção e seguir caminho (mouse)."""
import math

from .config import TILE, PLAYER_SIZE


class Player:
    def __init__(self, x, y, speed):
        self.x = x
        self.y = y
        self.speed = speed
        self.facing = (0.0, 1.0)
        self.size = PLAYER_SIZE
        self.path = []          # lista de tiles (clique do mouse)
        self.moving = False
        self.anim = 0.0
        self._stuck = 0.0

    @property
    def tile(self):
        return int(self.x // TILE), int(self.y // TILE)

    def cancel_path(self):
        self.path = []
        self._stuck = 0.0

    def _blocked_tiles(self, level):
        half = self.size / 2
        c0 = int((self.x - half) // TILE)
        c1 = int((self.x + half - 0.001) // TILE)
        r0 = int((self.y - half) // TILE)
        r1 = int((self.y + half - 0.001) // TILE)
        return [(c, r) for r in range(r0, r1 + 1) for c in range(c0, c1 + 1)
                if level.is_solid(c, r)]

    def move(self, dx, dy, level):
        """Move com colisão separada por eixo (desliza ao longo das paredes)."""
        half = self.size / 2
        if dx:
            self.x += dx
            for c, _ in self._blocked_tiles(level):
                if dx > 0:
                    self.x = min(self.x, c * TILE - half)
                else:
                    self.x = max(self.x, (c + 1) * TILE + half)
        if dy:
            self.y += dy
            for _, r in self._blocked_tiles(level):
                if dy > 0:
                    self.y = min(self.y, r * TILE - half)
                else:
                    self.y = max(self.y, (r + 1) * TILE + half)

    def walk(self, dt, vec, level):
        """Movimento direto por teclado/gesto. vec em [-1, 1]."""
        vx, vy = vec
        length = math.hypot(vx, vy)
        self.moving = length > 0.01
        if not self.moving:
            return
        if length > 1:
            vx, vy = vx / length, vy / length
            length = 1
        self.facing = (vx / length, vy / length)
        self.cancel_path()
        step = self.speed * dt
        self.move(vx * step, vy * step, level)
        self.anim += dt

    def follow_path(self, dt, level):
        """Segue o caminho calculado a partir de um clique do mouse."""
        self.moving = False
        if not self.path:
            return
        tx = self.path[0][0] * TILE + TILE / 2
        ty = self.path[0][1] * TILE + TILE / 2
        dx, dy = tx - self.x, ty - self.y
        dist = math.hypot(dx, dy)
        step = self.speed * dt
        if dist <= step + 0.5:
            self.x, self.y = tx, ty
            self.path.pop(0)
            return
        self.facing = (dx / dist, dy / dist)
        ox, oy = self.x, self.y
        self.move(dx / dist * step, dy / dist * step, level)
        self.moving = True
        self.anim += dt
        # detecta travamento (ex.: caminho bloqueado depois de um evento)
        if math.hypot(self.x - ox, self.y - oy) < step * 0.2:
            self._stuck += dt
            if self._stuck > 0.4:
                self.cancel_path()
        else:
            self._stuck = 0.0
