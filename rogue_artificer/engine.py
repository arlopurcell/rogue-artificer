from __future__ import annotations

from typing import TYPE_CHECKING

from tcod.context import Context
from tcod.console import Console
from tcod.map import compute_fov

from rogue_artificer.input_handlers import EventHandler

if TYPE_CHECKING:
    from rogue_artificer.entity import Entity
    from rogue_artificer.game_map import GameMap


class Engine:
    game_map: GameMap

    def __init__(self, player: Entity):
        self.event_handler = EventHandler(self)
        self.player = player

    def handle_enemy_turns(self) -> None:
        for entity in self.game_map.entities:
            if entity == self.player:
                continue

            print(f"The {entity.name} wonders when it'll get a real turn")

    def update_fov(self) -> None:
       """Recompute the visible area based on the players point of view."""
       self.game_map.visible[:] = compute_fov(
           self.game_map.tiles["transparent"],
           (self.player.x, self.player.y),
           radius=8,
       )
       # If a tile is "visible" it should be added to "explored".
       self.game_map.explored |= self.game_map.visible

    def render(self, console: Console, context: Context) -> None:
        self.game_map.render(console)
        context.present(console)
        console.clear()
