from __future__ import annotations

from typing import List, TYPE_CHECKING, Optional

from rogue_artificer.components.base_component import BaseComponent
from rogue_artificer.exceptions import Impossible

if TYPE_CHECKING:
    from rogue_artificer.entity import Actor
    from rogue_artificer.item import Item


ALL_KEYS = "abcdefghijklmnopqrstuvwxyz"

class Inventory(BaseComponent):
    parent: Actor

    def __init__(self, capacity: int):
        self.capacity = capacity
        self.items: dict[str, list[Item]] = {}
        self.wielded_key: Optional[str] = None

    def drop(self, key: str) -> None:
        """
        Removes an item from the inventory and restores it to the game map, at the player's current location.
        """
        item_stack = self.items[key]
        del self.items[key]
        for item in item_stack:
            item.place(self.parent.x, self.parent.y, self.game_map)

        if len(item_stack) > 1:
            self.engine.message_log.add_message(f"You dropped {len(item_stack)} {item_stack[0].name}s.")
        else:
            self.engine.message_log.add_message(f"You dropped the {item_stack[0].name}.")

    def consume(self, item: Item) -> None:
        for k, v in self.items.items():
            if v[0].name == item.name:
                self.consume_key(k)
                break

    def consume_key(self, key: str) -> None:
        self.items[key].pop()
        if not self.items[key]:
            del self.items[key]

    def add(self, item: Item) -> None:
        added_to_stack = False
        for stack in self.items.values():
            if stack[0].name == item.name:
                stack.append(item)
                item.parent = self
                added_to_stack = True
                break

        if not added_to_stack:
            added = False
            for key in ALL_KEYS:
                if key not in self.items:
                    self.items[key] = [item]
                    item.parent = self
                    added = True
                    break
            if not added:
                raise Impossible("Inventory is full")

    def get_one(self, key: str) -> Item:
        return self.items[key][0]

    def wield(self, key: str) -> None:
        self.wielded_key = key

    @property
    def wielded(self) -> Optional[Item]:
        return self.items[self.wielded_key][0] if self.wielded_key else None
