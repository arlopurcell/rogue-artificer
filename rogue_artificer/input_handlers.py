from __future__ import annotations

import os
from typing import Callable, Optional, TYPE_CHECKING, Tuple, Union

import tcod
import tcod.event
from tcod.event import KeySym
from tcod import libtcodpy

from rogue_artificer import actions
from rogue_artificer.actions import Action, BumpAction, WaitAction, PickupAction, DropItem
from rogue_artificer import color, exceptions
from rogue_artificer.components import inventory

if TYPE_CHECKING:
    from rogue_artificer.engine import Engine
    from rogue_artificer.item import Item

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

ActionOrHandler = Union[Action, "BaseEventHandler"]
"""An event handler return value which can trigger an action or switch active handlers.

If a handler is returned then it will become the active handler for future events.
If an action is returned it will be attempted and if it's valid then
MainGameEventHandler will become the active handler.
"""


class BaseEventHandler(tcod.event.EventDispatch[ActionOrHandler]):
    def handle_events(self, event: tcod.event.Event) -> BaseEventHandler:
        """Handle an event and return the next active event handler."""
        state = self.dispatch(event)
        if isinstance(state, BaseEventHandler):
            return state
        assert not isinstance(state, Action), f"{self!r} can not handle actions."
        return self
 
    def on_render(self, console: tcod.console.Console) -> None:
        raise NotImplementedError()
 
    def ev_quit(self, event: tcod.event.Quit) -> Optional[Action]:
        raise SystemExit()

class EventHandler(BaseEventHandler):
    def __init__(self, engine: Engine):
        self.engine = engine

    def handle_events(self, event: tcod.event.Event) -> BaseEventHandler:
        """Handle events for input handlers with an engine."""
        action_or_state = self.dispatch(event)
        if isinstance(action_or_state, BaseEventHandler):
            return action_or_state

        if self.handle_action(action_or_state):
            # A valid action was performed.
            if not self.engine.player.is_alive:
                # The player was killed sometime during or after the action.
                return GameOverEventHandler(self.engine)
            return MainGameEventHandler(self.engine)  # Return to the main handler.
        return self
 
    def handle_action(self, action: Optional[Action]) -> bool:
        """Handle actions returned from event methods.
 
        Returns True if the action will advance a turn.
        """
        if action is None:
            return False
 
        try:
            delay = action.perform()
        except exceptions.Impossible as exc:
            self.engine.message_log.add_message(exc.args[0], color.impossible)
            return False  # Skip enemy turn on exceptions.
        self.engine.game_map.turn_tracker.push(self.engine.player, delay)
 
        self.engine.handle_enemy_turns()
 
        self.engine.update_fov()
        return True

    def ev_mousemotion(self, event: tcod.event.MouseMotion) -> None:
        if self.engine.game_map.in_bounds(event.tile.x, event.tile.y):
            self.engine.mouse_location = event.tile.x, event.tile.y

    def on_render(self, console: tcod.console.Console) -> None:
        self.engine.render(console)


class MainGameEventHandler(EventHandler):
    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[ActionOrHandler]:
        key = event.sym
        is_shift = bool(event.mod & (tcod.event.KMOD_LSHIFT | tcod.event.KMOD_RSHIFT))
        player = self.engine.player

        if not is_shift and key in MOVE_KEYS:
            dx, dy = MOVE_KEYS[key]
            return BumpAction(player, dx, dy)

        elif not is_shift and key in WAIT_KEYS:
            return WaitAction(player)

        elif key == KeySym.ESCAPE:
            raise SystemExit()

        elif not is_shift and key == KeySym.v:
           return HistoryViewer(self.engine)

        elif not is_shift and key in PICKUP_KEYS:
            return PickupAction(player)

        elif not is_shift and key == KeySym.i:
            return InventoryActivateHandler(self.engine)

        elif not is_shift and key == KeySym.d:
            return InventoryDropHandler(self.engine)

        elif not is_shift and key == KeySym.SLASH:
            return LookHandler(self.engine)

        elif is_shift and key == KeySym.PERIOD:
            return actions.TakeStairsAction(player)

        elif not is_shift and key == KeySym.q:
            return QuaffHandler(self.engine)

        elif not is_shift and key == KeySym.w:
            return WieldHandler(self.engine)

        elif is_shift and key == KeySym.w:
            return WearHandler(self.engine)

        # No valid key was pressed
        return None

class GameOverEventHandler(EventHandler):
    def on_quit(self) -> None:
        """Handle exiting out of a finished game."""
        if os.path.exists("savegame.sav"):
            os.remove("savegame.sav")  # Deletes the active save file.
        raise exceptions.QuitWithoutSaving()  # Avoid saving a finished game.
 
    def ev_quit(self, event: tcod.event.Quit) -> None:
        self.on_quit()

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[Action]:
        action: Optional[Action] = None

        key = event.sym

        if key == KeySym.ESCAPE:
            self.on_quit()

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

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[MainGameEventHandler]:
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
            return MainGameEventHandler(self.engine)

        return None

class AskUserEventHandler(EventHandler):
    """Handles user input for actions which require special input."""
 
    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[ActionOrHandler]:
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
 
    def ev_mousebuttondown(self, event: tcod.event.MouseButtonDown) -> Optional[ActionOrHandler]:
        """By default any mouse click exits this input handler."""
        return self.on_exit()
 
    def on_exit(self) -> Optional[ActionOrHandler]:
        """Called when the user is trying to exit or cancel an action.
 
        By default this returns to the main event handler.
        """
        return MainGameEventHandler(self.engine)

