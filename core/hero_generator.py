import random
from typing import Dict, List, Set

from contract_attitudes import attitude_multiplier, random_contract_attitude
from data_loader import load_hero_generation_rules, load_hero_names
from growth_rates import random_growth_rate
from hero_specialties import random_specialty_for_class
from models import Hero


def weighted_choice(weight_map: Dict[str, int]) -> str:
    total = sum(int(weight) for weight in weight_map.values())
    roll = random.randint(1, total)
    running = 0

    for value, weight in weight_map.items():
        running += int(weight)
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


def scale_stats_for_level(stats: Dict[str, int], level: int, hero_class: str) -> Dict[str, int]:
    if level <= 1:
        return stats

    primary_stats = {
        "Warrior": ["might"],
        "Rogue": ["agility"],
        "Cleric": ["spirit"],
        "Mage": ["mind"],
    }.get(hero_class, [])

    scaled = dict(stats)

    for _ in range(level - 1):
        for stat in primary_stats:
            scaled[stat] = scaled.get(stat, 0) + 2

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
        "Rogue": ["might"],
        "Cleric": ["mind"],
        "Mage": ["spirit"],
    }.get(hero_class, [])

    primary_power = sum(stats.get(stat, 0) * 3 for stat in primary)
    secondary_power = sum(stats.get(stat, 0) * 2 for stat in secondary)
    general_power = sum(stats.values())
    return max(1, primary_power + secondary_power + general_power + level * 5)


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


def choose_level_for_state(class_rules: Dict, state) -> int:
    level_cap = getattr(state.guild_upgrades, "recruit_level_cap", 1)
    level_weights = class_rules.get("level_weights", {"1": 1})

    capped_weights = {
        level: weight
        for level, weight in level_weights.items()
        if int(level) <= level_cap
    }

    if not capped_weights:
        capped_weights = {"1": 1}

    return int(weighted_choice(capped_weights))


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

    if hero.level >= 5 or growth_rank >= 4:
        return "Elite"
    if hero.level >= 3 or growth_rank >= 3:
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
    asking_fee_per_campaign = max(10, int(round(asking_signing_fee / preferred_campaigns)))

    if hero.age <= 24:
        preferred_campaigns = max(preferred_campaigns, 3)
        profile["development_weight"] += 0.02
        profile["mentorship_weight"] += 0.02

    if hero.age >= 38:
        preferred_campaigns = max(1, preferred_campaigns - 1)
        profile["safety_weight"] += 0.03
        profile["reputation_weight"] += 0.03

    if developmental:
        preferred_campaigns = max(2, min(preferred_campaigns, 4))
        asking_signing_fee = max(25, int(asking_signing_fee * 0.55))
        asking_fee_per_campaign = max(10, int(round(asking_signing_fee / preferred_campaigns)))
        profile["development_weight"] += 0.05
        profile["money_per_campaign_weight"] = max(0.64, profile["money_per_campaign_weight"] - 0.06)

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


def generate_hero(existing_names: Set[str], state) -> Hero:
    rules = load_hero_generation_rules()
    class_name = choose_class_for_state(rules, state)
    class_rules = rules["classes"][class_name]

    age = random.randint(class_rules["age_min"], class_rules["age_max"])
    level = choose_level_for_state(class_rules, state)

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

    apply_reputation_to_contract(hero, state.reputation)
    assign_negotiation_profile(hero, developmental=False)
    return hero


def generate_developmental_hero(existing_names: Set[str], state) -> Hero:
    hero = generate_hero(existing_names, state)

    hero.age = random.randint(18, 24)
    hero.level = 1
    hero.xp = 0
    hero.contract_years = random.randint(2, 4)

    hero.growth_rate = random.choices(
        ["Mundane", "Talented", "Gifted"],
        weights=[25, 55, 20],
        k=1,
    )[0]

    hero.signing_bonus = max(25, int(hero.signing_bonus * 0.50))
    hero.wage_per_year = max(1, int(hero.wage_per_year * 0.60))

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

    random.shuffle(generated)
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