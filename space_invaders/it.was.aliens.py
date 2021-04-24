#!/usr/bin/env python3
import enum
import time
import curses
import random
import logging
from dataclasses import dataclass

from typing import Optional, List

"""
Notes/Assumptions:
    - Will error out if screen size is smaller than grid size
    - If screen size is large than grid size, will display the grid anchored to upper left corner.
"""

# Configs
# BOARD_HEIGHT: int = 5
# BOARD_WIDTH: int = 5
BOARD_HEIGHT: int = 25
BOARD_WIDTH: int = 25
ENEMY_COUNT: int = BOARD_WIDTH * 2
# ENEMY_COUNT: int = 100
TICKS_PER_MINUTE: int = 120

LOG_PATH = "it.was.aliens.log"

#########################
# No touchy beyond here #
#########################

# Logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter("[%(asctime)s][%(levelname)s] %(message)s")

file_handler = logging.FileHandler(LOG_PATH)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)

logger.addHandler(file_handler)

# Internal Vars
BORDER_WIDTH = (
    1  # Eh... please don't change this for now. Multi-cell width borders are blegh.
)

PLAYER_SYMBOL = "♕"
PLAYER_SYMBOL_FALLBACK = "P"  # Player
PLAYER_COLOR = curses.COLOR_RED
SHOOT_TICK = 1 # Number of ticks for "bullet" to travel forward one cell
SHOOT_DELAY = 2 # Can shoot once every SHOOT_DELAY ticks.

ENEMY_SYMBOL = "☠"
ENEMY_SYMBOL_FALLBACK = "A"  # Aliens
ENEMY_COLORS = [
    curses.COLOR_GREEN,
    curses.COLOR_YELLOW,
    curses.COLOR_BLUE,
    curses.COLOR_MAGENTA,
]

# TODO: Obstacles?

class EntityType(enum.Enum):
    PLAYER = 0
    ENEMY = 1
    OBSTACLE = 2
    BORDER = 3

# "Structs"
@dataclass
class Entity:
    symbol: str
    color: int
    entity_type: EntityType

# Muh Codes


class Borders:
    VERTICAL = Entity("║", curses.COLOR_WHITE, EntityType.BORDER)
    HORIZONTAL = Entity("═", curses.COLOR_WHITE, EntityType.BORDER)
    TOP_LEFT = Entity("╔", curses.COLOR_WHITE, EntityType.BORDER)
    TOP_RIGHT = Entity("╗", curses.COLOR_WHITE, EntityType.BORDER)
    BOT_LEFT = Entity("╚", curses.COLOR_WHITE, EntityType.BORDER)
    BOT_RIGHT = Entity("╝", curses.COLOR_WHITE, EntityType.BORDER)


class Entities:
    PLAYER: Entity = Entity(PLAYER_SYMBOL, PLAYER_COLOR, EntityType.PLAYER)
    ENEMIES: List[Entity] = [Entity(ENEMY_SYMBOL, color, EntityType.ENEMY) for color in ENEMY_COLORS]


