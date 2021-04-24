#!/usr/bin/env python3
import enum
import time
import curses
import random
import logging
from dataclasses import dataclass

from typing import Optional, List, Dict

"""
What Is:
    - Space Invaders implemented with curses and Python 3.x

What For:
    - Pair Programming Task for applying to the Recurse Center

Currently Does:
    - Configurable board size
    - Configurable enemy count
    - Configurable tick length
    - Border on game board
    - Quitting

Features To Implement:
    - Shooting/Destroying enemies

Notes/Assumptions:
    - Will error out if screen size is smaller than grid size
    - If screen size is large than grid size, will display the grid anchored to upper left corner.

InputManager:
    - The input manager functions by defining a series of "groups" of keys.
      These are currently:
        - "Movement keys"
        - "Fire key"
        - "Quit"
    - Retrieving the "last pressed key" in a given tick duration (ie, one update() call) is actually "get the last pressed key for group X".
        - In other words, given one tick duration there can be up to N "most recently pressed keys"
          where N is the number of input groups defined (3, for now).
    - If multiple keys are pressed in the duration of one tick, the newest pressed key will be returned
      for each group.
        - If a key in the group was not pressed, curses.ERR is returned instead.
        - Eg, assuming "wasd" are the direction keys and "space" is the fire key:
          If the keys "wd[space]" are pressed during one tick duration then the "latest pressed key"
          for the "fire" group would be the spacebar and the key for the "movement" group would be "d" while
          the "quit" group would return curses.ERR.

"""

###########
# Configs #
###########

BOARD_HEIGHT: int = 25
BOARD_WIDTH: int = 25
ENEMY_COUNT: int = BOARD_WIDTH * 2
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


# Structs/Enums


class EntityType(enum.Enum):
    PLAYER = 0
    ENEMY = 1
    OBSTACLE = 2
    BORDER = 3


@dataclass
class Entity:
    symbol: str
    color: int
    entity_type: EntityType


# Classes


class InputType(enum.Enum):
    MOVEMENT = 0
    FIRE = 1
    QUIT = 2


class InputManager:
    stdscr: curses.window  # type: ignore

    buffer_cleared: Dict[InputType, bool] = {
        InputType.MOVEMENT: False,
        InputType.FIRE: False,
        InputType.QUIT: False,
    }

    last_pressed: Dict[InputType, Optional[int]] = {
        InputType.MOVEMENT: None,
        InputType.FIRE: None,
        InputType.QUIT: None,
    }

    groups: Dict[InputType, List[int]] = {
        InputType.MOVEMENT: [ord("w"), ord("a"), ord("s"), ord("d")],
        InputType.FIRE: [ord(" ")],
        InputType.QUIT: [ord("q")],
    }

    reverse_group_lookup: Dict[int, InputType]

    def __init__(self, stdscr):
        self.stdscr = stdscr

        for input_type, keys in self.groups.items():
            for key in keys:
                self.reverse_group_lookup[key] = input_type

    def shouldQuit(self):
        last_pressed_key_for_quit = self.getLastPressedKeyForGroup(InputType.QUIT)
        logger.debug(
            f"Should quit? last_pressed: {last_pressed_key_for_quit} - q: {ord('q')}"
        )
        return last_pressed_key_for_quit == ord("q")

    def getInput(self):
        key = self.stdscr.getch()

        # If curses.ERR, no key was pressed.
        logger.debug(key)
        while key != curses.ERR:
            group = self.reverse_group_lookup[key]
            self.last_pressed[group] = key

            self.buffer_cleared = False

            key = self.stdscr.getch()

    def getLastPressedKeyForGroup(
        self, input_type: InputType, clear_buffer: bool = True
    ) -> Optional[int]:
        if self.buffer_cleared[input_type]:
            return None
        else:
            key = self.last_pressed[input_type]

            if clear_buffer:
                self.buffer_cleared[input_type] = True
            return key


