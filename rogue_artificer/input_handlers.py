from __future__ import annotations

from typing import Callable, Optional, TYPE_CHECKING, Tuple

import tcod.event
from tcod.event import KeySym
from tcod import libtcodpy

from rogue_artificer.actions import Action, BumpAction, WaitAction, PickupAction, DropItem
from rogue_artificer import color, exceptions

if TYPE_CHECKING:
    from rogue_artificer.engine import Engine
    from rogue_artificer.entity import Item

MOVE_KEYS = {
   # Arrow keys.
   KeySym.UP: (0, -1),
   KeySym.DOWN: (0, 1),
   KeySym.LEFT: (-1, 0),
   KeySym.RIGHT: (1, 0),
   KeySym.HOME: (-1, -1),
   KeySym.END: (-1, 1),
   KeySym.PAGEUP: (1, -1),
   KeySym.PAGEDOWN: (1, 1),
   # Numpad keys.
   KeySym.KP_1: (-1, 1),
   KeySym.KP_2: (0, 1),
   KeySym.KP_3: (1, 1),
   KeySym.KP_4: (-1, 0),
   KeySym.KP_6: (1, 0),
   KeySym.KP_7: (-1, -1),
   KeySym.KP_8: (0, -1),
   KeySym.KP_9: (1, -1),
   # Vi keys.
   KeySym.h: (-1, 0),
   KeySym.j: (0, 1),
   KeySym.k: (0, -1),
   KeySym.l: (1, 0),
   KeySym.y: (-1, -1),
   KeySym.u: (1, -1),
   KeySym.b: (-1, 1),
   KeySym.n: (1, 1),
}

PICKUP_KEYS = {
    KeySym.g,
    KeySym.COMMA,
}

WAIT_KEYS = {
   KeySym.PERIOD,
   KeySym.KP_5,
   KeySym.CLEAR,
   KeySym.s,
}

CONFIRM_KEYS = {
    KeySym.RETURN,
    KeySym.KP_ENTER,
}

CURSOR_Y_KEYS = {
   KeySym.UP: -1,
   KeySym.DOWN: 1,
   KeySym.PAGEUP: -10,
   KeySym.PAGEDOWN: 10,
}

class EventHandler(tcod.event.EventDispatch[Action]):
    def __init__(self, engine: Engine):
        self.engine = engine

    def handle_events(self, event: tcod.event.Event) -> None:
        self.handle_action(self.dispatch(event))
 
    def handle_action(self, action: Optional[Action]) -> bool:
        """Handle actions returned from event methods.
 
        Returns True if the action will advance a turn.
        """
        if action is None:
            return False
 
        try:
            action.perform()
        except exceptions.Impossible as exc:
            self.engine.message_log.add_message(exc.args[0], color.impossible)
            return False  # Skip enemy turn on exceptions.
 
        self.engine.handle_enemy_turns()
 
        self.engine.update_fov()
        return True

    def ev_mousemotion(self, event: tcod.event.MouseMotion) -> None:
        if self.engine.game_map.in_bounds(event.tile.x, event.tile.y):
            self.engine.mouse_location = event.tile.x, event.tile.y

    def ev_quit(self, event: tcod.event.Quit) -> Optional[Action]:
        raise SystemExit()

    def on_render(self, console: tcod.console.Console) -> None:
        self.engine.render(console)


class MainGameEventHandler(EventHandler):
    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[Action]:
        action: Optional[Action] = None

        key = event.sym
        player = self.engine.player

        if key in MOVE_KEYS:
            dx, dy = MOVE_KEYS[key]
            action = BumpAction(player, dx, dy)

        elif key in WAIT_KEYS:
            action = WaitAction(player)

        elif key == KeySym.ESCAPE:
            raise SystemExit()

        elif key == KeySym.v:
            self.engine.event_handler = HistoryViewer(self.engine)

        elif key in PICKUP_KEYS:
            action = PickupAction(player)

        elif key == KeySym.i:
            self.engine.event_handler = InventoryActivateHandler(self.engine)

        elif key == KeySym.d:
            self.engine.event_handler = InventoryDropHandler(self.engine)

        elif key == KeySym.SLASH:
            self.engine.event_handler = LookHandler(self.engine)

        # No valid key was pressed
        return action

class GameOverEventHandler(EventHandler):
    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[Action]:
        action: Optional[Action] = None

        key = event.sym

        if key == KeySym.ESCAPE:
            raise SystemExit()

        # No valid key was pressed
        return action



