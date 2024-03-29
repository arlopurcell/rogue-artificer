from typing import Optional, Tuple

from rogue_artificer.entity import Entity 
from rogue_artificer.components.consumable import Consumable
from rogue_artificer.render_order import RenderOrder

class Item(Entity):
    def __init__(
        self,
        *,
        x: int = 0,
        y: int = 0,
        char: str = "?",
        color: Tuple[int, int, int] = (255, 255, 255),
        name: str = "<Unnamed>",
        consumable: Optional[Consumable],
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