class SpaceInvaders:
    stdscr: curses.window  # type: ignore
    board: List[List[Optional[Entity]]]

    BORDER_WIDTH: int = (
        1  # Eh... please don't change this for now. Multi-cell width borders are blegh.
    )
    SHOOT_TICK: int = 1  # Number of ticks for "bullet" to travel forward one cell
    SHOOT_DELAY: int = 2  # Can shoot once every SHOOT_DELAY ticks.

    PLAYER_SYMBOL: str = "♕"
    PLAYER_SYMBOL_FALLBACK: str = "P"
    PLAYER_COLOR: int = curses.COLOR_RED

    ENEMY_SYMBOL: str = "☠"
    ENEMY_SYMBOL_FALLBACK: str = "A"
    ENEMY_COLORS: List[int] = [
        curses.COLOR_GREEN,
        curses.COLOR_YELLOW,
        curses.COLOR_BLUE,
        curses.COLOR_MAGENTA,
    ]

    def __init__(self, _stdscr):
        self.stdscr = _stdscr
        self.stdscr.keypad(True)
        self.stdscr.nodelay(True)

        curses.start_color()
        curses.noecho()
        curses.cbreak()
        curses.curs_set(False)

        self.inputManager = InputManager(self.stdscr)

        self.copyGlobalSettings()
        self.ensureScreenLargeEnough()
        self.initializeEntities()
        self.initializeBoard()
        self.populateBoard()

    def __del__(self):
        self.stdscr.keypad(False)

        curses.nocbreak()
        curses.echo()
        curses.endwin()
        curses.curs_set(True)

    def copyGlobalSettings(self):
        """
        Not the prettiest but floaty globals are icky too.
        Needs to all be one gist so no config yamls either.
        Gross.
        """

        global BOARD_HEIGHT, BOARD_WIDTH, ENEMY_COUNT, TICKS_PER_MINUTE
        self.BOARD_HEIGHT = BOARD_HEIGHT
        self.BOARD_WIDTH = BOARD_WIDTH
        self.TRUE_BOARD_HEIGHT = BOARD_HEIGHT + 2 * self.BORDER_WIDTH
        self.TRUE_BOARD_WIDTH = BOARD_WIDTH + 2 * self.BORDER_WIDTH
        self.ENEMY_COUNT = ENEMY_COUNT
        self.TICKS_PER_MINUTE = TICKS_PER_MINUTE

    def ensureScreenLargeEnough(self):
        """
        Maybe can just throw in __init__()?
        """
        if curses.LINES < self.BOARD_HEIGHT or curses.COLS < self.BOARD_WIDTH:
            raise Exception(
                f"Screen is not large enough. Please increase so there is a minimum of {self.BOARD_WIDTH} x {self.BOARD_HEIGHT}"
            )

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
            [None] * self.TRUE_BOARD_WIDTH for _ in range(self.TRUE_BOARD_HEIGHT)
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
        """
        NOTE:
            This is a _naive_ implementation of "ticks" or general time keeping.

            There are definitely more robust ways to do this, but this should be sufficient for now.
        """

        target_tick_dur_milli = 60 * 1000 / self.TICKS_PER_MINUTE
        curr_tick_start_milli = time.time_ns()

        min_delay = 0.5  # seconds

        def new_tick_start() -> bool:
            return target_tick_dur_milli < time.time_ns() - curr_tick_start_milli

        while True:
            self.inputManager.getInput()

            if new_tick_start():
                curr_tick_start_milli = time.time_ns()
                logger.debug(f"New tick started at: {curr_tick_start_milli}")

                self.update()
                self.draw()

            if self.inputManager.shouldQuit():
                break

            time.sleep(min_delay)

    def update(self):
        pressed_key = self.inputManager.getLastPressedKey()
        logger.info(f"Key was pressed: {pressed_key}")
        pass

    def draw(self):
        for y, row_data in enumerate(self.board):
            for x, entity in enumerate(row_data):
                if entity is not None:
                    # logger.debug(
                    #    f"Drawing entity at {y},{x} with symbol `{entity.symbol}` and color `{entity.color}`"
                    # )
                    self.stdscr.addch(y, x, entity.symbol, entity.color)
                else:
                    self.stdscr.addch(y, x, " ")

        self.stdscr.refresh()


class Borders:
    VERTICAL = Entity("║", curses.COLOR_WHITE, EntityType.BORDER)
    HORIZONTAL = Entity("═", curses.COLOR_WHITE, EntityType.BORDER)
    TOP_LEFT = Entity("╔", curses.COLOR_WHITE, EntityType.BORDER)
    TOP_RIGHT = Entity("╗", curses.COLOR_WHITE, EntityType.BORDER)
    BOT_LEFT = Entity("╚", curses.COLOR_WHITE, EntityType.BORDER)
    BOT_RIGHT = Entity("╝", curses.COLOR_WHITE, EntityType.BORDER)


class Entities:
    PLAYER: Entity = Entity(
        SpaceInvaders.PLAYER_SYMBOL, SpaceInvaders.PLAYER_COLOR, EntityType.PLAYER
    )
    ENEMIES: List[Entity] = [
        Entity(SpaceInvaders.ENEMY_SYMBOL, color, EntityType.ENEMY)
        for color in SpaceInvaders.ENEMY_COLORS
    ]


###############
# Entry Point #
###############


def main(stdscr):
    game = SpaceInvaders(stdscr)
    game.run()
    del game


if __name__ == "__main__":
    curses.wrapper(main)
