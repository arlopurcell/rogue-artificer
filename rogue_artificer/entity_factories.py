from rogue_artificer.components.ai import HostileEnemy
from rogue_artificer.components import consumable
from rogue_artificer.components.fighter import Fighter
from rogue_artificer.components.inventory import Inventory
from rogue_artificer.entity import Actor
from rogue_artificer.item import Item

player = Actor(
        char="@", 
        color=(255, 255, 255), 
        name="Player", 
        ai_cls=HostileEnemy,
        fighter=Fighter(hp=30, base_defense=0, unarmed_damage=1),
        inventory=Inventory(capacity=26),
)

orc = Actor(
        char="o", 
        color=(63, 127, 63), 
        name="Orc",
        ai_cls=HostileEnemy,
        fighter=Fighter(hp=10, base_defense=0, unarmed_damage=3),
        inventory=Inventory(capacity=0),
)

troll = Actor(
        char="T", 
        color=(0, 127, 0), 
        name="Troll",
        ai_cls=HostileEnemy,
        fighter=Fighter(hp=16, base_defense=1, unarmed_damage=4),
        inventory=Inventory(capacity=0),
)

health_potion = Item(
    char="!",
    color=(127, 0, 255),
    name="Health Potion",
    consumable=consumable.HealingConsumable(amount=4),
)


lightning_scroll = Item(
    char="~",
    color=(255, 255, 0),
    name="Lightning Scroll",
    consumable=consumable.LightningDamageConsumable(damage=20, maximum_range=5),
)

confusion_scroll = Item(
   char="~",
   color=(207, 63, 255),
   name="Confusion Scroll",
   consumable=consumable.ConfusionConsumable(number_of_turns=10),
)

fireball_scroll = Item(
   char="~",
   color=(255, 0, 0),
   name="Fireball Scroll",
   consumable=consumable.FireballDamageConsumable(damage=12, radius=3),
)
