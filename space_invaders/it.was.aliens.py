#!/usr/bin/env python3
import enum
import time
import curses
import random
import logging
from dataclasses import dataclass

from typing import Optional, List, Dict, Tuple

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

Known Bugs:
    - If you hold a key configured with InputManager, initial keypress is recognized, then
      the key is seen as "released", but then will correctly detect it as being "held" again soon thereafter.

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

BORDER_WIDTH: int = (
    1  # Eh... please don't change this for now. Multi-cell width borders are blegh.
)
TRUE_BOARD_WIDTH = BOARD_WIDTH + 2 * BORDER_WIDTH
TRUE_BOARD_HEIGHT = BOARD_HEIGHT + 2 * BORDER_WIDTH


# Logging


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter("[%(asctime)s][%(levelname)s] %(message)s")

file_handler = logging.FileHandler(LOG_PATH)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)

logger.addHandler(file_handler)


# Enums


class EntityType(enum.Enum):
    PLAYER = 0
    ENEMY = 1
    OBSTACLE = 2
    BORDER = 3


class InputType(enum.Enum):
    MOVEMENT = 0
    FIRE = 1
    QUIT = 2
    PAUSE = 3


# Classes


class Entity:
    symbol: str
    color: int
    entity_type: EntityType

    position: Tuple[int, int]  # y,x as per curses format

    def __init__(self, symbol: str, color: int, entity_type: EntityType):
        global TRUE_BOARD_WIDTH, TRUE_BOARD_HEIGHT
        self.TRUE_BOARD_WIDTH = TRUE_BOARD_WIDTH
        self.TRUE_BOARD_HEIGHT = TRUE_BOARD_HEIGHT

        self.symbol = symbol
        self.color = color
        self.entity_type = entity_type

    def setInitialPosition(self, y, x):
        self.position = (y, x)

    """
    All move* methods will error out if the destination
    of the move is either already occupied or out of bounds.
    """

    def moveLeft(self, board):
        self.__move(board, 0, -1)

    def moveRight(self, board):
        self.__move(board, 0, +1)

    def moveUp(self, board):
        self.__move(board, -1, 0)  # Curses uses quadrant IV instead of the usual I

    def moveDown(self, board):
        self.__move(board, +1, 0)

    def __move(self, board, dy, dx):
        old_y, old_x = self.position
        new_y, new_x = (old_y + dy, old_x + dx)
        if (
            new_x <= 0
            or new_x >= self.TRUE_BOARD_WIDTH - 1
            or new_y <= 0
            or new_y >= self.TRUE_BOARD_HEIGHT - 1
        ):
            raise Exception("Entity is being moved out of bounds!")

        if board.getPos(new_y, new_x) != None:
            raise Exception("Destination cell is already occupied!")

        logger.info(f"Moved from old pos {old_y},{old_x} to new pos {new_y},{new_x}")

        board.setPos(old_y, old_x, None)
        board.setPos(new_y, new_x, self)

        self.position = (new_y, new_x)


