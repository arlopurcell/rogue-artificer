from __future__ import annotations

import random
from typing import TYPE_CHECKING, Optional, Tuple

from rogue_artificer import color, exceptions
from rogue_artificer.item import Item, Armor, ArmorSlot

if TYPE_CHECKING:
    from rogue_artificer.engine import Engine
    from rogue_artificer.entity import Actor, Entity

class Action:
    def __init__(self, entity: Actor) -> None:
        super().__init__()
        self.actor = entity

    @property
    def engine(self) -> Engine:
        return self.actor.parent.engine
    
    def perform(self) -> int:
       """Perform this action with the objects needed to determine its scope.

       This method must be overridden by Action subclasses.
       returns the number of ticks the action will delay the actor
       """
       raise NotImplementedError()


class WaitAction(Action):
    def perform(self) -> int:
        return 10 # TODO make this delay just until the next ai moves somehow

class TakeStairsAction(Action):
    def perform(self) -> int:
        """
        Take the stairs, if any exist at the entity's location.
        """
        if (self.actor.x, self.actor.y) == self.engine.game_map.downstairs_location:
            self.engine.game_world.generate_floor()
            self.engine.message_log.add_message(
                "You descend the staircase.", color.descend
            )
            return self.actor.move_delay
        else:
            raise exceptions.Impossible("There are no stairs here.")

class ActionWithDirection(Action):
    def __init__(self, entity: Actor, dx: int, dy: int):
        super().__init__(entity)

        self.dx = dx
        self.dy = dy

    def perform(self) -> int:
        raise NotImplementedError()

    @property
    def dest_xy(self) -> Tuple[int, int]:
        return self.actor.x + self.dx, self.actor.y + self.dy

    @property
    def blocking_entity(self) -> Optional[Entity]:
        return self.engine.game_map.get_blocking_entity_at_location(*self.dest_xy)

    @property
    def target_actor(self) -> Optional[Actor]:
        """Return the actor at this action's destination"""
        return self.engine.game_map.get_actor_at_location(*self.dest_xy)

class MeleeAction(ActionWithDirection):
    def perform(self) -> int:
        target = self.target_actor
        if not target:
            raise exceptions.Impossible("Nothing to attack")

        damage = random.randint(1, self.actor.melee_damage) - random.randint(0, target.defense)

        attack_desc = f"{self.actor.name.capitalize()} attacks {target.name}"
        attack_color = color.player_atk if self.actor is self.engine.player else color.enemy_atk
        if damage > 0:
            self.engine.message_log.add_message(
                f"{attack_desc} for {damage}",
                attack_color,
            )
            target.fighter.hp -= damage
        else:
            self.engine.message_log.add_message(f"{attack_desc} but does no damage", attack_color)
        return self.actor.melee_delay

class MovementAction(ActionWithDirection):
    def perform(self) -> int:
        dest_x, dest_y = self.dest_xy
        if not self.engine.game_map.in_bounds(dest_x, dest_y):
            raise exceptions.Impossible("That's the edge of the world")
        if not self.engine.game_map.tiles["walkable"][dest_x, dest_y]:
            raise exceptions.Impossible("There's a wall there")
        if self.engine.game_map.get_blocking_entity_at_location(dest_x, dest_y):
            raise exceptions.Impossible("Something is in the way")

        self.actor.move(self.dx, self.dy)
        return self.actor.move_delay

class BumpAction(ActionWithDirection):
    def perform(self) -> int:
        if self.target_actor:
            return MeleeAction(self.actor, self.dx, self.dy).perform()
        else:
            return MovementAction(self.actor, self.dx, self.dy).perform()

class PickupAction(Action):
    """Pickup an item and add it to the inventory, if there is room for it."""
 
    def __init__(self, entity: Actor):
        super().__init__(entity)
 
    def perform(self) -> int:
        actor_location_x = self.actor.x
        actor_location_y = self.actor.y
        inventory = self.actor.inventory
 
        for item in self.engine.game_map.items:
            if actor_location_x == item.x and actor_location_y == item.y:
                if len(inventory.items) >= inventory.capacity:
                    raise exceptions.Impossible("Your inventory is full.")
 
                self.engine.game_map.entities.remove(item)
                inventory.add(item)
 
                self.engine.message_log.add_message(f"You picked up the {item.name}!")
                return 10
 
        raise exceptions.Impossible("There is nothing here to pick up.")

class ItemAction(Action):
    def __init__(
        self, entity: Actor, item_key: str, target_xy: Optional[Tuple[int, int]] = None
    ):
        super().__init__(entity)
        self.item_key = item_key
        if not target_xy:
            target_xy = entity.x, entity.y
        self.target_xy = target_xy
 
    @property
    def target_actor(self) -> Optional[Actor]:
        """Return the actor at this actions destination."""
        return self.engine.game_map.get_actor_at_location(*self.target_xy)
 
    def perform(self) -> int:
        """Invoke the items ability, this action will be given to provide context."""
        raise NotImplementedError()


class QuaffAction(ItemAction):
    def perform(self) -> int:
        item = self.actor.inventory.get_one(self.item_key)
        if item.consumable and item.consumable.is_quaffable:
            item.consumable.activate(self)
            self.actor.inventory.consume_key(self.item_key)
            return 10
        else:
            raise exceptions.Impossible("You can't drink that")


class DropItem(ItemAction):
    def perform(self) -> int:
        self.actor.inventory.drop(self.item_key)
        return 10


class WieldAction(ItemAction):
    def perform(self) -> int:
        self.actor.inventory.wield(self.item_key)
        return 10

class WearAction(ItemAction):
    def perform(self) -> int:
        item = self.actor.inventory.get_one(self.item_key)
        if isinstance(item, Armor):
            self.actor.inventory.wear(self.item_key)
            return 10
        else:
            raise exceptions.Impossible("You can't wear that")