class SpaceInvaders:
    stdscr: curses.window # type: ignore
    board: List[List[Optional[Entity]]]


    def __init__(self, _stdscr):
        self.stdscr = _stdscr
        self.stdscr.keypad(True)

        curses.start_color()
        curses.noecho()
        curses.cbreak()
        curses.curs_set(False)

        self.copyGlobals()
        self.ensureScreenLargeEnough()
        self.initializeEntities()
        self.initializeBoard()
        self.populateBoard()

    def copyGlobals(self):
        """
            Not the prettiest but floaty globals are icky too.
            Needs to all be one gist so no config yamls either.
            Gross.
        """

        global BORDER_WIDTH
        self.BORDER_WIDTH = BORDER_WIDTH

        global BOARD_HEIGHT, BOARD_WIDTH, ENEMY_COUNT, TICKS_PER_MINUTE
        self.BOARD_HEIGHT = BOARD_HEIGHT
        self.BOARD_WIDTH = BOARD_WIDTH
        self.TRUE_BOARD_HEIGHT = BOARD_HEIGHT + 2 * BORDER_WIDTH
        self.TRUE_BOARD_WIDTH = BOARD_WIDTH + 2 * BORDER_WIDTH
        self.ENEMY_COUNT = ENEMY_COUNT
        self.TICKS_PER_MINUTE = TICKS_PER_MINUTE

        global PLAYER_SYMBOL, PLAYER_SYMBOL_FALLBACK, PLAYER_COLOR
        self.PLAYER_SYMBOL = PLAYER_SYMBOL
        self.PLAYER_SYMBOL_FALLBACK = PLAYER_SYMBOL_FALLBACK
        self.PLAYER_COLOR = PLAYER_COLOR

        global ENEMY_SYMBOL, ENEMY_SYMBOL_FALLBACK, ENEMY_COLOR
        self.ENEMY_SYMBOL = ENEMY_SYMBOL
        self.ENEMY_SYMBOL_FALLBACK = ENEMY_SYMBOL_FALLBACK
        self.ENEMY_COLORS = ENEMY_COLORS

    def ensureScreenLargeEnough(self):
        """
            Maybe can just throw in __init__()?
        """
        if curses.LINES < self.BOARD_HEIGHT or curses.COLS < self.BOARD_WIDTH:
            raise Exception(
                f"Screen is not large enough. Please increase so there is a minimum of {self.BOARD_WIDTH} x {self.BOARD_HEIGHT}"
            )

    def __del__(self):
        self.stdscr.keypad(False)

        curses.nocbreak()
        curses.echo()
        curses.endwin()
        curses.curs_set(True)

    def initializeEntities(self):
        """
            Ehh... Kinda unnecessary rn
            TODO: Check for fallback chars - ie cannot display unicode? Maybe hard cuz clientside rendering? Args?
        """

        self.player: Entity = Entities.PLAYER
        self.enemies: List[Entity] = Entities.ENEMIES


    def initializeBoard(self):
        """
            Initialize the board with empty cells and draw border
        """
        board: List[List[BoardCell]] = [
            [None] * self.TRUE_BOARD_WIDTH
            for _ in range(self.TRUE_BOARD_HEIGHT)
        ]

        assert self.BORDER_WIDTH == 1

        # Vertical borders
        right_border_x = self.TRUE_BOARD_WIDTH - 1
        for y in range(1, self.TRUE_BOARD_HEIGHT - 1):  # Don't draw vertical in corners
            board[y][0] = Borders.VERTICAL
            board[y][right_border_x] = Borders.VERTICAL

        # Horizontal borders
        bot_border_y = self.TRUE_BOARD_HEIGHT - 1
        for x in range(1, self.TRUE_BOARD_WIDTH - 1):
            board[0][x] = Borders.HORIZONTAL
            board[bot_border_y][x] = Borders.HORIZONTAL

        # Corners
        max_x = self.TRUE_BOARD_WIDTH - 1
        max_y = self.TRUE_BOARD_HEIGHT - 1
        board[0][0] = Borders.TOP_LEFT
        board[0][max_x] = Borders.TOP_RIGHT
        board[max_y][0] = Borders.BOT_LEFT
        board[max_y][max_x] = Borders.BOT_RIGHT

        self.board = board

    def updateBoardCell(self, y: int, x: int, entity: Entity):
        """
            While we have a config for BOARD_WIDTH/HEIGHT, we also draw a border which
            makes us have a true width/height greater than the supplied values (unless border width = 0)

            As such this is a helper function to update self.board but using the "game coordinates"
            ie ignoring the borders
        """
        assert y >= 0 and y < self.BOARD_HEIGHT
        assert x >= 0 and x < self.BOARD_WIDTH

        true_y = y + self.BORDER_WIDTH
        true_x = x + self.BORDER_WIDTH

        self.board[true_y][true_x] = entity

    def populateBoard(self):
        """
            Place entities on the board
            - Player
            - Enemies
            - TODO: Obstacles
        """

        # Place player
        player_y = self.BOARD_HEIGHT - 1
        player_x = self.BOARD_WIDTH // 2
        self.updateBoardCell(player_y, player_x, self.player)

        for i in range(self.ENEMY_COUNT):
            enemy = random.choice(self.enemies)
            enemy_y = i // self.BOARD_WIDTH
            enemy_x = i % self.BOARD_WIDTH
            self.updateBoardCell(enemy_y, enemy_x, enemy)

    def run(self):
        self.draw()
        time.sleep(5)
        return

    def draw(self):
        for y, row_data in enumerate(self.board):
            for x, entity in enumerate(row_data):
                if entity is not None:
                    logger.debug(
                        f"Drawing entity at {y},{x} with symbol `{entity.symbol}` and color `{entity.color}`"
                    )
                    self.stdscr.addch(y, x, entity.symbol, entity.color)
                else:
                    self.stdscr.addch(y, x, " ")

        self.stdscr.refresh()


def main(stdscr):
    game = SpaceInvaders(stdscr)
    game.run()
    del game


if __name__ == "__main__":
    curses.wrapper(main)
