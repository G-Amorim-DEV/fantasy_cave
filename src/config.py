"""Configurações centrais do Fantasy Cave.

Valores que podem ser ajustados com segurança:
- TILE: tamanho do bloco em pixels. A janela é calculada a partir dele
  (TILE=40 -> 1000 x 712). Use 32 para uma janela menor.
- FPS, CAMERA_INDEX, HIT_COOLDOWN.
- DIFFICULTIES: velocidade, golpes por rocha, tempo de referência, etc.
  (a quantidade de cristais vem do mapa em src/level.py).
"""
from dataclasses import dataclass

TITLE = "Fantasy Cave"

# --- Resolução (derivada do tamanho do bloco) ---
TILE = 40
COLS = 25
ROWS = 16
HUD_H = 72
MAP_W = TILE * COLS
MAP_H = TILE * ROWS
SCREEN_W = MAP_W
SCREEN_H = MAP_H + HUD_H
FPS = 60

# --- Jogabilidade ---
PLAYER_SIZE = int(TILE * 0.6)     # caixa de colisão do explorador
REACH = TILE * 1.9                # alcance para mouse/gesto/tecla E
CONTACT_RADIUS = TILE * 0.5       # coleta automática de cristal por contato
HIT_COOLDOWN = 0.22               # intervalo mínimo entre golpes (segundos)

# --- Câmera / gestos ---
CAMERA_INDEX = 0


@dataclass(frozen=True)
class Difficulty:
    key: str
    name: str
    crystals: int        # deve bater com o número de 'C' no mapa
    rock_hits: int       # golpes para quebrar cada rocha
    speed_tiles: float   # velocidade em blocos por segundo
    par_time: int        # segundos de referência para bônus de tempo
    score_mult: int
    description: str
    color: tuple

    @property
    def speed(self):
        return self.speed_tiles * TILE


DIFFICULTIES = (
    Difficulty("easy", "Fácil", 5, 2, 5.6, 90, 1,
               "Poucas rochas e muito espaço para caminhar.", (110, 230, 150)),
    Difficulty("medium", "Médio", 8, 3, 5.2, 150, 2,
               "Mais rochas e caminhos menos diretos.", (255, 210, 100)),
    Difficulty("hard", "Difícil", 12, 4, 5.0, 240, 3,
               "Muitos obstáculos e cristais escondidos atrás de rochas.", (255, 110, 130)),
)


def get_difficulty(key):
    for d in DIFFICULTIES:
        if d.key == key:
            return d
    raise KeyError(key)
