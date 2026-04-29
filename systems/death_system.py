import random
from typing import List

from game_state import BereavementPayment, GameState
from models import Hero
from ui import danger, success, warning


EQUIPMENT_RECOVERY_CHANCE = 0.55


def queue_bereavement_payment(state: GameState, hero: Hero) -> str:
    death_benefit = max(10, hero.wage_per_year)

    state.pending_bereavement_payments.append(BereavementPayment(hero.name, death_benefit))

    return warning(
        f"{hero.name}'s family is owed a {death_benefit}g death benefit."
    )


def recover_equipment_from_dead_hero(state: GameState, hero: Hero, party_has_survivors: bool) -> List[str]:
    messages = []

    if not hero.equipment:
        return messages

    if not party_has_survivors:
        lost_names = ", ".join(item.name for item in hero.equipment.values())
        hero.equipment.clear()
        messages.append(danger(f"{hero.name}'s equipment was lost in the dungeon: {lost_names}."))
        return messages

    for slot, item in list(hero.equipment.items()):
        if random.random() <= EQUIPMENT_RECOVERY_CHANCE:
            state.inventory.append(item)
            messages.append(success(f"Recovered {hero.name}'s {item.name} from the dungeon."))
        else:
            messages.append(warning(f"{hero.name}'s {item.name} could not be recovered."))

        del hero.equipment[slot]

    return messages