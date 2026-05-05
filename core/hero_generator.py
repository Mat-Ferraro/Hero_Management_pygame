import random
from typing import Dict, List, Set

from contract_attitudes import attitude_multiplier, random_contract_attitude
from data_loader import load_hero_generation_rules, load_hero_names
from growth_rates import random_growth_rate
from hero_specialties import random_specialty_for_class
from models import Hero
from systems.hero_career import CAREER_PHASES_BY_CLASS, career_phase_name
from systems.hero_progression import (
    CLASS_TRAINING_PATHS,
    available_training_paths,
    ensure_progression_fields,
    spend_training_point,
)


RECRUIT_PHASE_WEIGHTS_BY_CLASS: Dict[str, Dict[str, int]] = {
    "Rogue": {
        "Rookie": 46,
        "Rising": 30,
        "Prime": 16,
        "Veteran": 6,
        "Elder": 2,
    },
    "Warrior": {
        "Rookie": 42,
        "Rising": 30,
        "Prime": 18,
        "Veteran": 8,
        "Elder": 2,
    },
    "Cleric": {
        "Rookie": 40,
        "Rising": 28,
        "Prime": 20,
        "Veteran": 9,
        "Elder": 3,
    },
    "Mage": {
        "Rookie": 38,
        "Rising": 28,
        "Prime": 21,
        "Veteran": 10,
        "Elder": 3,
    },
}

DEVELOPMENTAL_PHASE_WEIGHTS_BY_CLASS: Dict[str, Dict[str, int]] = {
    "Rogue": {"Rookie": 80, "Rising": 20},
    "Warrior": {"Rookie": 82, "Rising": 18},
    "Cleric": {"Rookie": 86, "Rising": 14},
    "Mage": {"Rookie": 90, "Rising": 10},
}


def weighted_choice(weight_map: Dict[str, int]) -> str:
    total = sum(max(0, int(weight)) for weight in weight_map.values())
    if total <= 0:
        return next(iter(weight_map))

    roll = random.randint(1, total)
    running = 0

    for value, weight in weight_map.items():
        running += max(0, int(weight))
        if roll <= running:
            return value

    return next(iter(weight_map))


def generate_name(existing_names: Set[str]) -> str:
    names = load_hero_names()
    first_names = names.get("first_names", ["Nameless"])
    titles = names.get("titles", ["Adventurer"])

    for _ in range(100):
        name = f"{random.choice(first_names)} {random.choice(titles)}"
        if name not in existing_names:
            return name

    return f"{random.choice(first_names)} {random.choice(titles)} {random.randint(100, 999)}"


def phase_age_range_for_class(class_name: str, phase_name: str) -> tuple[int, int]:
    phase_table = CAREER_PHASES_BY_CLASS.get(class_name, [])
    for name, min_age, max_age in phase_table:
        if name != phase_name:
            continue

        low = int(min_age)
        high = int(max_age) if max_age is not None else (low + 8)
        return low, max(low, high)

    return 18, 24


def choose_phase_for_new_recruit(class_name: str, developmental: bool = False) -> str:
    if developmental:
        weights = DEVELOPMENTAL_PHASE_WEIGHTS_BY_CLASS.get(
            class_name,
            {"Rookie": 85, "Rising": 15},
        )
        return weighted_choice(weights)

    weights = RECRUIT_PHASE_WEIGHTS_BY_CLASS.get(
        class_name,
        {
            "Rookie": 42,
            "Rising": 28,
            "Prime": 18,
            "Veteran": 9,
            "Elder": 3,
        },
    )
    return weighted_choice(weights)


def choose_age_for_phase(class_name: str, phase_name: str) -> int:
    low, high = phase_age_range_for_class(class_name, phase_name)
    return random.randint(low, high)


def level_range_for_phase(class_name: str, phase_name: str) -> tuple[int, int]:
    if class_name == "Rogue":
        table = {
            "Rookie": (1, 2),
            "Rising": (2, 4),
            "Prime": (4, 6),
            "Veteran": (4, 6),
            "Elder": (3, 5),
        }
    elif class_name == "Warrior":
        table = {
            "Rookie": (1, 2),
            "Rising": (2, 4),
            "Prime": (4, 6),
            "Veteran": (4, 6),
            "Elder": (3, 5),
        }
    elif class_name == "Cleric":
        table = {
            "Rookie": (1, 2),
            "Rising": (2, 4),
            "Prime": (4, 6),
            "Veteran": (4, 7),
            "Elder": (4, 7),
        }
    else:  # Mage
        table = {
            "Rookie": (1, 2),
            "Rising": (2, 4),
            "Prime": (4, 7),
            "Veteran": (4, 7),
            "Elder": (4, 7),
        }

    return table.get(phase_name, (1, 2))


