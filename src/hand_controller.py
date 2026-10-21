"""Controle opcional por gestos (OpenCV + MediaPipe).

- GestureDetector: lógica pura (sem câmera), fácil de testar.
- HandController: thread que captura a câmera. Se OpenCV/MediaPipe ou a câmera
  falharem, apenas muda o status para 'error'; o jogo segue com teclado e mouse.

Gestos:
- Posição da mão em relação ao centro da imagem -> mover (esquerda/direita/cima/baixo).
- Movimento rápido de cima para baixo OU para os lados -> "martelada" (golpe na rocha).
- Apontar com 1 ou 2 dedos (indicador, ou indicador + médio) para a rocha -> golpe na direção do dedo.
- Fechar a mão (aberta -> punho) -> interagir/coletar.
"""
import threading
import time
from collections import deque

from .config import CAMERA_INDEX


class GestureDetector:
    def __init__(self, dead_x=0.10, dead_y=0.12, span=0.25,
                 hammer_min_drop=0.12, hammer_speed=0.9,
                 swing_min=0.18, swing_speed=1.3, hammer_window=0.30,
                 hammer_cooldown=0.6, interact_cooldown=0.8, freeze_after_hammer=0.4,
                 point_hold=0.2, point_interval=0.7):
        self.dead_x, self.dead_y, self.span = dead_x, dead_y, span
        self.hammer_min_drop = hammer_min_drop      # queda vertical mínima (martelada)
        self.hammer_speed = hammer_speed
        self.swing_min = swing_min                  # deslocamento lateral mínimo (martelada de lado)
        self.swing_speed = swing_speed
        self.hammer_window = hammer_window
        self.hammer_cooldown = hammer_cooldown
        self.interact_cooldown = interact_cooldown
        self.freeze_after_hammer = freeze_after_hammer
        self.point_hold = point_hold                # tempo apontando antes do 1º golpe
        self.point_interval = point_interval        # intervalo entre golpes enquanto aponta
        self.move = (0.0, 0.0)
        self.reset()

    def reset(self):
        self._sx = self._sy = None
        self._hist = deque()
        self._last_hammer = -99.0
        self._last_interact = -99.0
        self._last_point = -99.0
        self._point_since = None
        self._pdir = None
        self._freeze_until = 0.0
        self._prev_fist = False
        self.move = (0.0, 0.0)

    def _axis(self, value, dead):
        off = value - 0.5
        if abs(off) < dead:
            return 0.0
        sign = 1.0 if off > 0 else -1.0
        return sign * min(1.0, (abs(off) - dead) / max(0.001, self.span - dead))

    def update(self, x, y, fist, now, point_dir=None):
        """x, y normalizados (0..1, x já espelhado). point_dir = vetor do dedo apontando
        (ou None). Retorna eventos: 'hammer', 'interact' ou ('point', dx, dy)."""
        events = []
        if self._sx is None:
            self._sx, self._sy = x, y
        else:
            self._sx += 0.35 * (x - self._sx)
            self._sy += 0.35 * (y - self._sy)

        if point_dir is not None:
            # apontando: sem martelada/punho, sem andar; golpeia na direção do dedo
            self._hist.clear()
            self._prev_fist = False
            if self._pdir is None:
                self._pdir = point_dir
            else:
                self._pdir = (self._pdir[0] + 0.5 * (point_dir[0] - self._pdir[0]),
                              self._pdir[1] + 0.5 * (point_dir[1] - self._pdir[1]))
            if self._point_since is None:
                self._point_since = now
            if now - self._point_since >= self.point_hold and now - self._last_point >= self.point_interval:
                events.append(("point", self._pdir[0], self._pdir[1]))
                self._last_point = now
            self.move = (0.0, 0.0)
            return events
        self._point_since = None
        self._pdir = None

        # martelada: queda rápida (cima->baixo) OU deslocamento lateral rápido
        self._hist.append((now, x, y))
        while self._hist and now - self._hist[0][0] > self.hammer_window:
            self._hist.popleft()
        if now - self._last_hammer >= self.hammer_cooldown:
            for t0, x0, y0 in self._hist:
                dt = now - t0
                if dt <= 0.02:
                    continue
                drop = y - y0
                side = abs(x - x0)
                if (drop >= self.hammer_min_drop and drop / dt >= self.hammer_speed) or \
                        (side >= self.swing_min and side / dt >= self.swing_speed):
                    events.append("hammer")
                    self._last_hammer = now
                    self._freeze_until = now + self.freeze_after_hammer
                    self._hist.clear()
                    break

        # abrir -> fechar a mão
        if fist and not self._prev_fist and now - self._last_interact >= self.interact_cooldown:
            events.append("interact")
            self._last_interact = now
        self._prev_fist = fist

        if now < self._freeze_until:
            self.move = (0.0, 0.0)
        else:
            self.move = (self._axis(self._sx, self.dead_x), self._axis(self._sy, self.dead_y))
        return events

    def lost(self):
        self.reset()


