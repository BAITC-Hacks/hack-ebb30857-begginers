"""Deterministic city simulation engine for Akim AI."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

DATA_PATH = Path(__file__).parent / "data" / "city_data.json"

INDICATOR_LABELS = {
    "transport": "Транспорт",
    "green": "Зеленые зоны",
    "social": "Социальная инфраструктура",
    "safety": "Безопасность",
    "services": "Городские услуги",
}

INDICATOR_GROW = {
    "transport": "вырос",
    "green": "выросли",
    "social": "выросла",
    "safety": "выросла",
    "services": "выросли",
}

INDICATOR_FALL = {
    "transport": "снизился",
    "green": "снизились",
    "social": "снизилась",
    "safety": "снизилась",
    "services": "снизились",
}

REQUIRED_CATEGORIES = ("transport", "green", "social", "safety", "services")


def load_city_data() -> dict[str, Any]:
    with DATA_PATH.open(encoding="utf-8") as file:
        return json.load(file)


def points_word(value: int) -> str:
    n = abs(value) % 100
    if 11 <= n <= 14:
        return "пунктов"
    last = n % 10
    if last == 1:
        return "пункт"
    if last in (2, 3, 4):
        return "пункта"
    return "пунктов"


def clamp(value: float, minimum: int = 0, maximum: int = 100) -> int:
    return int(max(minimum, min(maximum, round(value))))


def _category_map(city_data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {category["id"]: category for category in city_data["categories"]}


def resolve_measure(category: dict[str, Any], measure_id: str) -> dict[str, Any]:
    for measure in category["measures"]:
        if measure["id"] == measure_id:
            return measure
    raise ValueError(f"Мера «{measure_id}» не найдена в категории «{category['id']}».")


def calculate_aqol(indicators: dict[str, int], weights: dict[str, float]) -> int:
    score = sum(indicators[key] * weights[key] for key in REQUIRED_CATEGORIES)
    return int(round(score))


def apply_effects(baseline: dict[str, int], measures: list[dict[str, Any]]) -> dict[str, int]:
    totals = {key: float(baseline[key]) for key in REQUIRED_CATEGORIES}
    for measure in measures:
        for indicator, delta in measure.get("effects", {}).items():
            if indicator in totals:
                totals[indicator] += delta
    return {key: clamp(value) for key, value in totals.items()}


def mock_analysis(
    indicators: dict[str, int],
    baseline: dict[str, int],
    aqol: int,
    budget_used: int,
    budget_total: int,
    selected: list[dict[str, Any]],
) -> dict[str, Any]:
    deltas = {key: indicators[key] - baseline[key] for key in REQUIRED_CATEGORIES}
    ranked_up = sorted(deltas.items(), key=lambda item: item[1], reverse=True)
    ranked_down = sorted(deltas.items(), key=lambda item: item[1])
    remaining = budget_total - budget_used

    if aqol >= 70:
        summary = (
            f"Сценарий даёт высокий индекс качества жизни Астаны: {aqol} из 100. "
            "Выбранный пакет мер заметно улучшает городской баланс и может быть "
            "представлен как сильный управленческий кейс."
        )
    elif aqol >= 55:
        summary = (
            f"Сценарий даёт средний индекс качества жизни: {aqol} из 100. "
            "Есть ощутимый прогресс, но часть направлений остаётся недоинвестированной "
            "или получает побочные эффекты."
        )
    else:
        summary = (
            f"Сценарий даёт низкий индекс качества жизни: {aqol} из 100. "
            "Текущий набор решений недостаточно поднимает ключевые показатели "
            "или создаёт перекос между направлениями."
        )

    strengths: list[str] = []
    for key, delta in ranked_up:
        if delta > 0:
            strengths.append(
                f"{INDICATOR_LABELS[key]} {INDICATOR_GROW[key]} на {delta} "
                f"{points_word(delta)} и достиг {indicators[key]}/100."
            )
        if len(strengths) >= 3:
            break
    if remaining >= 20_000_000_000:
        strengths.append(
            f"В бюджете осталось {remaining // 1_000_000_000} млрд ₸ — "
            "есть резерв на корректировки."
        )
    if not strengths:
        strengths.append("Сценарий сохраняет исходный уровень без резкого падения показателей.")

    risks: list[str] = []
    for key, delta in ranked_down:
        if delta < 0:
            risks.append(
                f"{INDICATOR_LABELS[key]} {INDICATOR_FALL[key]} на {abs(delta)} "
                f"{points_word(delta)} из-за побочных эффектов выбранных мер."
            )
        if len(risks) >= 2:
            break
    lowest = min(indicators.items(), key=lambda item: item[1])
    if lowest[1] < 55:
        risks.append(
            f"Слабое место сценария — {INDICATOR_LABELS[lowest[0]]} ({lowest[1]}/100)."
        )
    if remaining < 5_000_000_000:
        risks.append("Почти весь бюджет израсходован: пространства для манёвра почти нет.")
    spread = max(indicators.values()) - min(indicators.values())
    if spread >= 25:
        risks.append("Показатели несбалансированы: разрыв между направлениями слишком большой.")
    if not risks:
        risks.append("Существенных рисков не выявлено, но эффект стоит проверить на пилотном районе.")

    consequences = [
        f"Выбрано: {measure['category_title']} — {measure['name']} "
        f"({measure['cost'] // 1_000_000_000} млрд ₸)."
        for measure in selected
    ]
    consequences.append(
        f"Итог: AQOL {aqol}/100 при бюджете {budget_used // 1_000_000_000} из "
        f"{budget_total // 1_000_000_000} млрд ₸."
    )

    return {
        "summary": summary,
        "strengths": strengths[:4],
        "risks": risks[:4],
        "consequences": consequences,
        "source": "mock",
    }


def try_ai_analysis(payload: dict[str, Any], mock: dict[str, Any]) -> dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return mock

    try:
        import json as json_lib
        import urllib.request

        prompt = (
            "Ты городской аналитик Астаны. По данным симуляции напиши JSON "
            "с полями summary (строка), strengths (массив из 3 строк), "
            "risks (массив из 3 строк), consequences (массив из 3-5 строк). "
            "Не пересчитывай AQOL, используй уже готовый балл. Отвечай на русском.\n\n"
            f"{json_lib.dumps(payload, ensure_ascii=False)}"
        )
        body = json_lib.dumps(
            {
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.4,
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=12) as response:
            raw = json_lib.loads(response.read().decode("utf-8"))
        content = raw["choices"][0]["message"]["content"]
        parsed = json_lib.loads(content)
        return {
            "summary": parsed.get("summary", mock["summary"]),
            "strengths": parsed.get("strengths", mock["strengths"]),
            "risks": parsed.get("risks", mock["risks"]),
            "consequences": parsed.get("consequences", mock["consequences"]),
            "source": "ai",
        }
    except Exception:
        return mock


def run_simulation(decisions: dict[str, str]) -> dict[str, Any]:
    city_data = load_city_data()
    categories = _category_map(city_data)
    missing = [key for key in REQUIRED_CATEGORIES if not decisions.get(key)]
    if missing:
        raise ValueError("Нужно выбрать по одной мере в каждом из пяти направлений.")

    selected: list[dict[str, Any]] = []
    budget_used = 0
    for category_id in REQUIRED_CATEGORIES:
        category = categories[category_id]
        measure = resolve_measure(category, decisions[category_id])
        budget_used += measure["cost"]
        selected.append(
            {
                "id": measure["id"],
                "name": measure["name"],
                "cost": measure["cost"],
                "effects": measure["effects"],
                "category_id": category_id,
                "category_title": category["title"],
            }
        )

    budget_total = city_data["budget_total"]
    if budget_used > budget_total:
        over = (budget_used - budget_total) // 1_000_000_000
        raise ValueError(
            f"Бюджет превышен на {over} млрд ₸. Измените набор мер, чтобы уложиться в 100 млрд ₸."
        )

    indicators = apply_effects(city_data["baseline"], selected)
    aqol = calculate_aqol(indicators, city_data["weights"])
    mock = mock_analysis(
        indicators=indicators,
        baseline=city_data["baseline"],
        aqol=aqol,
        budget_used=budget_used,
        budget_total=budget_total,
        selected=selected,
    )
    analysis = try_ai_analysis(
        {
            "aqol_score": aqol,
            "indicators": indicators,
            "baseline": city_data["baseline"],
            "budget_used": budget_used,
            "selected": [
                {"category": item["category_title"], "name": item["name"], "cost": item["cost"]}
                for item in selected
            ],
        },
        mock,
    )

    return {
        "budget_used": budget_used,
        "budget_remaining": budget_total - budget_used,
        "indicators": indicators,
        "aqol_score": aqol,
        "selected": [
            {
                "category_id": item["category_id"],
                "category_title": item["category_title"],
                "measure_id": item["id"],
                "name": item["name"],
                "cost": item["cost"],
            }
            for item in selected
        ],
        "analysis": analysis,
    }
