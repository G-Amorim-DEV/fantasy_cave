"""Lógica dos níveis: mapas, rochas, cristais, saída e caminhos.

Este módulo não usa Pygame, então pode ser testado sem janela.

Legenda dos mapas:
    #  parede (indestrutível)      .  chão
    R  rocha quebrável             C  cristal
    P  início do jogador           X  saída (bloqueada até pegar todos os cristais)
"""
import math
from collections import deque

from .config import TILE, COLS, ROWS

LAYOUTS = {
    "easy": [
        "#########################",
        "#P......#.......#.......#",
        "#...............#..C#...#",
        "#.......#.......R.....C.#",
        "#.......#.......#.......#",
        "####.######.#########R###",
        "#.......#.......#.......#",
        "#...#...#...............#",
        "#...........C...#.......#",
        "#.......#.......#.......#",
        "###.########R#######.####",
        "#.......#.......#.......#",
        "#.......R...C...#.......#",
        "#.......#...#.C......X..#",
        "#.......#.......#.......#",
        "#########################",
    ],
    "medium": [
        "#########################",
        "#P......#.......#.......#",
        "#...#.......C...#.....C.#",
        "#...#...#.......R....R..#",
        "#.......#.......#.......#",
        "####R######.#########R###",
        "#.......#.......#.......#",
        "#.......R...#...#.......#",
        "#..C....#...#..R#.....C.#",
        "#.......#.....RC#.......#",
        "######.####R#############",
        "#.......#.......#.....RC#",
        "#...#...#.......R...#..R#",
        "#...#.....C.....#.....X.#",
        "#...C...#.......#.......#",
        "#########################",
    ],
    "hard": [
        "#########################",
        "#P......#.....RC#.......#",
        "#...#...#...#..RR...#...#",
        "#...#..RR...#...#...#..R#",
        "#.....RC#C......#.....RC#",
        "####.#####R###########R##",
        "#.......#.......#C......#",
        "#...#...R...C...#...#...#",
        "#R..#...#...#...R...#..R#",
        "#CR.....#.......#.....RC#",
        "######R#####R#####.######",
        "#.......#.......#.......#",
        "#...#...#...C...R...#...#",
        "#R..#...R...#...#R..#.X.#",
        "#CR.....#......CRC......#",
        "#########################",
    ],
}


class Rock:
    """Rocha quebrável. Some do nível quando hp chega a zero."""

    def __init__(self, col, row, hp):
        self.col, self.row = col, row
        self.max_hp = hp
        self.hp = hp
        self.shake = 0.0

    @property
    def damage_fraction(self):
        return 1.0 - self.hp / self.max_hp

    def hit(self):
        """Aplica um golpe. Retorna True se a rocha quebrou."""
        self.hp -= 1
        self.shake = 0.25
        return self.hp <= 0


class Crystal:
    def __init__(self, col, row, index):
        self.col, self.row = col, row
        self.x = col * TILE + TILE / 2
        self.y = row * TILE + TILE / 2
        self.collected = False
        self.phase = index * 1.7
        self.color_index = index % 3


class Level:
    def __init__(self, difficulty):
        self.difficulty = difficulty
        self.key = difficulty.key
        rows = LAYOUTS[difficulty.key]
        assert len(rows) == ROWS and all(len(r) == COLS for r in rows), "mapa com tamanho inválido"
        self.walls = [[ch == "#" for ch in row] for row in rows]
        self.rocks = {}
        self.crystals = []
        self.start_tile = (1, 1)
        self.exit_tile = (COLS - 2, ROWS - 2)
        for r, row in enumerate(rows):
            for c, ch in enumerate(row):
                if ch == "R":
                    self.rocks[(c, r)] = Rock(c, r, difficulty.rock_hits)
                elif ch == "C":
                    self.crystals.append(Crystal(c, r, len(self.crystals)))
                elif ch == "P":
                    self.start_tile = (c, r)
                elif ch == "X":
                    self.exit_tile = (c, r)
        self.total_crystals = len(self.crystals)
        self.collected = 0
        self.exit_open = False
        self.rocks_broken = 0

    # ---------- consultas ----------
    def is_wall(self, c, r):
        if c < 0 or r < 0 or c >= COLS or r >= ROWS:
            return True
        return self.walls[r][c]

    def is_solid(self, c, r):
        """Bloqueia o jogador: parede, rocha inteira ou saída ainda trancada."""
        if self.is_wall(c, r) or (c, r) in self.rocks:
            return True
        return (c, r) == self.exit_tile and not self.exit_open

    def special_tiles(self):
        tiles = {self.start_tile, self.exit_tile}
        tiles.update(self.rocks.keys())
        tiles.update((cr.col, cr.row) for cr in self.crystals)
        return tiles

    @staticmethod
    def tile_center(c, r):
        return c * TILE + TILE / 2, r * TILE + TILE / 2

    @staticmethod
    def tile_at(x, y):
        return int(x // TILE), int(y // TILE)

    # ---------- ações ----------
    def hit_rock(self, tile):
        """Golpeia a rocha em 'tile'. Retorna None, 'hit' ou 'broken'."""
        rock = self.rocks.get(tile)
        if rock is None:
            return None
        if rock.hit():
            del self.rocks[tile]
            self.rocks_broken += 1
            return "broken"
        return "hit"

    def collect_crystal(self, crystal):
        """Coleta um cristal uma única vez. Retorna True se foi coletado agora."""
        if crystal.collected:
            return False
        crystal.collected = True
        self.collected += 1
        if self.collected >= self.total_crystals:
            self.exit_open = True
        return True

    # ---------- caminhos ----------
    def find_path(self, start, goals):
        """BFS 4-direções por tiles livres. Retorna lista de tiles (sem o início),
        [] se já está no destino, ou None se não há caminho."""
        goals = set(goals)
        if start in goals:
            return []
        prev = {start: None}
        queue = deque([start])
        while queue:
            cur = queue.popleft()
            for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nxt = (cur[0] + dc, cur[1] + dr)
                if nxt in prev or self.is_solid(*nxt):
                    continue
                prev[nxt] = cur
                if nxt in goals:
                    path = [nxt]
                    while prev[path[-1]] != start:
                        path.append(prev[path[-1]])
                    return path[::-1]
                queue.append(nxt)
        return None

    def is_solvable(self):
        """Verifica se, quebrando rochas, todos os cristais e a saída são alcançáveis."""
        seen = {self.start_tile}
        queue = deque([self.start_tile])
        while queue:
            c, r = queue.popleft()
            for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (c + dc, r + dr)
                if n not in seen and not self.is_wall(*n):
                    seen.add(n)
                    queue.append(n)
        goals = [(cr.col, cr.row) for cr in self.crystals] + [self.exit_tile]
        return all(g in seen for g in goals)

    def compute_score(self, elapsed):
        d = self.difficulty
        time_bonus = max(0, int(d.par_time - elapsed)) * 3
        return (self.collected * 100 + self.rocks_broken * 20 + time_bonus) * d.score_mult


def distance(ax, ay, bx, by):
    return math.hypot(ax - bx, ay - by)
