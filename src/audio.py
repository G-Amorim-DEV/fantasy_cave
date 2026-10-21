"""Sons sintetizados (sem arquivos). Se houver assets/sounds/<nome>.wav, ele é usado.
Qualquer falha de áudio é ignorada: o jogo continua sem som."""
import math
import os
from array import array

import pygame

SOUNDS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "sounds")


class Audio:
    def __init__(self):
        self.sounds = {}
        self.enabled = False
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(22050, -16, 1, 512)
            rate, size, channels = pygame.mixer.get_init()
            if abs(size) != 16:
                return
            self.rate, self.channels = rate, channels
            self.sounds = {
                "hit": self._tone([(140, 0.07)], 0.5, decay=True),
                "break": self._tone([(220, 0.07), (150, 0.08), (90, 0.12)], 0.5, decay=True),
                "crystal": self._tone([(660, 0.07), (880, 0.07), (1320, 0.12)], 0.35, decay=True),
                "exit": self._tone([(440, 0.1), (554, 0.1), (660, 0.1), (880, 0.25)], 0.35, decay=True),
                "click": self._tone([(500, 0.04)], 0.25, decay=True),
                "win": self._tone([(523, 0.15), (659, 0.15), (784, 0.15), (1047, 0.35)], 0.35, decay=True),
            }
            for name in list(self.sounds):
                path = os.path.join(SOUNDS_DIR, name + ".wav")
                if os.path.isfile(path):
                    try:
                        self.sounds[name] = pygame.mixer.Sound(path)
                    except Exception:
                        pass
            self.enabled = True
        except Exception:
            self.enabled = False

    def _tone(self, notes, volume, decay=False):
        data = array("h")
        for freq, dur in notes:
            n = int(self.rate * dur)
            for i in range(n):
                env = (1 - i / n) if decay else 1.0
                v = int(32767 * volume * env * math.sin(2 * math.pi * freq * i / self.rate))
                for _ in range(self.channels):
                    data.append(v)
        return pygame.mixer.Sound(buffer=data.tobytes())

    def play(self, name):
        if not self.enabled:
            return
        try:
            self.sounds[name].play()
        except Exception:
            pass