def scale_stats_for_level(stats: Dict[str, int], level: int, hero_class: str) -> Dict[str, int]:
    if level <= 1:
        return dict(stats)

    primary_stats = {
        "Warrior": ["might"],
        "Rogue": ["agility"],
        "Cleric": ["spirit"],
        "Mage": ["mind"],
    }.get(hero_class, [])

    scaled = dict(stats)

    for _ in range(level - 1):
        for stat in primary_stats:
            scaled[stat] = scaled.get(stat, 0) + 1

        random_stat = random.choice(["might", "agility", "mind", "spirit"])
        scaled[random_stat] = scaled.get(random_stat, 0) + 1

    return scaled


def base_combat_power(hero_class: str, level: int, stats: Dict[str, int]) -> int:
    primary = {
        "Warrior": ["might"],
        "Rogue": ["agility"],
        "Cleric": ["spirit"],
        "Mage": ["mind"],
    }.get(hero_class, [])

    secondary = {
        "Warrior": ["spirit"],
        "Rogue": ["mind"],
        "Cleric": ["mind"],
        "Mage": ["spirit"],
    }.get(hero_class, [])

    primary_power = sum(stats.get(stat, 0) * 2 for stat in primary)
    secondary_power = sum(stats.get(stat, 0) * 1 for stat in secondary)
    general_power = sum(stats.values())
    return max(1, primary_power + secondary_power + general_power + level * 3)


def calculate_contract_values(
    hero_class: str,
    age: int,
    level: int,
    stats: Dict[str, int],
    contract_attitude: str,
    reputation,
    injured: bool = False,
) -> tuple[int, int]:
    rules = load_hero_generation_rules()
    pricing = rules.get("pricing", {})

    power = base_combat_power(hero_class, level, stats)

    signing_fee = pricing.get("signing_base", 25)
    signing_fee += power * pricing.get("signing_power_multiplier", 2.2)
    signing_fee += level * pricing.get("signing_level_multiplier", 35)

    wage = pricing.get("wage_base", 6)
    wage += power * pricing.get("wage_power_multiplier", 0.35)
    wage += level * pricing.get("wage_level_multiplier", 5)

    if age <= pricing.get("young_premium_age", 24):
        signing_fee *= pricing.get("young_premium", 1.10)
        wage *= pricing.get("young_premium", 1.10)

    if age >= pricing.get("old_discount_age", 55):
        signing_fee *= pricing.get("old_discount", 0.80)
        wage *= pricing.get("old_discount", 0.80)

    if injured:
        signing_fee *= pricing.get("injury_discount", 0.70)
        wage *= pricing.get("injury_discount", 0.70)

    signing_fee *= attitude_multiplier(contract_attitude, "signing_bonus", reputation)
    wage *= attitude_multiplier(contract_attitude, "wage", reputation)

    return max(1, int(signing_fee)), max(1, int(wage))


def apply_reputation_to_contract(hero: Hero, reputation) -> None:
    def reputation_multiplier(score: int, positive_discount: float, negative_markup: float) -> float:
        if score > 0:
            return max(0.70, 1.0 - ((score / 100.0) * positive_discount))

        if score < 0:
            return min(1.75, 1.0 + ((abs(score) / 100.0) * negative_markup))

        return 1.0

    class_key = hero.hero_class.lower()
    class_score = getattr(reputation, class_key, 0)

    wage_multiplier = 1.0
    signing_multiplier = 1.0

    wage_multiplier *= reputation_multiplier(reputation.reliability, positive_discount=0.15, negative_markup=0.45)
    wage_multiplier *= reputation_multiplier(class_score, positive_discount=0.12, negative_markup=0.25)

    signing_multiplier *= reputation_multiplier(reputation.safety, positive_discount=0.10, negative_markup=0.35)
    signing_multiplier *= reputation_multiplier(reputation.overall, positive_discount=0.08, negative_markup=0.20)
    signing_multiplier *= reputation_multiplier(class_score, positive_discount=0.10, negative_markup=0.20)

    hero.wage_per_year = max(1, int(hero.wage_per_year * wage_multiplier))
    hero.signing_bonus = max(1, int(hero.signing_bonus * signing_multiplier))


def choose_class_for_state(rules: Dict, state) -> str:
    unlocked_classes = getattr(state.guild_upgrades, "unlocked_classes", ["Warrior"])
    valid_classes = [
        class_name
        for class_name in unlocked_classes
        if class_name in rules["classes"]
    ]

    if not valid_classes:
        valid_classes = ["Warrior"]

    return random.choice(valid_classes)


