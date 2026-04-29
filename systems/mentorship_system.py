from typing import List


MIN_LEVEL_GAP_FOR_MENTORSHIP = 2
BASE_MENTORSHIP_XP_PER_VALUE = 8


def apply_party_mentorship(party, base_xp: int) -> List[str]:
    """
    Applies bonus XP to lower-level heroes when a higher-level same-class hero
    is in the same party.

    Rules:
    - Same class only
    - Mentor must be at least MIN_LEVEL_GAP_FOR_MENTORSHIP levels higher
    - Mentor must have mentorship_value > 0
    - Bonus scales with mentor value and mission XP
    """
    messages = []

    if base_xp <= 0 or len(party) < 2:
        return messages

    for trainee in party:
        if trainee.is_temporary_survivor:
            continue

        best_mentor = None
        best_bonus = 0

        for mentor in party:
            if mentor is trainee:
                continue

            if mentor.is_temporary_survivor:
                continue

            if mentor.hero_class != trainee.hero_class:
                continue

            if mentor.level < trainee.level + MIN_LEVEL_GAP_FOR_MENTORSHIP:
                continue

            mentor_value = mentor.mentorship_value()
            if mentor_value <= 0:
                continue

            bonus_xp = calculate_mentorship_bonus(base_xp, mentor_value)

            if bonus_xp > best_bonus:
                best_bonus = bonus_xp
                best_mentor = mentor

        if best_mentor and best_bonus > 0:
            xp_messages = trainee.add_xp(best_bonus)
            messages.append(
                f"{best_mentor.name} mentored {trainee.name}: +{best_bonus} bonus XP."
            )
            messages.extend(xp_messages)

    return messages


def calculate_mentorship_bonus(base_xp: int, mentor_value: int) -> int:
    flat_bonus = mentor_value * BASE_MENTORSHIP_XP_PER_VALUE
    scaled_bonus = int(base_xp * (0.05 * mentor_value))

    return max(1, flat_bonus + scaled_bonus)