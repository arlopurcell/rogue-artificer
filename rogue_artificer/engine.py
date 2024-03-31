from __future__ import annotations

from typing import TYPE_CHECKING
import lzma
import pickle

from tcod.console import Console
from tcod.map import compute_fov

from rogue_artificer import exceptions
from rogue_artificer import render_functions
from rogue_artificer.message_log import MessageLog

if TYPE_CHECKING:
    from rogue_artificer.entity import Actor
    from rogue_artificer.game_map import GameMap, GameWorld


class Engine:
    game_map: GameMap
    game_world: GameWorld

    def __init__(self, player: Actor):
        self.message_log = MessageLog()
        self.mouse_location: tuple[int, int] = (0, 0)
        self.player = player

    def handle_enemy_turns(self) -> None:
        while True:
            if not self.player.is_alive:
                return

            actor = self.game_map.turn_tracker.pop()
            if not actor.is_alive:
                continue
            if actor == self.player:
                return
            if actor.ai:
                delay = 10 # default value in case action fails
                try:
                    delay = actor.ai.perform()
                except exceptions.Impossible as e:
                    print(e)

                self.game_map.turn_tracker.push(actor, delay)

    def update_fov(self) -> None:
       """Recompute the visible area based on the players point of view."""
       self.game_map.visible[:] = compute_fov(
           self.game_map.tiles["transparent"],
           (self.player.x, self.player.y),
           radius=8,
       )
       # If a tile is "visible" it should be added to "explored".
       self.game_map.explored |= self.game_map.visible

    def render(self, console: Console) -> None:
        self.game_map.render(console)

        self.message_log.render(console=console, x=21, y=45, width=40, height=5)

        render_functions.render_bar(
                console=console,
                current_value=self.player.fighter.hp,
                maximum_value=self.player.fighter.max_hp,
                total_width=20,
        )

        render_functions.render_dungeon_level(
                console=console,
                dungeon_level=self.game_world.current_floor,
                location=(0, 47),
        )

        render_functions.render_names_at_mouse_location(console=console, x=21, y=44, engine=self)
        
    def save_as(self, filename: str) -> None:
        """Save this Engine instance as a compressed file."""
        save_data = lzma.compress(pickle.dumps(self))
        with open(filename, "wb") as f:
            f.write(save_data)