def choose_level_for_phase(class_rules: Dict, state, class_name: str, phase_name: str) -> int:
    level_cap = getattr(state.guild_upgrades, "recruit_level_cap", 1)
    low, high = level_range_for_phase(class_name, phase_name)
    high = min(high, level_cap)
    low = min(low, high)

    if high < 1:
        return 1

    return random.randint(max(1, low), max(1, high))


def market_tier_for_hero(hero: Hero, developmental: bool = False) -> str:
    if developmental:
        return "Developmental"

    growth_rank = {
        "Mundane": 0,
        "Talented": 1,
        "Gifted": 2,
        "Heroic": 3,
        "Legendary": 4,
        "Mythic": 5,
    }.get(hero.growth_rate, 1)

    unlocked_count = len(getattr(hero, "unlocked_subclasses", []) or [])

    if hero.level >= 6 or growth_rank >= 4 or unlocked_count >= 2:
        return "Elite"
    if hero.level >= 4 or growth_rank >= 3 or unlocked_count >= 1:
        return "Premium"
    return "Standard"

def assign_negotiation_profile(hero: Hero, developmental: bool = False) -> Hero:
    attitude_profiles = {
        "Modest": {
            "money_per_campaign_weight": 0.70,
            "term_weight": 0.10,
            "mentorship_weight": 0.08,
            "reputation_weight": 0.05,
            "safety_weight": 0.03,
            "development_weight": 0.04,
        },
        "Practical": {
            "money_per_campaign_weight": 0.72,
            "term_weight": 0.10,
            "mentorship_weight": 0.05,
            "reputation_weight": 0.06,
            "safety_weight": 0.03,
            "development_weight": 0.04,
        },
        "Ambitious": {
            "money_per_campaign_weight": 0.70,
            "term_weight": 0.06,
            "mentorship_weight": 0.03,
            "reputation_weight": 0.12,
            "safety_weight": 0.02,
            "development_weight": 0.07,
        },
        "Mercenary": {
            "money_per_campaign_weight": 0.82,
            "term_weight": 0.06,
            "mentorship_weight": 0.01,
            "reputation_weight": 0.04,
            "safety_weight": 0.01,
            "development_weight": 0.02,
        },
        "Noble": {
            "money_per_campaign_weight": 0.64,
            "term_weight": 0.08,
            "mentorship_weight": 0.04,
            "reputation_weight": 0.15,
            "safety_weight": 0.05,
            "development_weight": 0.04,
        },
    }

    profile = dict(attitude_profiles.get(hero.contract_attitude, attitude_profiles["Practical"]))

    preferred_campaigns = max(1, hero.contract_years)
    asking_signing_fee = max(25, hero.signing_bonus)

    phase = career_phase_name(hero)

    if phase == "Rookie":
        preferred_campaigns = max(3, min(preferred_campaigns, 5))
        asking_signing_fee = max(25, int(asking_signing_fee * 0.78))
        profile["development_weight"] += 0.04
        profile["mentorship_weight"] += 0.03
        profile["money_per_campaign_weight"] = max(0.62, profile["money_per_campaign_weight"] - 0.05)

    elif phase == "Rising":
        preferred_campaigns = max(3, min(preferred_campaigns, 5))
        asking_signing_fee = max(25, int(asking_signing_fee * 0.92))
        profile["development_weight"] += 0.02

    elif phase == "Prime":
        preferred_campaigns = max(2, min(preferred_campaigns, 4))
        asking_signing_fee = max(25, int(asking_signing_fee * 1.08))
        profile["reputation_weight"] += 0.02

    elif phase == "Veteran":
        preferred_campaigns = min(preferred_campaigns, 3)
        asking_signing_fee = max(25, int(asking_signing_fee * 0.92))
        profile["safety_weight"] += 0.03
        profile["reputation_weight"] += 0.03

    elif phase == "Elder":
        preferred_campaigns = min(preferred_campaigns, 2)
        asking_signing_fee = max(25, int(asking_signing_fee * 0.78))
        profile["safety_weight"] += 0.05
        profile["reputation_weight"] += 0.04
        profile["money_per_campaign_weight"] = min(0.88, profile["money_per_campaign_weight"] + 0.04)

    if hero.age <= 24:
        preferred_campaigns = max(preferred_campaigns, 3)

    if developmental:
        preferred_campaigns = max(2, min(preferred_campaigns, 4))
        asking_signing_fee = max(25, int(asking_signing_fee * 0.70))
        profile["development_weight"] += 0.05
        profile["money_per_campaign_weight"] = max(0.60, profile["money_per_campaign_weight"] - 0.06)

    asking_fee_per_campaign = max(10, int(round(asking_signing_fee / preferred_campaigns)))

    hero.preferred_campaigns = preferred_campaigns
    hero.asking_signing_fee = asking_signing_fee
    hero.asking_fee_per_campaign = asking_fee_per_campaign

    hero.money_per_campaign_weight = profile["money_per_campaign_weight"]
    hero.term_weight = profile["term_weight"]
    hero.mentorship_weight = profile["mentorship_weight"]
    hero.reputation_weight = profile["reputation_weight"]
    hero.safety_weight = profile["safety_weight"]
    hero.development_weight = profile["development_weight"]

    hero.is_developmental = developmental
    hero.market_tier = market_tier_for_hero(hero, developmental=developmental)
    return hero

