from __future__ import annotations

from typing import List, Tuple, TYPE_CHECKING, Optional

import random
import numpy as np  # type: ignore
import tcod

from rogue_artificer.actions import Action, MeleeAction, MovementAction, WaitAction, BumpAction

if TYPE_CHECKING:
    from rogue_artificer.entity import Actor


class BaseAI(Action):
    actor: Actor

    def perform(self) -> int:
        raise NotImplementedError()

    def get_path_to(self, dest_x: int, dest_y: int) -> List[Tuple[int, int]]:
        """Compute and return a path to the target position.

        If there is no valid path then returns an empty list.
        """
        # Copy the walkable array.
        cost = np.array(self.actor.parent.tiles["walkable"], dtype=np.int8)

        for entity in self.actor.parent.entities:
            # Check that an enitiy blocks movement and the cost isn't zero (blocking.)
            if entity.blocks_movement and cost[entity.x, entity.y]:
                # Add to the cost of a blocked position.
                # A lower number means more enemies will crowd behind each other in
                # hallways.  A higher number means enemies will take longer paths in
                # order to surround the player.
                cost[entity.x, entity.y] += 10

        # Create a graph from the cost array and pass that graph to a new pathfinder.
        graph = tcod.path.SimpleGraph(cost=cost, cardinal=2, diagonal=3)
        pathfinder = tcod.path.Pathfinder(graph)

        pathfinder.add_root((self.actor.x, self.actor.y))  # Start position.

        # Compute the path to the destination and remove the starting point.
        path: List[List[int]] = pathfinder.path_to((dest_x, dest_y))[1:].tolist()

        # Convert from List[List[int]] to List[Tuple[int, int]].
        return [(index[0], index[1]) for index in path]

class HostileEnemy(BaseAI):
    def __init__(self, actor: Actor):
        super().__init__(actor)
        self.path: List[Tuple[int, int]] = []

    def perform(self) -> int:
        target = self.engine.player
        dx = target.x - self.actor.x
        dy = target.y - self.actor.y
        distance = max(abs(dx), abs(dy)) # Chebyshev distance

        if self.engine.game_map.visible[self.actor.x, self.actor.y]:
            if distance <= 1:
                return MeleeAction(self.actor, dx, dy).perform()
            
            self.path = self.get_path_to(target.x, target.y)

        if self.path:
            dest_x, dest_y = self.path.pop(0)
            return MovementAction(self.actor, dest_x - self.actor.x, dest_y - self.actor.y).perform()

        return WaitAction(self.actor).perform()


class ConfusedEnemy(BaseAI):
    """
    A confused enemy will stumble around aimlessly for a given number of turns, then revert back to its previous AI.
    If an actor occupies a tile it is randomly moving into, it will attack.
    """
 
    def __init__(
        self, actor: Actor, previous_ai: Optional[BaseAI], turns_remaining: int
    ):
        super().__init__(actor)
 
        self.previous_ai = previous_ai
        self.turns_remaining = turns_remaining
 
    def perform(self) -> int:
        # Revert the AI back to the original state if the effect has run its course.
        if self.turns_remaining <= 0:
            self.engine.message_log.add_message(
                f"The {self.actor.name} is no longer confused."
            )
            self.actor.ai = self.previous_ai
            return 0
        else:
            # Pick a random direction
            direction_x, direction_y = random.choice(
                [
                    (-1, -1),  # Northwest
                    (0, -1),  # North
                    (1, -1),  # Northeast
                    (-1, 0),  # West
                    (1, 0),  # East
                    (-1, 1),  # Southwest
                    (0, 1),  # South
                    (1, 1),  # Southeast
                ]
            )
 
            self.turns_remaining -= 1
 
            # The actor will either try to move or attack in the chosen random direction.
            # Its possible the actor will just bump into the wall, wasting a turn.
            return BumpAction(self.actor, direction_x, direction_y,).perform()