class InventoryEventHandler(AskUserEventHandler):
    """This handler lets the user select an item.
 
    What happens then depends on the subclass.
    """
 
    TITLE = "<missing title>"
    relevance_filter = True

    def is_relevant(self, item: Item) -> bool:
        return True
 
    def on_render(self, console: tcod.console.Console) -> None:
        """Render an inventory menu, which displays the items in the inventory, and the letter to select them.
        Will move to a different position based on where the player is located, so the player can always see where
        they are.
        """
        # render parent, then dim
        super().on_render(console)
        console.rgb["fg"] //= 2
        console.rgb["bg"] //= 2

        relevant_items = {k: stack for k, stack in self.engine.player.inventory.items.items() if not self.relevance_filter or self.is_relevant(stack[0])}
        number_of_items_in_inventory = len(relevant_items)
 
        height = number_of_items_in_inventory + 2
 
        if height <= 3:
            height = 3
        width = 40
 
        x = (console.width - width) // 2
        y = 2
 
        console.draw_frame(
            x=x,
            y=y,
            width=width,
            height=height,
            decoration="╔═╗║ ║╚═╝",
            clear=True,
            fg=(255, 255, 255),
            bg=(10, 10, 10),
        )
        console.print(
            x=x + (width - len(self.TITLE)) // 2, 
            y=y, 
            string=self.TITLE,
            fg=(0, 0, 0),
            bg=(255, 255, 255),
        )
 
        if number_of_items_in_inventory > 0:
            for i, (k, item_stack) in enumerate(relevant_items.items()):
                if len(item_stack) == 1:
                    text = item_stack[0].name
                else:
                    text = f"{len(item_stack)} {item_stack[0].name}s"

                if k == self.engine.player.inventory.wielded_key:
                    text += " (wielded)"
                else:
                    for slot, armor_key in self.engine.player.inventory.armor_keys.items():
                        if k == armor_key:
                            text += f" (worn on {slot})"
                
                console.print(x + 1, y + i + 1, f"{k} - {text.capitalize()}")
        else:
            console.print(x + 1, y + 1, "(Empty)")
        # TODO show something like "(Press '.' to show irrelevant items)"
 
    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[ActionOrHandler]:
        player = self.engine.player
        key = event.sym
 
        # TODO handle upper case
        if KeySym.a <= key <= KeySym.z:
            index = chr(key)
            try:
                return self.on_item_selected(index)
            except IndexError:
                self.engine.message_log.add_message("Invalid entry.", color.invalid)
                return None
        elif key == KeySym.PERIOD:
            self.relevance_filter = not self.relevance_filter
            return None
        return super().ev_keydown(event)
 
    def on_item_selected(self, key: str) -> Optional[ActionOrHandler]:
        """Called when the user selects a valid item."""
        raise NotImplementedError()

class InventoryActivateHandler(InventoryEventHandler):
    """Handle viewing inventory items."""
 
    TITLE = "Inventory"
 
    def on_item_selected(self, key: str) -> Optional[ActionOrHandler]:
        # TODO show description of item?
        return MainGameEventHandler(self.engine)
 
 
class InventoryDropHandler(InventoryEventHandler):
    """Handle dropping an inventory item."""
 
    TITLE = "Select an item to drop"
 
    def on_item_selected(self, key: str) -> Optional[ActionOrHandler]:
        """Drop this item."""
        return DropItem(self.engine.player, key)

class QuaffHandler(InventoryEventHandler):
    TITLE = "Select an item to drink"
 
    def is_relevant(self, item: Item) -> bool:
        return bool(item.consumable) and item.consumable.is_quaffable

    def on_item_selected(self, key: str) -> Optional[ActionOrHandler]:
        return actions.QuaffAction(self.engine.player, key)

class WieldHandler(InventoryEventHandler):
    TITLE = "Select an item to wield"

    def is_relevant(self, item: Item) -> bool:
        from rogue_artificer.item import MeleeWeapon
        return isinstance(item, MeleeWeapon)

    def on_item_selected(self, key: str) -> Optional[ActionOrHandler]:
        return actions.WieldAction(self.engine.player, key)

class WearHandler(InventoryEventHandler):
    TITLE = "Select an item to wear"

    def is_relevant(self, item: Item) -> bool:
        from rogue_artificer.item import Armor
        return isinstance(item, Armor)

    def on_item_selected(self, key: str) -> Optional[ActionOrHandler]:
        return actions.WearAction(self.engine.player, key)


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
 
    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[ActionOrHandler]:
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
 
    def ev_mousebuttondown(self, event: tcod.event.MouseButtonDown) -> Optional[ActionOrHandler]:
        """Left click confirms a selection."""
        if self.engine.game_map.in_bounds(*event.tile):
            if event.button == 1:
                return self.on_index_selected(*event.tile)
        return super().ev_mousebuttondown(event)
 
    def on_index_selected(self, x: int, y: int) -> Optional[ActionOrHandler]:
        """Called when an index is selected."""
        raise NotImplementedError()
 
 
class LookHandler(SelectIndexHandler):
    """Lets the player look around using the keyboard."""
 
    def on_index_selected(self, x: int, y: int) -> None:
        """Return to main handler."""
        return MainGameEventHandler(self.engine)


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

class PopupMessage(BaseEventHandler):
    """Display a popup text window."""
 
    def __init__(self, parent_handler: BaseEventHandler, text: str):
        self.parent = parent_handler
        self.text = text
 
    def on_render(self, console: tcod.console.Console) -> None:
        """Render the parent and dim the result, then print the message on top."""
        self.parent.on_render(console)
        console.rgb["fg"] //= 8
        console.rgb["bg"] //= 8
 
        console.print(
            console.width // 2,
            console.height // 2,
            self.text,
            fg=color.white,
            bg=color.black,
            alignment=tcod.CENTER,
        )
 
    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[BaseEventHandler]:
        """Any key returns to the parent handler."""
        return self.parent
