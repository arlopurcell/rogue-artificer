from __future__ import annotations

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from rogue_artificer.engine import Engine
    from rogue_artificer.entity import Entity
    from rogue_artificer.game_map import GameMap


class BaseComponent:
    parent: Entity  # Owning entity instance.

    @property
    def game_map(self) -> GameMap:
        return self.parent.game_map

    @property
    def engine(self) -> Engine:
        return self.game_map.engine