def _path_names_for_hero(hero) -> List[str]:
    return list(available_training_paths(hero).keys())


def _apply_training_steps(hero, steps: int) -> None:
    ensure_progression_fields(hero)
    steps = max(0, int(steps))

    path_names = _path_names_for_hero(hero)
    if not path_names or steps <= 0:
        return

    hero.training_points += steps

    for _ in range(steps):
        candidates = [
            path_name
            for path_name in path_names
            if hero.training_path_progress.get(path_name, 0)
            < len(CLASS_TRAINING_PATHS[hero.hero_class][path_name]["ranks"])
        ]
        if not candidates:
            break

        weights = []
        phase = career_phase_name(hero)
        for path_name in candidates:
            weight = 1
            lowered = path_name.lower()

            if hero.hero_class == "Warrior":
                if phase in ("Rising", "Prime") and lowered in ("vanguard", "warden"):
                    weight += 2
                if phase in ("Veteran", "Elder") and lowered == "captain":
                    weight += 2
            elif hero.hero_class == "Rogue":
                if phase in ("Rookie", "Rising") and lowered == "scout":
                    weight += 2
                if phase in ("Prime", "Veteran") and lowered in ("fixer", "shadow"):
                    weight += 2
            elif hero.hero_class == "Cleric":
                if phase in ("Rising", "Prime") and lowered in ("templar", "shepherd"):
                    weight += 2
                if phase in ("Veteran", "Elder") and lowered == "oracle":
                    weight += 2
            elif hero.hero_class == "Mage":
                if phase in ("Rising", "Prime") and lowered == "arcanist":
                    weight += 2
                if phase in ("Veteran", "Elder") and lowered in ("seer", "spellblade"):
                    weight += 2

            if hero.training_path_progress.get(path_name, 0) == 0:
                weight += 1

            weights.append(weight)

        chosen_path = random.choices(candidates, weights=weights, k=1)[0]
        spend_training_point(hero, chosen_path)


def _prior_development_steps_for_hero(hero) -> int:
    phase = career_phase_name(hero)

    if phase == "Rookie":
        return 0

    if phase == "Rising":
        return random.randint(0, 1)

    if phase == "Prime":
        return random.randint(1, 3)

    if phase == "Veteran":
        return random.randint(2, 4)

    if phase == "Elder":
        if hero.hero_class == "Rogue":
            return random.randint(1, 3)
        return random.randint(3, 5)

    return 0


def generate_hero(existing_names: Set[str], state) -> Hero:
    rules = load_hero_generation_rules()
    class_name = choose_class_for_state(rules, state)
    class_rules = rules["classes"][class_name]

    phase_name = choose_phase_for_new_recruit(class_name, developmental=False)
    age = choose_age_for_phase(class_name, phase_name)
    level = choose_level_for_phase(class_rules, state, class_name, phase_name)

    stats = {}
    for stat, stat_range in class_rules["stat_ranges"].items():
        stats[stat] = random.randint(int(stat_range[0]), int(stat_range[1]))

    stats = scale_stats_for_level(stats, level, class_name)

    contract_attitude = random_contract_attitude()
    signing_bonus, wage_per_year = calculate_contract_values(
        hero_class=class_name,
        age=age,
        level=level,
        stats=stats,
        contract_attitude=contract_attitude,
        reputation=state.reputation,
    )

    contract_rules = rules.get("contract_years", {"min": 2, "max": 7})
    contract_years = random.randint(int(contract_rules["min"]), int(contract_rules["max"]))

    hero = Hero(
        name=generate_name(existing_names),
        hero_class=class_name,
        age=age,
        level=level,
        xp=0,
        stats=stats,
        signing_bonus=signing_bonus,
        wage_per_year=wage_per_year,
        contract_years=contract_years,
        specialty=random_specialty_for_class(class_name),
        growth_rate=random_growth_rate(),
        contract_attitude=contract_attitude,
    )

    ensure_progression_fields(hero)
    _apply_training_steps(hero, _prior_development_steps_for_hero(hero))

    apply_reputation_to_contract(hero, state.reputation)
    assign_negotiation_profile(hero, developmental=False)
    return hero