class HandController:
    PREVIEW_SIZE = (96, 72)

    def __init__(self):
        self._lock = threading.Lock()
        self._thread = None
        self._stop = threading.Event()
        self.detector = GestureDetector()
        self._status = "off"        # off | starting | active | error
        self._message = ""
        self._hand = False
        self._move = (0.0, 0.0)
        self._events = []
        self._frame = None
        self._aim = None            # (x, y) normalizado do ponto de mira (cruz na prévia)
        self._pointing = False

    # ---------- API usada pelo jogo ----------
    @property
    def running(self):
        return self._thread is not None and self._thread.is_alive() and not self._stop.is_set()

    def toggle(self):
        if self.running:
            self.stop()
        else:
            self.start()

    def start(self):
        if self._thread is not None and self._thread.is_alive():
            self._stop.set()
            self._thread.join(timeout=1.5)
        self._stop.clear()
        self.detector.reset()
        self._set(status="starting", message="", hand=False, move=(0.0, 0.0), frame=None, aim=None, pointing=False)
        self._thread = threading.Thread(target=self._run, name="hand-controller", daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        self._set(status="off", message="", hand=False, move=(0.0, 0.0), frame=None, aim=None, pointing=False)

    def shutdown(self):
        """Chamado ao fechar o jogo: libera a câmera."""
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)

    def snapshot(self):
        with self._lock:
            return {"status": self._status, "message": self._message, "hand": self._hand,
                    "move": self._move, "frame": self._frame, "aim": self._aim,
                    "pointing": self._pointing}

    def pop_events(self):
        with self._lock:
            ev, self._events = self._events, []
        return ev

    # ---------- interno ----------
    def _set(self, **kw):
        with self._lock:
            if "status" in kw:
                self._status = kw["status"]
            if "message" in kw:
                self._message = kw["message"]
            if "hand" in kw:
                self._hand = kw["hand"]
            if "move" in kw:
                self._move = kw["move"]
            if "frame" in kw:
                self._frame = kw["frame"]
            if "aim" in kw:
                self._aim = kw["aim"]
            if "pointing" in kw:
                self._pointing = kw["pointing"]

    def _fail(self, msg):
        if not self._stop.is_set():
            self._set(status="error", message=msg, hand=False, move=(0.0, 0.0), frame=None, aim=None, pointing=False)

    @staticmethod
    def _fingers(lm):
        """Dedos estendidos [indicador, médio, anelar, mínimo]: ponta mais longe do pulso que a articulação."""
        def d(i):
            return (lm[i].x - lm[0].x) ** 2 + (lm[i].y - lm[0].y) ** 2
        return [d(tip) > d(pip) for tip, pip in ((8, 6), (12, 10), (16, 14), (20, 18))]

    def _run(self):
        try:
            import cv2
            import mediapipe as mp
        except Exception as exc:  # dependências opcionais ausentes
            self._fail("OpenCV/MediaPipe não instalados (%s)" % type(exc).__name__)
            return
        cap = None
        hands = None
        try:
            hands_mod = mp.solutions.hands
        except Exception:
            self._fail("versão do MediaPipe incompatível (use mediapipe==0.10.21)")
            return
        try:
            cap = cv2.VideoCapture(CAMERA_INDEX)
            if not cap.isOpened():
                self._fail("câmera não encontrada ou em uso")
                return
            hands = hands_mod.Hands(max_num_hands=1, model_complexity=0,
                                    min_detection_confidence=0.6, min_tracking_confidence=0.5)
            self._set(status="active", message="")
            fails = 0
            while not self._stop.is_set():
                ok, frame = cap.read()
                if not ok:
                    fails += 1
                    if fails > 30:
                        self._fail("a câmera parou de enviar imagens")
                        return
                    time.sleep(0.03)
                    continue
                fails = 0
                frame = cv2.flip(frame, 1)
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                result = hands.process(rgb)
                now = time.monotonic()
                small = cv2.resize(rgb, self.PREVIEW_SIZE)
                if result.multi_hand_landmarks:
                    lm = result.multi_hand_landmarks[0].landmark
                    # centro da palma: média do pulso e das bases dos dedos
                    idx = (0, 5, 9, 13, 17)
                    x = sum(lm[i].x for i in idx) / len(idx)
                    y = sum(lm[i].y for i in idx) / len(idx)
                    ext = self._fingers(lm)
                    fist = not any(ext)
                    # apontar com 1 ou 2 dedos: indicador estendido, anelar e mínimo fechados
                    pointing = ext[0] and not ext[2] and not ext[3]
                    point_dir = None
                    aim = (x, y)
                    if pointing:
                        vx, vy = lm[8].x - lm[5].x, lm[8].y - lm[5].y
                        n = (vx * vx + vy * vy) ** 0.5
                        if n > 0.02:
                            point_dir = (vx / n, vy / n)
                            aim = (lm[8].x, lm[8].y)
                    events = self.detector.update(x, y, fist, now, point_dir)
                    with self._lock:
                        self._hand = True
                        self._move = self.detector.move
                        self._events.extend(events)
                        self._aim = aim
                        self._pointing = point_dir is not None
                else:
                    self.detector.lost()
                    with self._lock:
                        self._hand = False
                        self._move = (0.0, 0.0)
                        self._aim = None
                        self._pointing = False
                with self._lock:
                    self._frame = (small.tobytes(), self.PREVIEW_SIZE[0], self.PREVIEW_SIZE[1])
        except Exception as exc:
            self._fail("erro na câmera: %s" % type(exc).__name__)
        finally:
            try:
                if hands is not None:
                    hands.close()
            except Exception:
                pass
            if cap is not None:
                cap.release()
