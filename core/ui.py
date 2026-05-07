def color_text(text: str, color: str | None = None) -> str:
    return str(text)


def pad_col(text: str, width: int, color: str | None = None, align: str = "left") -> str:
    raw = str(text)

    if len(raw) > width:
        if width <= 1:
            raw = raw[:width]
        else:
            raw = raw[: width - 1] + "…"

    if align == "right":
        return raw.rjust(width)

    return raw.ljust(width)


def success(text: str) -> str:
    return str(text)


def warning(text: str) -> str:
    return str(text)


def danger(text: str) -> str:
    return str(text)


def info(text: str) -> str:
    return str(text)


def highlight(text: str) -> str:
    return str(text)


def bold(text: str) -> str:
    return str(text)


def dim(text: str) -> str:
    return str(text)


def color_class(hero_class: str) -> str:
    return str(hero_class)


def color_damage_type(damage_type: str) -> str:
    return str(damage_type)


def color_growth_rate(growth_rate: str) -> str:
    return str(growth_rate)


def color_contract_attitude(contract_attitude: str) -> str:
    return str(contract_attitude)


def color_health_status(status: str) -> str:
    return str(status)


def color_money_value(amount: int, low: int = 100, high: int = 300) -> str:
    return f"{amount}g"