def generate_developmental_hero(existing_names: Set[str], state) -> Hero:
    rules = load_hero_generation_rules()
    class_name = choose_class_for_state(rules, state)
    class_rules = rules["classes"][class_name]

    phase_name = choose_phase_for_new_recruit(class_name, developmental=True)
    age = choose_age_for_phase(class_name, phase_name)
    level = 1 if phase_name == "Rookie" else 2
    level = min(level, getattr(state.guild_upgrades, "recruit_level_cap", 1))

    stats = {}
    for stat, stat_range in class_rules["stat_ranges"].items():
        stats[stat] = random.randint(int(stat_range[0]), int(stat_range[1]))

    stats = scale_stats_for_level(stats, level, class_name)

    contract_attitude = random_contract_attitude()
    signing_bonus, wage_per_year = calculate_contract_values(
        hero_class=class_name,
        age=age,
        level=level,
        stats=stats,
        contract_attitude=contract_attitude,
        reputation=state.reputation,
    )

    hero = Hero(
        name=generate_name(existing_names),
        hero_class=class_name,
        age=age,
        level=level,
        xp=0,
        stats=stats,
        signing_bonus=max(25, int(signing_bonus * 0.55)),
        wage_per_year=max(1, int(wage_per_year * 0.60)),
        contract_years=random.randint(2, 4),
        specialty=random_specialty_for_class(class_name),
        growth_rate=random.choices(
            ["Mundane", "Talented", "Gifted"],
            weights=[25, 55, 20],
            k=1,
        )[0],
        contract_attitude=contract_attitude,
    )

    ensure_progression_fields(hero)
    hero.training_points = 0
    hero.training_path_progress = {}
    hero.unlocked_subclasses = []
    hero.unlocked_abilities = []
    hero.primary_subclass = None
    hero.subclass = None
    hero.special_ability = None

    apply_reputation_to_contract(hero, state.reputation)
    assign_negotiation_profile(hero, developmental=True)
    return hero


def generate_contract_market(
    state,
    count: int | None = None,
    include_developmental: bool = True,
    developmental_count: int = 3,
) -> List[Hero]:
    rules = load_hero_generation_rules()
    market_size = count or int(rules.get("market_size", 8))

    existing_names = {
        hero.name for hero in state.roster
    } | {
        hero.name for hero in state.available_contracts
    } | {
        hero.name for hero in state.retired_heroes
    } | {
        hero.name for hero in state.fallen_heroes
    }

    generated: List[Hero] = []

    normal_target = market_size
    if include_developmental:
        normal_target = max(0, market_size - developmental_count)

    while len(generated) < normal_target:
        hero = generate_hero(existing_names, state)
        existing_names.add(hero.name)
        generated.append(hero)

    if include_developmental:
        while len(generated) < market_size:
            hero = generate_developmental_hero(existing_names, state)
            existing_names.add(hero.name)
            generated.append(hero)

    tier_rank = {
        "Elite": 0,
        "Premium": 1,
        "Standard": 2,
        "Developmental": 3,
    }

    phase_rank = {
        "Prime": 0,
        "Rising": 1,
        "Veteran": 2,
        "Rookie": 3,
        "Elder": 4,
    }

    generated.sort(
        key=lambda hero: (
            tier_rank.get(getattr(hero, "market_tier", "Standard"), 9),
            phase_rank.get(career_phase_name(hero), 9),
            -int(getattr(hero, "level", 1)),
            -len(getattr(hero, "unlocked_subclasses", []) or []),
            int(getattr(hero, "age", 18)),
        )
    )

    return generated


def generate_fallback_contract_market(state, count: int = 8) -> List[Hero]:
    existing_names = {
        hero.name for hero in state.roster
    } | {
        hero.name for hero in state.available_contracts
    } | {
        hero.name for hero in state.retired_heroes
    } | {
        hero.name for hero in state.fallen_heroes
    }

    generated: List[Hero] = []
    while len(generated) < count:
        hero = generate_developmental_hero(existing_names, state)
        existing_names.add(hero.name)
        generated.append(hero)

    return generated