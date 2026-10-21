"""Loop principal, estados (menus, jogo, pausa, vitória) e regras de interação."""
import math

import pygame

from .audio import Audio
from .config import (CONTACT_RADIUS, DIFFICULTIES, FPS, HIT_COOLDOWN, HUD_H, MAP_H, MAP_W, REACH,
                     SCREEN_H, SCREEN_W, TILE, TITLE)
from .hand_controller import HandController
from .input_manager import InputManager
from .level import Level, distance

PREVIEW_W = 96
from .player import Player
from .renderer import Renderer
from .ui import (CYAN, GOLD, MUTED, WHITE, Button, CardButton, Fonts, Menu, MenuAmbience,
                 ParticleSystem, build_menu_background, draw_text, wrap_text)

MENU, DIFFICULTY, PLAYING, PAUSED, VICTORY = "menu", "difficulty", "playing", "paused", "victory"


def center_rect(cx, cy, w, h):
    return pygame.Rect(cx - w // 2, cy - h // 2, w, h)


class Game:
    def __init__(self):
        pygame.init()
        try:
            self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H), pygame.SCALED | pygame.RESIZABLE)
        except pygame.error:
            self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption(TITLE)
        self.clock = pygame.time.Clock()
        self.fonts = Fonts()
        self.audio = Audio()
        self.hand = HandController()
        self.input = InputManager(self.hand)
        self.menu_bg = build_menu_background()
        self.ambience = MenuAmbience()
        self.particles = ParticleSystem()
        self.running = True
        self.t = 0.0
        self.state = MENU
        self.difficulty = DIFFICULTIES[0]
        self.level = self.player = self.renderer = None
        self.elapsed = 0.0
        self.hit_cd = 0.0
        self.pending = None
        self.hint = ""
        self.banner = ("", 0.0)
        self.toast = ("", 0.0)
        self.gesture_msg = ("", 0.0)
        self.hover = None
        self.focus = None
        self.result = {}
        self.best = {}
        self._build_menus()

    # ---------- menus ----------
    def _build_menus(self):
        cx = SCREEN_W // 2
        self.main_menu = Menu([
            Button(center_rect(cx, 440, 320, 62), "Jogar", "play"),
            Button(center_rect(cx, 515, 320, 62), "Sair", "quit"),
        ])
        cards = [CardButton(center_rect(cx + (i - 1) * 310, 360, 280, 270), d) for i, d in enumerate(DIFFICULTIES)]
        cards.append(Button(center_rect(cx, 590, 240, 56), "Voltar", "back"))
        self.diff_menu = Menu(cards)
        self.pause_menu = Menu([
            Button(center_rect(cx, 300, 340, 58), "Continuar", "resume"),
            Button(center_rect(cx, 370, 340, 58), "Reiniciar nível", "restart"),
            Button(center_rect(cx, 440, 340, 58), "Trocar dificuldade", "difficulty"),
            Button(center_rect(cx, 510, 340, 58), "Sair", "quit"),
        ])
        self.victory_menu = Menu([])

    def _build_victory_menu(self):
        cx = SCREEN_W // 2
        items = [("Jogar novamente (R)", "restart")]
        if self.next_difficulty() is not None:
            items.append(("Próxima dificuldade (N)", "next"))
        items += [("Trocar dificuldade (D)", "difficulty"), ("Sair (Q)", "quit")]
        y0 = 395
        self.victory_menu = Menu([Button(center_rect(cx, y0 + i * 62, 380, 52), label, act)
                                  for i, (label, act) in enumerate(items)])

    def next_difficulty(self):
        i = DIFFICULTIES.index(self.difficulty)
        return DIFFICULTIES[i + 1] if i + 1 < len(DIFFICULTIES) else None

    # ---------- níveis ----------
    def start_level(self, difficulty):
        self.difficulty = difficulty
        self.level = Level(difficulty)
        x, y = self.level.tile_center(*self.level.start_tile)
        self.player = Player(x, y, difficulty.speed)
        self.renderer = Renderer(self.level)
        self.particles = ParticleSystem()
        self.elapsed = 0.0
        self.hit_cd = 0.0
        self.pending = None
        self.banner = ("", 0.0)
        self.toast = ("", 0.0)
        self.state = PLAYING

    def say(self, text, secs=1.6):
        self.toast = (text, secs)

    # ---------- loop ----------
    def run(self):
        try:
            while self.running:
                dt = min(self.clock.tick(FPS) / 1000.0, 0.05)
                self.step(dt, pygame.event.get())
        finally:
            self.hand.shutdown()
            pygame.quit()

    def step(self, dt, events):
        """Um quadro completo: entrada, atualização e desenho."""
        self.t += dt
        inp = self.input.process(events)
        if inp.quit:
            self.running = False
            return
        if pygame.K_m in inp.pressed:
            self.hand.toggle()
        if inp.gestures:
            self.gesture_msg = (inp.gestures[-1], 1.2)
        if self.gesture_msg[1] > 0:
            self.gesture_msg = (self.gesture_msg[0], self.gesture_msg[1] - dt)

        handler = {MENU: self.update_menu, DIFFICULTY: self.update_difficulty,
                   PLAYING: self.update_play, PAUSED: self.update_pause,
                   VICTORY: self.update_victory}[self.state]
        handler(dt, inp)
        self.draw()
        pygame.display.flip()

    # ---------- atualizações por estado ----------
    def update_menu(self, dt, inp):
        act = self.main_menu.update(inp)
        if pygame.K_ESCAPE in inp.pressed:
            act = "quit"
        if act == "play":
            self.audio.play("click")
            self.state = DIFFICULTY
        elif act == "quit":
            self.running = False

    def update_difficulty(self, dt, inp):
        act = self.diff_menu.update(inp)
        if pygame.K_ESCAPE in inp.pressed:
            act = "back"
        if act == "back":
            self.state = MENU
        elif act is not None:
            self.audio.play("click")
            self.start_level(next(d for d in DIFFICULTIES if d.key == act))

    def update_pause(self, dt, inp):
        act = self.pause_menu.update(inp)
        if pygame.K_ESCAPE in inp.pressed:
            act = "resume"
        if pygame.K_r in inp.pressed:
            act = "restart"
        if act == "resume":
            self.state = PLAYING
        elif act == "restart":
            self.start_level(self.difficulty)
        elif act == "difficulty":
            self.state = DIFFICULTY
        elif act == "quit":
            self.running = False

    def update_victory(self, dt, inp):
        self.particles.update(dt)
        act = self.victory_menu.update(inp)
        p = inp.pressed
        if pygame.K_r in p:
            act = "restart"
        elif pygame.K_n in p and self.next_difficulty() is not None:
            act = "next"
        elif pygame.K_d in p or pygame.K_ESCAPE in p:
            act = "difficulty"
        elif pygame.K_q in p:
            act = "quit"
        if act == "restart":
            self.start_level(self.difficulty)
        elif act == "next":
            self.start_level(self.next_difficulty())
        elif act == "difficulty":
            self.state = DIFFICULTY
        elif act == "quit":
            self.running = False

    # ---------- jogo ----------
    def update_play(self, dt, inp):
        lv, p = self.level, self.player
        if pygame.K_ESCAPE in inp.pressed:
            self.state = PAUSED
            return
        if pygame.K_r in inp.pressed:
            self.start_level(self.difficulty)
            return
        self.elapsed += dt
        self.hit_cd = max(0.0, self.hit_cd - dt)
        for rock in lv.rocks.values():
            rock.shake = max(0.0, rock.shake - dt)
        self.toast = (self.toast[0], self.toast[1] - dt)
        self.banner = (self.banner[0], self.banner[1] - dt)

        # movimento: teclado/gesto têm prioridade sobre o caminho do mouse
        if inp.move != (0.0, 0.0):
            self.pending = None
            p.walk(dt, inp.move, lv)
        else:
            p.follow_path(dt, lv)

        self.hover = self.object_at(inp.mouse_pos)
        self.focus = self.compute_focus()

        if inp.hit:
            self.hit_focus()
        if inp.point is not None:
            self.point_hit(inp.point)
        if inp.interact:
            self.interact_nearby()
        if inp.click:
            self.handle_click(inp.click)
        self.run_pending()

        # coleta por contato
        for cr in lv.crystals:
            if not cr.collected and distance(p.x, p.y, cr.x, cr.y) <= CONTACT_RADIUS:
                self.collect(cr)

        self.hint = self.compute_hint()
        self.particles.update(dt)

        if lv.exit_open and p.tile == lv.exit_tile:
            self.win()

    def object_at(self, pos):
        mx, my = pos[0], pos[1] - HUD_H
        if not (0 <= mx < MAP_W and 0 <= my < MAP_H):
            return None
        lv = self.level
        for cr in lv.crystals:
            if not cr.collected and distance(mx, my, cr.x, cr.y) <= 22:
                return ("crystal", cr)
        tile = lv.tile_at(mx, my)
        if tile in lv.rocks:
            return ("rock", tile)
        if tile == lv.exit_tile:
            return ("exit", tile)
        if not lv.is_solid(*tile):
            return ("floor", tile)
        return None

    def compute_focus(self):
        """Rocha à frente do jogador (perto e na direção em que ele olha)."""
        p, lv = self.player, self.level
        best, best_d = None, 1e9
        for tile in lv.rocks:
            cx, cy = lv.tile_center(*tile)
            d = distance(p.x, p.y, cx, cy)
            if d <= TILE * 1.35 and d > 0:
                dot = ((cx - p.x) * p.facing[0] + (cy - p.y) * p.facing[1]) / d
                if dot > 0.55 and d < best_d:
                    best, best_d = tile, d
        return best

    def compute_hint(self):
        lv, p = self.level, self.player
        if self.focus is not None:
            return "Espaço, clique, martelada ou apontar o dedo para quebrar"
        for cr in lv.crystals:
            if not cr.collected and distance(p.x, p.y, cr.x, cr.y) <= REACH:
                return "E, clique ou mão fechada para coletar"
        ex, ey = lv.tile_center(*lv.exit_tile)
        if distance(p.x, p.y, ex, ey) <= TILE * 2.2:
            if lv.exit_open:
                return "A saída está livre: entre nela!"
            return "Saída bloqueada: colete todos os cristais"
        return ""

    # ---------- ações ----------
    def hit_focus(self):
        if self.focus is None:
            self.say("Nenhuma rocha à frente")
            return
        self.do_hit(self.focus)

    def point_hit(self, direction):
        """Gesto de apontar: golpeia a rocha próxima mais alinhada com a direção do dedo."""
        p, lv = self.player, self.level
        dx, dy = direction
        n = math.hypot(dx, dy)
        if n < 0.01:
            return
        dx, dy = dx / n, dy / n
        p.facing = (dx, dy)
        best, best_d = None, 1e9
        for tile in lv.rocks:
            cx, cy = lv.tile_center(*tile)
            d = distance(p.x, p.y, cx, cy)
            if 0 < d <= REACH and ((cx - p.x) * dx + (cy - p.y) * dy) / d > 0.7 and d < best_d:
                best, best_d = tile, d
        if best is None:
            self.say("Aponte para uma rocha próxima")
        else:
            self.do_hit(best)

    def do_hit(self, tile):
        if self.hit_cd > 0:
            return
        self.hit_cd = HIT_COOLDOWN
        lv = self.level
        cx, cy = lv.tile_center(*tile)
        result = lv.hit_rock(tile)
        if result == "hit":
            self.particles.emit(cx, cy, (190, 160, 130), 8, 110, 0.5, 3)
            self.audio.play("hit")
        elif result == "broken":
            self.particles.emit(cx, cy, (190, 160, 130), 28, 190, 0.8, 4)
            self.particles.emit(cx, cy, (255, 200, 120), 10, 150, 0.6, 2)
            self.particles.text(cx, cy - 20, "Rocha quebrada!", GOLD)
            self.audio.play("break")

    def interact_nearby(self):
        p = self.player
        near = [cr for cr in self.level.crystals
                if not cr.collected and distance(p.x, p.y, cr.x, cr.y) <= REACH]
        if near:
            self.collect(min(near, key=lambda c: distance(p.x, p.y, c.x, c.y)))
        else:
            self.say("Nada para coletar por perto")

    def collect(self, crystal):
        lv = self.level
        if not lv.collect_crystal(crystal):
            return
        self.particles.emit(crystal.x, crystal.y, (140, 240, 255), 24, 170, 0.8, 3, gravity=60)
        self.particles.text(crystal.x, crystal.y - 24, "+1 cristal", CYAN)
        self.audio.play("crystal")
        if lv.exit_open:
            ex, ey = lv.tile_center(*lv.exit_tile)
            self.particles.emit(ex, ey, (160, 255, 190), 40, 200, 1.0, 3, gravity=-40)
            self.banner = ("Saída liberada!", 3.0)
            self.audio.play("exit")

    def handle_click(self, pos):
        lv, p = self.level, self.player
        obj = self.object_at(pos)
        if obj is None:
            return
        kind, val = obj
        if kind == "crystal":
            if distance(p.x, p.y, val.x, val.y) <= REACH:
                self.collect(val)
            else:
                self.walk_to({(val.col, val.row)}, ("collect", val))
        elif kind == "rock":
            cx, cy = lv.tile_center(*val)
            if distance(p.x, p.y, cx, cy) <= REACH:
                self.do_hit(val)
            else:
                goals = {(val[0] + dc, val[1] + dr) for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1))
                         if not lv.is_solid(val[0] + dc, val[1] + dr)}
                self.walk_to(goals, ("hit", val))
        elif kind == "exit":
            if lv.exit_open:
                self.walk_to({val}, None)
            else:
                self.say("A saída está bloqueada: colete todos os cristais")
        else:
            self.walk_to({val}, None)

    def walk_to(self, goals, pending):
        path = self.level.find_path(self.player.tile, goals)
        if path is None:
            self.say("Caminho bloqueado por rochas: quebre-as primeiro")
            self.pending = None
            return
        self.player.path = path
        self.player._stuck = 0.0
        self.pending = pending

    def run_pending(self):
        if not self.pending or self.player.path:
            return
        kind, target = self.pending
        self.pending = None
        lv, p = self.level, self.player
        if kind == "hit" and target in lv.rocks:
            cx, cy = lv.tile_center(*target)
            if distance(p.x, p.y, cx, cy) <= REACH:
                self.do_hit(target)
        elif kind == "collect" and not target.collected:
            if distance(p.x, p.y, target.x, target.y) <= REACH:
                self.collect(target)

    def win(self):
        lv = self.level
        score = lv.compute_score(self.elapsed)
        key = self.difficulty.key
        new_best = score > self.best.get(key, -1)
        if new_best:
            self.best[key] = score
        self.result = {"score": score, "time": self.elapsed, "best": self.best[key], "new_best": new_best}
        self.audio.play("win")
        px, py = self.player.x, self.player.y
        self.particles.emit(px, py, (255, 230, 120), 50, 240, 1.2, 3, gravity=80)
        self._build_victory_menu()
        self.state = VICTORY

    # ---------- desenho ----------
    def draw(self):
        s = self.screen
        if self.state in (MENU, DIFFICULTY):
            self.draw_menu_screens(s)
            return
        self.draw_game(s)
        if self.state == PAUSED:
            self.dim(s)
            draw_text(s, "PAUSA", self.fonts.h1, WHITE, (SCREEN_W // 2, 200), "center")
            self.pause_menu.draw(s, self.fonts, self.t)
            draw_text(s, "ESC: continuar   R: reiniciar   M: câmera", self.fonts.small, MUTED,
                      (SCREEN_W // 2, 590), "center")
        elif self.state == VICTORY:
            self.dim(s, 190)
            self.draw_victory(s)

    @staticmethod
    def dim(surf, alpha=150):
        veil = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        veil.fill((6, 4, 16, alpha))
        surf.blit(veil, (0, 0))

    def draw_menu_screens(self, s):
        s.blit(self.menu_bg, (0, 0))
        self.ambience.draw(s, self.t)
        cx = SCREEN_W // 2
        if self.state == MENU:
            glow = 0.5 + 0.5 * math.sin(self.t * 2)
            draw_text(s, TITLE, self.fonts.title, (int(170 + 60 * glow), int(140 + 60 * glow), 255),
                      (cx, 120), "center")
            goal = ("Explore a caverna fantástica, quebre rochas para abrir caminho, colete todos os "
                    "cristais e encontre a saída!")
            for i, line in enumerate(wrap_text(goal, self.fonts.body, 700)):
                draw_text(s, line, self.fonts.body, WHITE, (cx, 215 + i * 30), "center")
            self.main_menu.draw(s, self.fonts, self.t)
            tips = ["Teclado: WASD/setas mover · Espaço golpear · E coletar · M câmera · R reiniciar · ESC pausa",
                    "Mouse: clique no chão para andar · clique em rochas e cristais · botões dos menus",
                    "Gestos (opcional, tecla M): mão ao lado/acima/abaixo move · queda rápida = martelada"]
            for i, line in enumerate(tips):
                draw_text(s, line, self.fonts.tiny, MUTED, (cx, 585 + i * 22), "center")
            self.draw_camera_status(s, (cx, 20), "midtop")
        else:
            draw_text(s, "Escolha a dificuldade", self.fonts.h1, WHITE, (cx, 90), "center")
            draw_text(s, "Mouse, setas/WASD e Enter · ESC volta", self.fonts.small, MUTED, (cx, 140), "center")
            self.diff_menu.draw(s, self.fonts, self.t)

    def draw_game(self, s):
        s.fill((10, 8, 20))
        world = s.subsurface((0, HUD_H, MAP_W, MAP_H))
        focus = self.focus if self.state == PLAYING else None
        self.renderer.draw(world, self.player, self.t, focus, self.hover if self.state == PLAYING else None,
                           self.particles, self.fonts)
        self.draw_hud(s)
        self.draw_overlays(s)

    def draw_hud(self, s):
        lv, d = self.level, self.difficulty
        pygame.draw.rect(s, (22, 16, 42), (0, 0, SCREEN_W, HUD_H))
        pygame.draw.line(s, (110, 80, 180), (0, HUD_H - 1), (SCREEN_W, HUD_H - 1), 2)
        draw_text(s, "Dificuldade: " + d.name, self.fonts.h2, d.color, (16, 10))
        draw_text(s, "Rochas quebradas: %d" % lv.rocks_broken, self.fonts.tiny, MUTED, (16, 46))
        done = lv.collected >= lv.total_crystals
        draw_text(s, "Cristais: %d/%d" % (lv.collected, lv.total_crystals), self.fonts.h1,
                  (140, 255, 170) if done else CYAN, (SCREEN_W // 2, 34), "center")
        right = SCREEN_W - 16
        if self.draw_camera_preview(s):
            right = SCREEN_W - PREVIEW_W - 12
        m, sec = divmod(int(self.elapsed), 60)
        draw_text(s, "Tempo %02d:%02d" % (m, sec), self.fonts.h2, WHITE, (right, 10), "topright")
        self.draw_camera_status(s, (right, 46), "topright")

    def draw_camera_preview(self, s):
        """Miniatura da câmera no canto da barra superior (não cobre o mapa), com cruz de mira."""
        snap = self.hand.snapshot()
        if snap["status"] != "active" or snap["frame"] is None:
            return False
        data, w, h = snap["frame"]
        try:
            img = pygame.image.frombuffer(data, (w, h), "RGB")
        except (ValueError, pygame.error):
            return False
        x0, y0 = SCREEN_W - w, 0
        s.blit(img, (x0, y0))
        # marca discreta do centro (zona neutra de movimento)
        pygame.draw.line(s, (200, 200, 220), (x0 + w // 2 - 4, y0 + h // 2), (x0 + w // 2 + 4, y0 + h // 2), 1)
        pygame.draw.line(s, (200, 200, 220), (x0 + w // 2, y0 + h // 2 - 4), (x0 + w // 2, y0 + h // 2 + 4), 1)
        aim = snap["aim"]
        color = (80, 255, 120) if snap["hand"] else (120, 100, 160)
        if aim is not None and snap["hand"]:
            ax = x0 + int(max(0.0, min(1.0, aim[0])) * (w - 1))
            ay = y0 + int(max(0.0, min(1.0, aim[1])) * (h - 1))
            color = (255, 170, 60) if snap["pointing"] else (80, 255, 120)
            pygame.draw.circle(s, color, (ax, ay), 8, 2)
            pygame.draw.line(s, color, (ax - 11, ay), (ax + 11, ay), 2)    # cruz de mira
            pygame.draw.line(s, color, (ax, ay - 11), (ax, ay + 11), 2)
        pygame.draw.rect(s, color, (x0, y0, w, h), 2)
        return True

    def camera_text(self):
        snap = self.hand.snapshot()
        st = snap["status"]
        if st == "off":
            return "Câmera: desligada (M)", MUTED
        if st == "starting":
            return "Câmera: iniciando...", GOLD
        if st == "error":
            return "Câmera indisponível: " + snap["message"][:34], (255, 120, 120)
        if snap["hand"]:
            return "Câmera ativa · mão detectada", (140, 255, 170)
        return "Câmera ativa · sem mão", GOLD

    def draw_camera_status(self, s, pos, anchor):
        text, color = self.camera_text()
        draw_text(s, text, self.fonts.tiny, color, pos, anchor)

    def draw_overlays(self, s):
        if self.state != PLAYING:
            return
        if self.hint:
            r = draw_text(s, self.hint, self.fonts.body, WHITE, (SCREEN_W // 2, SCREEN_H - 28), "center",
                          shadow=False)
            box = r.inflate(28, 14)
            pill = pygame.Surface(box.size, pygame.SRCALPHA)
            pygame.draw.rect(pill, (20, 14, 40, 200), pill.get_rect(), border_radius=12)
            s.blit(pill, box)
            draw_text(s, self.hint, self.fonts.body, WHITE, (SCREEN_W // 2, SCREEN_H - 28), "center")
        if self.toast[1] > 0:
            draw_text(s, self.toast[0], self.fonts.body, GOLD, (SCREEN_W // 2, HUD_H + 22), "center")
        if self.gesture_msg[1] > 0:
            draw_text(s, self.gesture_msg[0], self.fonts.small, (140, 255, 170), (16, HUD_H + 10))
        if self.banner[1] > 0:
            a = min(1.0, self.banner[1])
            col = tuple(int(v * a) for v in (150, 255, 190))
            draw_text(s, self.banner[0], self.fonts.h1, col, (SCREEN_W // 2, HUD_H + 90), "center")

    def draw_victory(self, s):
        cx = SCREEN_W // 2
        lv, r = self.level, self.result
        draw_text(s, "Vitória!", self.fonts.title, GOLD, (cx, 105), "center")
        draw_text(s, "Você encontrou a saída da Fantasy Cave!", self.fonts.body, WHITE, (cx, 175), "center")
        m, sec = divmod(int(r["time"]), 60)
        lines = ["Dificuldade: %s" % self.difficulty.name,
                 "Cristais coletados: %d/%d" % (lv.collected, lv.total_crystals),
                 "Tempo: %02d:%02d   ·   Rochas quebradas: %d" % (m, sec, lv.rocks_broken),
                 "Pontuação: %d%s" % (r["score"], "  (novo recorde!)" if r["new_best"] else
                                      "   ·   Melhor: %d" % r["best"])]
        for i, line in enumerate(lines):
            draw_text(s, line, self.fonts.h2 if i in (0, 3) else self.fonts.body,
                      self.difficulty.color if i == 0 else WHITE, (cx, 235 + i * 36), "center")
        self.victory_menu.draw(s, self.fonts, self.t)
        self.particles.draw(s, self.fonts)
