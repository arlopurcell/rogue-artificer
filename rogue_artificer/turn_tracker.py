import heapq

from typing import Iterable
from rogue_artificer.entity import Actor, Entity

class TurnTracker:
    def __init__(self, entities: Iterable[Entity]):
        # ELements are tuples of [tick, entry_counter, actor] where:
        # tick is the game tick on which the actor should next act
        # entry_counter is just a counter for each time something is added to the heap. this is to ensure stability of the heap so that actors with the same tick will act in the order in which they were added
        # actor is the actor which should act
        self.actor_heap: list[tuple[int, int, Actor]] = []
        self.entry_counter: int = 0
        self.current_tick = 0

        for entity in entities:
            if isinstance(entity, Actor):
                heapq.heappush(self.actor_heap, (0, self.entry_counter, entity))
                self.entry_counter += 1

    def push(self, actor: Actor, delay: int):
        heapq.heappush(self.actor_heap, (self.current_tick + delay, self.entry_counter, actor))
        self.entry_counter += 1

    def pop(self) -> Actor:
        tick, _, actor = heapq.heappop(self.actor_heap)
        self.current_tick = tick
        return actor