class HistoryViewer(EventHandler):
   """Print the history on a larger window which can be navigated."""

   def __init__(self, engine: Engine):
       super().__init__(engine)
       self.log_length = len(engine.message_log.messages)
       self.cursor = self.log_length - 1

   def on_render(self, console: tcod.console.Console) -> None:
       super().on_render(console)  # Draw the main state as the background.

       log_console = tcod.console.Console(console.width - 6, console.height - 6)

       # Draw a frame with a custom banner title.
       log_console.draw_frame(0, 0, log_console.width, log_console.height)
       log_console.print_box(
           0, 0, log_console.width, 1, "┤Message history├", alignment=libtcodpy.CENTER
       )

       # Render the message log using the cursor parameter.
       self.engine.message_log.render_messages(
           log_console,
           1,
           1,
           log_console.width - 2,
           log_console.height - 2,
           self.engine.message_log.messages[: self.cursor + 1],
       )
       log_console.blit(console, 3, 3)

   def ev_keydown(self, event: tcod.event.KeyDown) -> None:
       # Fancy conditional movement to make it feel right.
       if event.sym in CURSOR_Y_KEYS:
           adjust = CURSOR_Y_KEYS[event.sym]
           if adjust < 0 and self.cursor == 0:
               # Only move from the top to the bottom when you're on the edge.
               self.cursor = self.log_length - 1
           elif adjust > 0 and self.cursor == self.log_length - 1:
               # Same with bottom to top movement.
               self.cursor = 0
           else:
               # Otherwise move while staying clamped to the bounds of the history log.
               self.cursor = max(0, min(self.cursor + adjust, self.log_length - 1))
       elif event.sym == KeySym.HOME:
           self.cursor = 0  # Move directly to the top message.
       elif event.sym == KeySym.END:
           self.cursor = self.log_length - 1  # Move directly to the last message.
       else:  # Any other key moves back to the main game state.
           self.engine.event_handler = MainGameEventHandler(self.engine)

class AskUserEventHandler(EventHandler):
    """Handles user input for actions which require special input."""
 
    def handle_action(self, action: Optional[Action]) -> bool:
        """Return to the main event handler when a valid action was performed."""
        if super().handle_action(action):
            self.engine.event_handler = MainGameEventHandler(self.engine)
            return True
        return False
 
    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[Action]:
        """By default any key exits this input handler."""
        if event.sym in {  # Ignore modifier keys.
            KeySym.LSHIFT,
            KeySym.RSHIFT,
            KeySym.LCTRL,
            KeySym.RCTRL,
            KeySym.LALT,
            KeySym.RALT,
        }:
            return None
        return self.on_exit()
 
    def ev_mousebuttondown(self, event: tcod.event.MouseButtonDown) -> Optional[Action]:
        """By default any mouse click exits this input handler."""
        return self.on_exit()
 
    def on_exit(self) -> Optional[Action]:
        """Called when the user is trying to exit or cancel an action.
 
        By default this returns to the main event handler.
        """
        self.engine.event_handler = MainGameEventHandler(self.engine)
        return None

class InventoryEventHandler(AskUserEventHandler):
    """This handler lets the user select an item.
 
    What happens then depends on the subclass.
    """
 
    TITLE = "<missing title>"
 
    def on_render(self, console: tcod.console.Console) -> None:
        """Render an inventory menu, which displays the items in the inventory, and the letter to select them.
        Will move to a different position based on where the player is located, so the player can always see where
        they are.
        """
        super().on_render(console)
        number_of_items_in_inventory = len(self.engine.player.inventory.items)
 
        height = number_of_items_in_inventory + 2
 
        if height <= 3:
            height = 3
 
        if self.engine.player.x <= 30:
            x = 40
        else:
            x = 0
 
        y = 0
 
        width = len(self.TITLE) + 4
 
        console.draw_frame(
            x=x,
            y=y,
            width=width,
            height=height,
            title=self.TITLE,
            clear=True,
            fg=(255, 255, 255),
            bg=(0, 0, 0),
        )
 
        if number_of_items_in_inventory > 0:
            for i, item in enumerate(self.engine.player.inventory.items):
                item_key = chr(ord("a") + i)
                console.print(x + 1, y + i + 1, f"({item_key}) {item.name}")
        else:
            console.print(x + 1, y + 1, "(Empty)")
 
    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[Action]:
        player = self.engine.player
        key = event.sym
        index = key - KeySym.a
        # TODO handle upper case
 
        if 0 <= index <= 26:
            try:
                selected_item = player.inventory.items[index]
            except IndexError:
                self.engine.message_log.add_message("Invalid entry.", color.invalid)
                return None
            return self.on_item_selected(selected_item)
        return super().ev_keydown(event)
 
    def on_item_selected(self, item: Item) -> Optional[Action]:
        """Called when the user selects a valid item."""
        raise NotImplementedError()

