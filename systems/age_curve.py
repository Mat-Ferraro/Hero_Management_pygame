from dataclasses import dataclass


@dataclass(frozen=True)
class AgeCurveProfile:
    young_until: int
    prime_start: int
    prime_until: int
    elder_start: int
    retirement_age: int
    young_multiplier: float
    prime_multiplier: float
    elder_multiplier: float
    old_multiplier: float
    growth_label: str


AGE_CURVES = {
    "Warrior": AgeCurveProfile(
        young_until=24,
        prime_start=25,
        prime_until=38,
        elder_start=39,
        retirement_age=48,
        young_multiplier=0.90,
        prime_multiplier=1.12,
        elder_multiplier=0.95,
        old_multiplier=0.78,
        growth_label="physical prime",
    ),
    "Rogue": AgeCurveProfile(
        young_until=23,
        prime_start=24,
        prime_until=32,
        elder_start=33,
        retirement_age=42,
        young_multiplier=1.02,
        prime_multiplier=1.10,
        elder_multiplier=0.86,
        old_multiplier=0.68,
        growth_label="early peak",
    ),
    "Cleric": AgeCurveProfile(
        young_until=29,
        prime_start=30,
        prime_until=50,
        elder_start=51,
        retirement_age=68,
        young_multiplier=0.92,
        prime_multiplier=1.08,
        elder_multiplier=1.00,
        old_multiplier=0.88,
        growth_label="long service",
    ),
    "Mage": AgeCurveProfile(
        young_until=39,
        prime_start=40,
        prime_until=70,
        elder_start=71,
        retirement_age=95,
        young_multiplier=0.82,
        prime_multiplier=1.02,
        elder_multiplier=1.15,
        old_multiplier=1.22,
        growth_label="scholarly ascent",
    ),
}


DEFAULT_CURVE = AgeCurveProfile(
    young_until=25,
    prime_start=26,
    prime_until=40,
    elder_start=41,
    retirement_age=55,
    young_multiplier=0.90,
    prime_multiplier=1.05,
    elder_multiplier=0.95,
    old_multiplier=0.80,
    growth_label="standard career",
)


def age_curve_for_class(hero_class: str) -> AgeCurveProfile:
    return AGE_CURVES.get(hero_class, DEFAULT_CURVE)


def career_stage(hero) -> str:
    curve = age_curve_for_class(hero.hero_class)

    if hero.age <= curve.young_until:
        return "Developing"

    if hero.age <= curve.prime_until:
        return "Prime"

    if hero.age < curve.retirement_age:
        return "Veteran"

    return "Elder"


def age_power_multiplier(hero) -> float:
    curve = age_curve_for_class(hero.hero_class)

    if hero.age <= curve.young_until:
        return curve.young_multiplier

    if hero.age <= curve.prime_until:
        return curve.prime_multiplier

    if hero.age < curve.retirement_age:
        return curve.elder_multiplier

    return curve.old_multiplier


def retirement_age(hero) -> int:
    return age_curve_for_class(hero.hero_class).retirement_age


def retirement_pressure(hero) -> float:
    curve = age_curve_for_class(hero.hero_class)

    if hero.age <= curve.retirement_age:
        return 0.0

    years_over = hero.age - curve.retirement_age
    return min(0.75, years_over * 0.06)


def mentorship_value(hero) -> int:
    stage = career_stage(hero)

    if stage == "Developing":
        return 0

    if stage == "Prime":
        return 1

    if stage == "Veteran":
        return 2

    return 3


def career_summary(hero) -> str:
    curve = age_curve_for_class(hero.hero_class)
    stage = career_stage(hero)
    multiplier = age_power_multiplier(hero)

    return (
        f"{stage} | {curve.growth_label} | "
        f"Age Power x{multiplier:.2f} | "
        f"Retires around {curve.retirement_age}"
    )