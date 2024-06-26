from __future__ import annotations

import math
import copy
from typing import Tuple, Type, TypeVar, TYPE_CHECKING, Optional

from rogue_artificer.render_order import RenderOrder

if TYPE_CHECKING:
    from rogue_artificer.components.ai import BaseAI
    from rogue_artificer.components.consumable import Consumable
    from rogue_artificer.components.fighter import Fighter
    from rogue_artificer.components.inventory import Inventory
    from rogue_artificer.game_map import GameMap


T = TypeVar("T", bound="Entity")

class Entity:
    """
    A generic object to represent players, enemies, items, etc.
    """
    parent: GameMap | Inventory

    def __init__(
            self,
            game_map: Optional[GameMap] = None,
            x: int = 0,
            y: int = 0,
            char: str = "?",
            color: Tuple[int, int, int] = (255, 255, 255),
            name: str = "<Unnamed>",
            blocks_movement: bool = False,
            render_order: RenderOrder = RenderOrder.CORPSE,
    ):
        self.x = x
        self.y = y
        self.char = char
        self.color = color
        self.name = name
        self.blocks_movement = blocks_movement
        self.render_order = render_order
        if game_map:
            self.parent = game_map
            game_map.entities.append(self)

    @property
    def game_map(self) -> GameMap:
        return self.parent.game_map

    def spawn(self: T, game_map: GameMap, x: int, y: int) -> T:
        clone = copy.deepcopy(self)
        clone.x = x
        clone.y = y
        clone.parent = game_map
        game_map.entities.append(clone)
        return clone


    def place(self, x: int, y: int, game_map: Optional[GameMap] = None) -> None:
        """Place this entity at a new location.  Handles moving across GameMaps."""
        self.x = x
        self.y = y
        if game_map:
            if hasattr(self, "parent"):  # Possibly uninitialized.
                if self.parent is self.game_map:
                    self.parent.entities.remove(self)
            self.parent = game_map
            game_map.entities.append(self)
            
    def distance(self, x: int, y: int) -> float:
        """
        Return the distance between the current entity and the given (x, y) coordinate.
        """
        return math.sqrt((x - self.x) ** 2 + (y - self.y) ** 2)

    def move(self, dx: int, dy: int) -> None:
        # Move the entity by a given amount
        self.x += dx
        self.y += dy

class Actor(Entity):
    def __init__(
            self,
            *,
            x: int = 0,
            y: int = 0,
            char: str = "?",
            color: Tuple[int, int, int] = (255, 255, 255),
            name: str = "<Unnamed>",
            ai_cls: Type[BaseAI],
            fighter: Fighter,
            inventory: Inventory,
    ):
        super().__init__(
                x=x,
                y=y,
                char=char,
                color=color,
                name=name,
                blocks_movement=True,
                render_order=RenderOrder.ACTOR,
        )

        self.ai: Optional[BaseAI] = ai_cls(self)

        self.fighter = fighter
        self.fighter.parent = self

        self.inventory = inventory
        self.inventory.parent = self

    def __str__(self):
        return f"Actor [{self.name}]"

    def __repr__(self):
        return f"Actor [{self.name}]"


    def spawn(self: T, game_map: GameMap, x: int, y: int) -> T:
        clone = super().spawn(game_map, x, y)
        game_map.turn_tracker.push(clone, 0)
        return clone

    @property
    def is_alive(self) -> bool:
        """Returns True as long as this actor can perform actions."""
        return bool(self.ai)

    @property
    def move_delay(self) -> int:
        # TODO look at move speed modifiers in inventory
        return 10

    @property
    def melee_delay(self) -> int:
        # TODO look at melee speed modifiers in inventory
        return 10

    @property
    def melee_damage(self) -> int:
        weapon = self.inventory.wielded
        return weapon.melee_damage if weapon else self.fighter.unarmed_damage

    @property
    def defense(self) -> int:
        return self.fighter.base_defense + self.inventory.defense