class InventoryActivateHandler(InventoryEventHandler):
    """Handle using an inventory item."""
 
    TITLE = "Select an item to use"
 
    def on_item_selected(self, item: Item) -> Optional[Action]:
        """Return the action for the selected item."""
        return item.consumable.get_action(self.engine.player)
 
 
class InventoryDropHandler(InventoryEventHandler):
    """Handle dropping an inventory item."""
 
    TITLE = "Select an item to drop"
 
    def on_item_selected(self, item: Item) -> Optional[Action]:
        """Drop this item."""
        return DropItem(self.engine.player, item)


class SelectIndexHandler(AskUserEventHandler):
    """Handles asking the user for an index on the map."""
 
    def __init__(self, engine: Engine):
        """Sets the cursor to the player when this handler is constructed."""
        super().__init__(engine)
        player = self.engine.player
        engine.mouse_location = player.x, player.y
 
    def on_render(self, console: tcod.Console) -> None:
        """Highlight the tile under the cursor."""
        super().on_render(console)
        x, y = self.engine.mouse_location
        console.rgb["bg"][x, y] = color.white
        console.rgb["fg"][x, y] = color.black
 
    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[Action]:
        """Check for key movement or confirmation keys."""
        key = event.sym
        if key in MOVE_KEYS:
            modifier = 1  # Holding modifier keys will speed up key movement.
            if event.mod & (tcod.event.KMOD_LSHIFT | tcod.event.KMOD_RSHIFT):
                modifier *= 5
            if event.mod & (tcod.event.KMOD_LCTRL | tcod.event.KMOD_RCTRL):
                modifier *= 10
            if event.mod & (tcod.event.KMOD_LALT | tcod.event.KMOD_RALT):
                modifier *= 20
 
            x, y = self.engine.mouse_location
            dx, dy = MOVE_KEYS[key]
            x += dx * modifier
            y += dy * modifier
            # Clamp the cursor index to the map size.
            x = max(0, min(x, self.engine.game_map.width - 1))
            y = max(0, min(y, self.engine.game_map.height - 1))
            self.engine.mouse_location = x, y
            return None
        elif key in CONFIRM_KEYS:
            return self.on_index_selected(*self.engine.mouse_location)
        return super().ev_keydown(event)
 
    def ev_mousebuttondown(self, event: tcod.event.MouseButtonDown) -> Optional[Action]:
        """Left click confirms a selection."""
        if self.engine.game_map.in_bounds(*event.tile):
            if event.button == 1:
                return self.on_index_selected(*event.tile)
        return super().ev_mousebuttondown(event)
 
    def on_index_selected(self, x: int, y: int) -> Optional[Action]:
        """Called when an index is selected."""
        raise NotImplementedError()
 
 
class LookHandler(SelectIndexHandler):
    """Lets the player look around using the keyboard."""
 
    def on_index_selected(self, x: int, y: int) -> None:
        """Return to main handler."""
        self.engine.event_handler = MainGameEventHandler(self.engine)


class SingleRangedAttackHandler(SelectIndexHandler):
    """Handles targeting a single enemy. Only the enemy selected will be affected."""
 
    def __init__(
        self, engine: Engine, callback: Callable[[Tuple[int, int]], Optional[Action]]
    ):
        super().__init__(engine)
 
        self.callback = callback
 
    def on_index_selected(self, x: int, y: int) -> Optional[Action]:
        return self.callback((x, y))


class AreaRangedAttackHandler(SelectIndexHandler):
    """Handles targeting an area within a given radius. Any entity within the area will be affected."""
 
    def __init__(
        self,
        engine: Engine,
        radius: int,
        callback: Callable[[Tuple[int, int]], Optional[Action]],
    ):
        super().__init__(engine)
 
        self.radius = radius
        self.callback = callback
 
    def on_render(self, console: tcod.Console) -> None:
        """Highlight the tile under the cursor."""
        super().on_render(console)
 
        x, y = self.engine.mouse_location
 
        # Draw a rectangle around the targeted area, so the player can see the affected tiles.
        console.draw_frame(
            x=x - self.radius - 1,
            y=y - self.radius - 1,
            width=self.radius ** 2,
            height=self.radius ** 2,
            fg=color.red,
            clear=False,
        )
 
    def on_index_selected(self, x: int, y: int) -> Optional[Action]:
        return self.callback((x, y))