"""
I created an inputmanager class to handle the somewhat confusing behavior of
curses' input buffer and its interaction with the "tick" mechanism. Since the way
a game's handles input in a slow tick-rate game is inherently differently from how one
navigates graphical user interfaces in realtime, this "wrapper" makes interacting with
curses' getch() a little closer to say using Unity's Input Manager

The following describes the InputManager's behavior.

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


class InputManager:
    stdscr: curses.window  # type: ignore

    """
    Do we still need the buffer functionality? Might not need it depending on execution flow in SpaceInvaders.run()
    """
    buffer_cleared: Dict[InputType, bool] = {
        InputType.MOVEMENT: False,
        InputType.FIRE: False,
        InputType.QUIT: False,
        InputType.PAUSE: False,
    }

    last_pressed: Dict[InputType, int] = {
        InputType.MOVEMENT: curses.ERR,
        InputType.FIRE: curses.ERR,
        InputType.QUIT: curses.ERR,
        InputType.PAUSE: curses.ERR,
    }

    groups: Dict[InputType, List[int]] = {
        InputType.MOVEMENT: [ord("w"), ord("a"), ord("s"), ord("d")],
        InputType.FIRE: [ord(" ")],
        InputType.QUIT: [ord("q")],
        InputType.PAUSE: [ord("p")],
    }

    reverse_group_lookup: Dict[int, InputType] = {}

    def __init__(self, stdscr):
        self.stdscr = stdscr

        for input_type, keys in self.groups.items():
            for key in keys:
                self.reverse_group_lookup[key] = input_type

    def shouldQuit(self):
        last_pressed_key_for_quit = self.getLastPressedKeyForGroup(
            InputType.QUIT, False
        )
        return last_pressed_key_for_quit == ord("q")

    def storeInput(self) -> None:
        key = self.stdscr.getch()

        # If curses.ERR, no key was pressed.
        while key != curses.ERR:
            if key in self.reverse_group_lookup:
                # If the key pressed is not a key defined in our InputManager,
                # ignore and get next buffered key
                group = self.reverse_group_lookup[key]
                self.last_pressed[group] = key
                self.buffer_cleared[group] = False

            key = self.stdscr.getch()

    def getLastPressedKeyForGroup(
        self, input_type: InputType, clear_buffer: bool = True
    ) -> int:
        if self.buffer_cleared[input_type]:
            return curses.ERR
        else:
            key = self.last_pressed[input_type]

            if clear_buffer:
                self.buffer_cleared[input_type] = True
            return key


class Board:
    board: List[List[Optional[Entity]]]

    def __init__(self, player: Entity, enemies: List[Entity], num_enemies: int) -> None:
        self.__copyGlobalSettings()
        self.__initializeBoard()
        self.__populateBoard(player, enemies, num_enemies)

    def __initializeBoard(self) -> None:
        """
        Initialize the board with empty cells and draw border
        """
        board: List[List[Optional[Entity]]] = [
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

    def __populateBoard(
        self, player: Entity, enemies: List[Entity], num_enemies: int
    ) -> None:
        """
        Place entities on the board
        - Player
        - Enemies
        - TODO: Obstacles
        """

        # Place player
        player_y = self.BOARD_HEIGHT - 1
        player_x = self.BOARD_WIDTH // 2
        self.setPos(player_y, player_x, player)
        player.setInitialPosition(player_y, player_x)

        for i in range(num_enemies):
            enemy = random.choice(enemies)
            enemy_y = i // self.BOARD_WIDTH
            enemy_x = i % self.BOARD_WIDTH
            self.setPos(enemy_y, enemy_x, enemy)

    def __copyGlobalSettings(self) -> None:
        """
        Not the prettiest but floaty globals are icky too.
        Needs to all be one gist so no config yamls either.
        Gross.
        """

        global BORDER_WIDTH, BOARD_HEIGHT, BOARD_WIDTH
        global TRUE_BOARD_HEIGHT, TRUE_BOARD_WIDTH

        self.BORDER_WIDTH = BORDER_WIDTH
        self.BOARD_HEIGHT = BOARD_HEIGHT
        self.BOARD_WIDTH = BOARD_WIDTH
        self.TRUE_BOARD_HEIGHT = TRUE_BOARD_HEIGHT
        self.TRUE_BOARD_WIDTH = TRUE_BOARD_WIDTH

    def getBoard(self) -> List[List[Optional[Entity]]]:
        return self.board

    def getPos(self, y: int, x: int) -> Optional[Entity]:
        return self.board[y][x]

    def setPos(self, y: int, x: int, entity: Optional[Entity]) -> None:
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


class SpaceInvaders:
    stdscr: curses.window  # type: ignore

    player: Entity
    enemies: List[Entity]

    player_pos: Tuple[int, int]

    is_paused: bool = False

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

    def __init__(self, _stdscr) -> None:
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

        self.board = Board(self.player, self.enemies, self.ENEMY_COUNT)

    def __del__(self) -> None:
        self.stdscr.keypad(False)

        curses.nocbreak()
        curses.echo()
        curses.endwin()
        curses.curs_set(True)

    def copyGlobalSettings(self) -> None:
        """
        Not the prettiest but floaty globals are icky too.
        Needs to all be one gist so no config yamls either.
        Gross.
        """

        global BORDER_WIDTH, BOARD_HEIGHT, BOARD_WIDTH
        global TRUE_BOARD_HEIGHT, TRUE_BOARD_WIDTH
        global ENEMY_COUNT, TICKS_PER_MINUTE

        self.BORDER_WIDTH = BORDER_WIDTH
        self.BOARD_HEIGHT = BOARD_HEIGHT
        self.BOARD_WIDTH = BOARD_WIDTH
        self.TRUE_BOARD_HEIGHT = TRUE_BOARD_HEIGHT
        self.TRUE_BOARD_WIDTH = TRUE_BOARD_WIDTH
        self.ENEMY_COUNT = ENEMY_COUNT
        self.TICKS_PER_MINUTE = TICKS_PER_MINUTE

    def ensureScreenLargeEnough(self) -> None:
        """
        Maybe can just throw in __init__()?
        """
        if curses.LINES < self.BOARD_HEIGHT or curses.COLS < self.BOARD_WIDTH:
            raise Exception(
                f"Screen is not large enough. Please increase so there is a minimum of {self.BOARD_WIDTH} x {self.BOARD_HEIGHT}"
            )

    def initializeEntities(self) -> None:
        """
        Ehh... Kinda unnecessary rn
        TODO: Check for fallback chars - ie cannot display unicode? Maybe hard cuz clientside rendering? Args?
        """

        self.player = Entities.PLAYER
        self.enemies = Entities.ENEMIES

    #######################
    # Game Loop Functions #
    #######################

    def run(self) -> None:
        """
        NOTE:
            This is a _naive_ implementation of "ticks" or general time keeping.

            There are definitely more robust ways to do this, but this should be sufficient for now.
        """

        def new_tick_start() -> bool:
            return target_tick_dur_milli < time.time_ns() - curr_tick_start_milli

        target_tick_dur_milli = 60 * 1000 / self.TICKS_PER_MINUTE
        curr_tick_start_milli = time.time_ns()

        min_delay = 0.5  # seconds

        while True:
            self.inputManager.storeInput()

            if self.inputManager.shouldQuit():
                break

            if new_tick_start():
                curr_tick_start_milli = time.time_ns()

                if not self.is_paused:
                    logger.debug(f"New tick started at: {curr_tick_start_milli}")
                    self.update()

                self.draw()

            time.sleep(min_delay)

    def updatePlayer(self, pressed_key: int) -> None:
        if pressed_key == ord("a"):
            logger.info("Moving ship to the left")
            self.player.moveLeft(self.board)
        elif pressed_key == ord("d"):
            logger.info("Moving ship to the right")
            self.player.moveRight(self.board)

    def updateEnemies(self) -> None:
        pass

    def togglePause(self) -> None:
        self.is_paused = not self.is_paused

    def update(self) -> None:
        logger.info("Input:")
        for group in InputType:
            pressed_key = self.inputManager.getLastPressedKeyForGroup(group)
            logger.info(f"{InputType(group).name}: {pressed_key}")

            if pressed_key == curses.ERR:
                # No input. Check next group.
                continue

            if group == InputType.PAUSE:
                self.togglePause()

            if group in (InputType.MOVEMENT, InputType.FIRE):
                self.updatePlayer(pressed_key)

        self.updateEnemies()

    def draw(self) -> None:
        for y, row_data in enumerate(self.board.getBoard()):
            for x, entity in enumerate(row_data):
                if entity is not None:
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
