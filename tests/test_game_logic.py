"""Testes da lógica (sem janela): python -m unittest discover -s tests -v
O teste de fumaça com Pygame usa drivers de vídeo/áudio 'dummy' e é ignorado se o Pygame faltar."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import DIFFICULTIES, HUD_H, TILE
from src.hand_controller import GestureDetector
from src.level import Level
from src.player import Player


class LevelTests(unittest.TestCase):
    def test_layouts_match_difficulty(self):
        for d in DIFFICULTIES:
            lv = Level(d)
            self.assertEqual(lv.total_crystals, d.crystals, d.key)
            self.assertTrue(lv.is_solvable(), d.key)
            self.assertTrue(all(r.max_hp == d.rock_hits for r in lv.rocks.values()))

    def test_difficulty_progression(self):
        counts = [len(Level(d).rocks) for d in DIFFICULTIES]
        self.assertEqual(counts, sorted(counts))
        self.assertEqual([d.crystals for d in DIFFICULTIES], [5, 8, 12])
        self.assertEqual([d.rock_hits for d in DIFFICULTIES], [2, 3, 4])

    def test_rock_breaks_after_exact_hits(self):
        for d in DIFFICULTIES:
            lv = Level(d)
            tile = next(iter(lv.rocks))
            for _ in range(d.rock_hits - 1):
                self.assertEqual(lv.hit_rock(tile), "hit")
                self.assertTrue(lv.is_solid(*tile))
            self.assertEqual(lv.hit_rock(tile), "broken")
            self.assertFalse(lv.is_solid(*tile))
            self.assertIsNone(lv.hit_rock(tile))

    def test_crystal_collected_once_and_exit_unlocks(self):
        lv = Level(DIFFICULTIES[0])
        self.assertTrue(lv.is_solid(*lv.exit_tile))
        for i, cr in enumerate(lv.crystals):
            self.assertFalse(lv.exit_open)
            self.assertTrue(lv.collect_crystal(cr))
            self.assertFalse(lv.collect_crystal(cr))
            self.assertEqual(lv.collected, i + 1)
        self.assertTrue(lv.exit_open)
        self.assertFalse(lv.is_solid(*lv.exit_tile))

    def test_path_blocked_by_rocks_then_open(self):
        lv = Level(DIFFICULTIES[2])
        goal = lv.exit_tile
        lv.exit_open = True
        path = lv.find_path(lv.start_tile, {goal})
        if path is None:
            for tile in list(lv.rocks):
                while lv.hit_rock(tile) == "hit":
                    pass
            self.assertIsNotNone(lv.find_path(lv.start_tile, {goal}))


class PlayerTests(unittest.TestCase):
    def test_cannot_cross_wall_or_intact_rock(self):
        lv = Level(DIFFICULTIES[0])
        x, y = lv.tile_center(*lv.start_tile)
        p = Player(x, y, DIFFICULTIES[0].speed)
        for _ in range(120):
            p.walk(1 / 60, (-1, -1), lv)
        half = p.size / 2
        self.assertGreaterEqual(p.x - half, TILE - 0.01)
        self.assertGreaterEqual(p.y - half, TILE - 0.01)
        rock = next(iter(lv.rocks))
        cx, cy = lv.tile_center(*rock)
        p = Player(cx - TILE * 1.5, cy, DIFFICULTIES[0].speed)
        if lv.is_solid(*p.tile):
            self.skipTest("posição de teste ocupada")
        for _ in range(120):
            p.walk(1 / 60, (1, 0), lv)
        self.assertLessEqual(p.x + p.size / 2, rock[0] * TILE + 0.01 + (TILE if not lv.is_solid(*rock) else 0))
        self.assertNotEqual(p.tile, rock)

    def test_can_pass_after_breaking(self):
        lv = Level(DIFFICULTIES[0])
        rock = next(t for t in lv.rocks if not lv.is_solid(t[0] - 1, t[1]) and not lv.is_solid(t[0] + 1, t[1]))
        cx, cy = lv.tile_center(*rock)
        while lv.hit_rock(rock) == "hit":
            pass
        p = Player(cx - TILE, cy, DIFFICULTIES[0].speed)
        for _ in range(60):
            p.walk(1 / 60, (1, 0), lv)
        self.assertGreater(p.x, cx)


class GestureTests(unittest.TestCase):
    def test_hammer_detected_once_with_cooldown(self):
        g = GestureDetector()
        events, t = [], 0.0
        for i in range(10):          # mão parada no centro
            events += g.update(0.5, 0.35, False, t)
            t += 0.033
        self.assertEqual(events, [])
        for i in range(6):           # queda rápida
            events += g.update(0.5, 0.35 + 0.06 * (i + 1), False, t)
            t += 0.033
        self.assertEqual(events.count("hammer"), 1)
        for i in range(6):           # continua descendo logo depois: não repete (cooldown)
            events += g.update(0.5, 0.7 + 0.04 * i, False, t)
            t += 0.033
        self.assertEqual(events.count("hammer"), 1)

    def test_slow_motion_is_not_hammer(self):
        g = GestureDetector()
        events, t = [], 0.0
        for i in range(60):
            events += g.update(0.5, 0.3 + 0.005 * i, False, t)
            t += 0.033
        self.assertNotIn("hammer", events)

    def test_sideways_swing_is_hammer(self):
        for sign in (1, -1):
            g = GestureDetector()
            events, t = [], 0.0
            for i in range(8):
                events += g.update(0.5, 0.4, False, t)
                t += 0.033
            for i in range(5):       # varrida rápida para o lado
                events += g.update(0.5 + sign * 0.07 * (i + 1), 0.4, False, t)
                t += 0.033
            self.assertEqual(events.count("hammer"), 1, sign)

    def test_pointing_hits_repeatedly_in_finger_direction(self):
        g = GestureDetector()
        events, t = [], 0.0
        for i in range(40):          # ~1,3 s apontando para a direita
            events += g.update(0.5, 0.5, False, t, point_dir=(1.0, 0.0))
            t += 0.033
        points = [e for e in events if isinstance(e, tuple) and e[0] == "point"]
        self.assertGreaterEqual(len(points), 2)
        self.assertLessEqual(len(points), 3)
        self.assertGreater(points[0][1], 0.9)
        self.assertNotIn("hammer", events)
        self.assertNotIn("interact", events)
        self.assertEqual(g.move, (0.0, 0.0))

    def test_move_and_fist(self):
        g = GestureDetector()
        for i in range(20):
            g.update(0.85, 0.5, False, i * 0.033)
        self.assertGreater(g.move[0], 0.5)
        self.assertEqual(g.move[1], 0.0)
        ev = g.update(0.85, 0.5, True, 1.0)
        self.assertIn("interact", ev)
        self.assertNotIn("interact", g.update(0.85, 0.5, True, 1.05))


class SmokeTests(unittest.TestCase):
    def test_point_gesture_breaks_rock_headless(self):
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
        try:
            import pygame
        except ImportError:
            self.skipTest("pygame não instalado")
        from src.game import Game
        g = Game()
        g.start_level(DIFFICULTIES[0])
        lv = g.level
        tile = next(t for t in lv.rocks if not lv.is_solid(t[0] - 1, t[1]))
        cx, cy = lv.tile_center(*tile)
        g.player.x, g.player.y = cx - TILE, cy
        g.point_hit((1.0, 0.1))
        self.assertEqual(lv.rocks[tile].hp, lv.rocks[tile].max_hp - 1)
        g.hit_cd = 0
        g.point_hit((-1.0, 0.0))                       # apontando para longe da rocha: nada acontece
        self.assertEqual(lv.rocks[tile].hp, lv.rocks[tile].max_hp - 1)
        g.hand.shutdown()
        pygame.quit()

    def test_full_flow_headless(self):
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
        try:
            import pygame
        except ImportError:
            self.skipTest("pygame não instalado")
        from src.game import Game, MENU, DIFFICULTY, PLAYING, VICTORY, PAUSED

        g = Game()

        def key(k):
            return pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode="", scancode=0)

        def click(pos):
            return pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=1)

        def frames(n, ev=()):
            for i in range(n):
                g.step(1 / 60, list(ev) if i == 0 else [])

        frames(2)
        self.assertEqual(g.state, MENU)
        frames(1, [click(g.main_menu.buttons[0].rect.center)])
        self.assertEqual(g.state, DIFFICULTY)
        frames(1, [click(g.diff_menu.buttons[0].rect.center)])
        self.assertEqual(g.state, PLAYING)
        lv = g.level
        # golpe com espaço e com clique numa rocha
        tile = next(iter(lv.rocks))
        cx, cy = lv.tile_center(*tile)
        g.player.x, g.player.y = cx - TILE, cy
        g.player.facing = (1, 0)
        if lv.is_solid(*g.player.tile):
            self.skipTest("posição ocupada")
        frames(2)
        self.assertEqual(g.focus, tile)
        frames(1, [key(pygame.K_SPACE)])
        self.assertEqual(lv.rocks[tile].hp, lv.rocks[tile].max_hp - 1)
        frames(20)
        frames(1, [click((int(cx), int(cy) + HUD_H))])        # clique = golpe (rocha ao alcance)
        self.assertNotIn(tile, lv.rocks)
        # coleta tudo e vence
        for cr in lv.crystals:
            g.collect(cr)
        self.assertTrue(lv.exit_open)
        g.player.x, g.player.y = lv.tile_center(*lv.exit_tile)
        frames(2)
        self.assertEqual(g.state, VICTORY)
        frames(1, [key(pygame.K_d)])
        self.assertEqual(g.state, DIFFICULTY)
        frames(1, [key(pygame.K_RETURN)])
        self.assertEqual(g.state, PLAYING)
        frames(1, [key(pygame.K_ESCAPE)])
        self.assertEqual(g.state, PAUSED)
        frames(1, [key(pygame.K_r)])
        self.assertEqual(g.state, PLAYING)
        self.assertEqual(g.level.collected, 0)
        g.hand.shutdown()
        pygame.quit()


if __name__ == "__main__":
    unittest.main()
