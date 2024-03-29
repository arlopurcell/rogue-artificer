from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Tuple

from rogue_artificer import color, exceptions

if TYPE_CHECKING:
    from rogue_artificer.engine import Engine
    from rogue_artificer.entity import Actor, Entity, Item

class Action:
    def __init__(self, entity: Actor) -> None:
        super().__init__()
        self.entity = entity

    @property
    def engine(self) -> Engine:
        return self.entity.parent.engine
    
    def perform(self) -> None:
       """Perform this action with the objects needed to determine its scope.

       This method must be overridden by Action subclasses.
       """
       raise NotImplementedError()


class WaitAction(Action):
    def perform(self) -> None:
        pass

class TakeStairsAction(Action):
    def perform(self) -> None:
        """
        Take the stairs, if any exist at the entity's location.
        """
        if (self.entity.x, self.entity.y) == self.engine.game_map.downstairs_location:
            self.engine.game_world.generate_floor()
            self.engine.message_log.add_message(
                "You descend the staircase.", color.descend
            )
        else:
            raise exceptions.Impossible("There are no stairs here.")

class ActionWithDirection(Action):
    def __init__(self, entity: Actor, dx: int, dy: int):
        super().__init__(entity)

        self.dx = dx
        self.dy = dy

    def perform(self) -> None:
        raise NotImplementedError()

    @property
    def dest_xy(self) -> Tuple[int, int]:
        return self.entity.x + self.dx, self.entity.y + self.dy

    @property
    def blocking_entity(self) -> Optional[Entity]:
        return self.engine.game_map.get_blocking_entity_at_location(*self.dest_xy)

    @property
    def target_actor(self) -> Optional[Actor]:
        """Return the actor at this action's destination"""
        return self.engine.game_map.get_actor_at_location(*self.dest_xy)

class MeleeAction(ActionWithDirection):
    def perform(self) -> None:
        target = self.target_actor
        if not target:
            raise exceptions.Impossible("Nothing to attack")

        damage = self.entity.fighter.power - target.fighter.defense

        attack_desc = f"{self.entity.name.capitalize()} attacks {target.name}"
        attack_color = color.player_atk if self.entity is self.engine.player else color.enemy_atk
        if damage > 0:
            self.engine.message_log.add_message(
                f"{attack_desc} for {damage}",
                attack_color,
            )
            target.fighter.hp -= damage
        else:
            self.engine.message_log.add_message(f"{attack_desc} but does no damage", attack_color)

class MovementAction(ActionWithDirection):
    def perform(self) -> None:
        dest_x, dest_y = self.dest_xy
        if not self.engine.game_map.in_bounds(dest_x, dest_y):
            raise exceptions.Impossible("That's the edge of the world")
        if not self.engine.game_map.tiles["walkable"][dest_x, dest_y]:
            raise exceptions.Impossible("There's a wall there")
        if self.engine.game_map.get_blocking_entity_at_location(dest_x, dest_y):
            raise exceptions.Impossible("Somethig is in the way")

        self.entity.move(self.dx, self.dy)

class BumpAction(ActionWithDirection):
    def perform(self) -> None:
        if self.target_actor:
            return MeleeAction(self.entity, self.dx, self.dy).perform()
        else:
            return MovementAction(self.entity, self.dx, self.dy).perform()

class PickupAction(Action):
    """Pickup an item and add it to the inventory, if there is room for it."""
 
    def __init__(self, entity: Actor):
        super().__init__(entity)
 
    def perform(self) -> None:
        actor_location_x = self.entity.x
        actor_location_y = self.entity.y
        inventory = self.entity.inventory
 
        for item in self.engine.game_map.items:
            if actor_location_x == item.x and actor_location_y == item.y:
                if len(inventory.items) >= inventory.capacity:
                    raise exceptions.Impossible("Your inventory is full.")
 
                self.engine.game_map.entities.remove(item)
                inventory.add(item)
 
                self.engine.message_log.add_message(f"You picked up the {item.name}!")
                return
 
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
 
    def perform(self) -> None:
        """Invoke the items ability, this action will be given to provide context."""
        raise NotImplementedError()


class QuaffAction(ItemAction):
    def perform(self) -> None:
        item = self.entity.inventory.get_one(self.item_key)
        if item.consumable and item.consumable.is_quaffable:
            item.consumable.activate(self)
            self.entity.inventory.consume_key(self.item_key)
        else:
            raise exceptions.Impossible("You can't drink that")


class DropItem(ItemAction):
    def perform(self) -> None:
        self.entity.inventory.drop(self.item_key)

