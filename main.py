"""Ponto de entrada do Fantasy Cave. Execute com: python main.py"""
import sys


def main():
    try:
        import pygame  # noqa: F401
    except ImportError:
        print("Pygame não está instalado. Rode: pip install pygame")
        sys.exit(1)
    from src.game import Game
    Game().run()


if __name__ == "__main__":
    main()
