import random


def generate_phone() -> str:
    """
    Генерирует номер в формате +79XXXXXXXXX.
    Пример: +79123456789
    """
    operator = random.randint(0, 9)          # код оператора
    tail = "".join(str(random.randint(0, 9)) for _ in range(8))
    return f"+79{operator}{tail}"


def generate_code() -> str:
    """Рандомный 6-значный код."""
    return f"{random.randint(100000, 999999)}"