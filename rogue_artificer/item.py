from __future__ import annotations

from typing import Optional, Tuple, TYPE_CHECKING
from enum import auto, StrEnum

from rogue_artificer.entity import Entity 
from rogue_artificer.render_order import RenderOrder

if TYPE_CHECKING:
    from rogue_artificer.components.consumable import Consumable

class Item(Entity):
    def __init__(
        self,
        *,
        x: int = 0,
        y: int = 0,
        char: str = "?",
        color: Tuple[int, int, int] = (255, 255, 255),
        name: str = "<Unnamed>",
        consumable: Optional[Consumable] = None,
    ):
        super().__init__(
            x=x,
            y=y,
            char=char,
            color=color,
            name=name,
            blocks_movement=False,
            render_order=RenderOrder.ITEM,
        )
 
        self.consumable = consumable
        if self.consumable is not None:
            self.consumable.parent = self

    @property
    def melee_damage(self) -> int:
        return 1


class MeleeWeapon(Item):
    def __init__(
        self,
        *,
        color: Tuple[int, int, int] = (255, 255, 255),
        name: str,
        damage: int,
    ):
        super().__init__(color=color, name=name, char=")")
        self.damage = damage

    @property
    def melee_damage(self) -> int:
        return self.damage

class ArmorSlot(StrEnum):
    HEAD = auto()
    BODY = auto()
    HANDS = auto()
    FEET = auto()
    CLOAK = auto()

class Armor(Item):
    def __init__(
        self,
        *,
        color: Tuple[int, int, int] = (255, 255, 255),
        name: str,
        defense: int,
        slot: ArmorSlot,
    ):
        super().__init__(color=color, name=name, char="[")
        self.defense = defense
        self.slot = slot
