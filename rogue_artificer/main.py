import tcod
import traceback

from rogue_artificer.input_handlers import BaseEventHandler, EventHandler, MainGameEventHandler
from rogue_artificer.entity import Entity
from rogue_artificer import setup_game, exceptions, color
from rogue_artificer.ttf import load_ttf

def save_game(handler: BaseEventHandler, filename: str) -> None:
   """If the current event handler has an active Engine then save it."""
   if isinstance(handler, EventHandler):
       handler.engine.save_as(filename)
       print("Game saved.")

def main():
    screen_width = 80
    screen_height = 60 

    tileset = tcod.tileset.load_truetype_font("assets/MartianMonoNerdFontMono-Medium.ttf", 12, 12)
    handler: BaseEventHandler = setup_game.MainMenu()

    console = tcod.console.Console(screen_width, screen_height, order="F")
    with tcod.context.new_terminal(
        console.width,
        console.height,
        tileset=tileset,
        title="Rogue Artificer",
    ) as context:
        try:
            while True:
                console.clear()
                handler.on_render(console=console)
                context.present(console, keep_aspect=True, integer_scaling=True)

                try:
                    for event in tcod.event.wait():
                        context.convert_event(event)
                        handler = handler.handle_events(event)
                except Exception:  # Handle exceptions in game.
                    traceback.print_exc()  # Print error to stderr.
                    # Then print the error to the message log.
                    if isinstance(handler, EventHandler):
                        handler.engine.message_log.add_message(traceback.format_exc(), color.error)
        except exceptions.QuitWithoutSaving:
            raise
        except SystemExit:
            save_game(handler, "savegame.sav")
            raise
        except BaseException: # save on any other unexpected exception
            save_game(handler, "savegame.sav")
            raise
