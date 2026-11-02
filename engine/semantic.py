"""
Semantic Analysis and Metaphor Matching Engine (Scenario 1)
Translates headlines, metaphors, and conceptual themes into a harmonious
selection of main and background illustration components.
"""

import re
from typing import Dict, List, Tuple
from engine.library import COMPONENT_TAGS


# Conceptual domain clusters for thematic co-occurrence
THEMATIC_DOMAINS = {
    "FINANCE": {
        "keywords": [
            "финансы", "деньги", "доход", "расход", "прибыль", "капитал", "инвестиции",
            "бюджет", "сбережения", "банк", "валюта", "крипта", "биткоин", "зарплата",
            "кэш", "богатство", "экономика", "траты", "счет", "вклад", "дивиденды",
            "money", "finance", "cash", "wealth", "revenue", "profit", "investment"
        ],
        "primary": ["кошелёк", "монета"],
        "supporting": ["папка", "телефон"],
    },
    "EDUCATION": {
        "keywords": [
            "учеба", "образование", "книга", "чтение", "знания", "университет", "школа",
            "студент", "наука", "литература", "учебник", "лекция", "курс", "экзамен",
            "мудрость", "библиотека", "саморазвитие", "интеллект", "study", "learning",
            "education", "book", "knowledge", "science"
        ],
        "primary": ["книга", "лампа"],
        "supporting": ["ручка", "папка"],
    },
    "CREATIVITY": {
        "keywords": [
            "идея", "вдохновение", "креатив", "инсайт", "озарение", "творчество", "мысль",
            "дизайн", "новаторство", "изобретение", "прозрение", "искусство", "стартап",
            "созидание", "лампа", "свет", "idea", "creative", "inspiration", "insight"
        ],
        "primary": ["лампа", "пазлы"],
        "supporting": ["ручка", "книга", "цветы"],
    },
    "BUSINESS": {
        "keywords": [
            "бизнес", "работа", "офис", "проект", "документы", "отчет", "договор", "контракт",
            "клиенты", "переговоры", "организация", "дела", "задачи", "менеджмент", "корпорация",
            "планирование", "business", "work", "office", "project", "contract", "documents"
        ],
        "primary": ["папка", "ручка"],
        "supporting": ["телефон", "кошелёк"],
    },
    "TECHNOLOGY": {
        "keywords": [
            "технологии", "смартфон", "телефон", "приложение", "связь", "онлайн", "интернет",
            "соцсети", "чат", "мессенджер", "сообщения", "звонки", "цифровой", "it",
            "программирование", "софт", "phone", "mobile", "app", "tech", "digital"
        ],
        "primary": ["телефон", "наушники"],
        "supporting": ["папка", "пазлы"],
    },
    "AUDIO_RELAX": {
        "keywords": [
            "музыка", "звук", "аудио", "подкаст", "слушать", "наушники", "релакс", "отдых",
            "трек", "мелодия", "плейлист", "концентрация", "медитация", "тишина", "фокус",
            "music", "audio", "sound", "podcast", "headphones", "relaxation"
        ],
        "primary": ["наушники", "телефон"],
        "supporting": ["цветы", "книга"],
    },
    "LOGIC_STRATEGY": {
        "keywords": [
            "логика", "стратегия", "пазл", "задача", "решение", "структура", "система",
            "совместимость", "интеграция", "головоломка", "аналитика", "архитектура",
            "порядок", "сборка", "puzzle", "strategy", "logic", "solution", "system"
        ],
        "primary": ["пазлы", "лампа"],
        "supporting": ["папка", "телефон"],
    },
    "NATURE_HARMONY": {
        "keywords": [
            "цветы", "природа", "красота", "весна", "лето", "праздник", "подарок", "радость",
            "эмоции", "гармония", "уют", "эстетика", "букет", "жизнь", "растения",
            "flowers", "nature", "beauty", "gift", "celebration", "harmony"
        ],
        "primary": ["цветы", "книга"],
        "supporting": ["лампа", "наушники"],
    },
}


def simple_stem_ru(word: str) -> str:
    """Lightweight Russian stemmer to match word roots."""
    w = word.lower().strip()
    if len(w) <= 3:
        return w
    # Strip common inflections (longest first)
    suffixes = [
        "овать", "ывать", "ение", "ание", "ость", "ного", "ному",
        "ными", "ных", "овая", "евая", "овое", "евое", "овые", "евые",
        "овый", "евый", "скую", "ская", "ское", "ские", "ский",
        "ная", "ное", "ные", "ный", "ную", "ной",
        "ами", "ями", "ей", "ем", "ом", "ам", "ям", "ах", "ях",
        "ов", "ев", "ия", "ии", "ию", "ие", "ей", "ой", "ай",
        "ы", "и", "а", "я", "у", "ю", "е", "о"
    ]
    for s in suffixes:
        if w.endswith(s) and len(w) - len(s) >= 3:
            w = w[:-len(s)]
            break
    # Secondary strip if still long (e.g. финансова -> финансов -> финанс)
    for s in ["ов", "ев", "ск", "н"]:
        if w.endswith(s) and len(w) - len(s) >= 4:
            w = w[:-len(s)]
            break
    return w


STOP_WORDS = {
    "и", "в", "во", "на", "с", "со", "по", "для", "к", "ко", "о", "об", "а",
    "но", "не", "да", "из", "у", "от", "до", "за", "под", "при", "над", "без",
    "то", "как", "так", "все", "это", "the", "a", "an", "and", "or", "to",
    "in", "of", "for", "with", "on", "at", "by"
}


class SemanticEngine:
    """Matches text metaphors and headlines to balanced illustration compositions."""

    def __init__(self):
        # Pre-index component stems
        self.component_stems: Dict[str, List[str]] = {}
        for comp, tags in COMPONENT_TAGS.items():
            stems = [simple_stem_ru(t) for t in tags if t not in STOP_WORDS]
            self.component_stems[comp] = list(set(stems))

    def analyze_prompt(self, prompt: str) -> Dict[str, any]:
        """
        Analyze prompt text and select balanced components for the composition.
        """
        if not prompt or not prompt.strip():
            # Default balanced arrangement
            return {
                "hero": "лампа",
                "secondary": ["книга"],
                "background": ["папка"],
                "reasoning": "Базовая композиция: Лампа (идея) + Книга (знания) + Папка (организация).",
                "layout_preset": "triangular",
            }

        cleaned = prompt.lower()
        raw_words = re.findall(r"\b[a-zA-Zа-яА-ЯёЁ0-9_-]+\b", cleaned)
        words = [w for w in raw_words if w not in STOP_WORDS and len(w) >= 2]
        word_stems = [simple_stem_ru(w) for w in words]

        scores: Dict[str, float] = {comp: 0.0 for comp in COMPONENT_TAGS}

        # 1. Match direct component names and tags
        for comp, tags in COMPONENT_TAGS.items():
            for w in words:
                if w == comp:
                    scores[comp] += 15.0
                elif w in tags:
                    scores[comp] += 8.0

            # Match word stems
            comp_stems = self.component_stems[comp]
            for ws in word_stems:
                if ws in comp_stems:
                    scores[comp] += 6.0
                else:
                    # Substring root matching only if both length >= 4
                    for cs in comp_stems:
                        if len(cs) >= 4 and len(ws) >= 4 and (cs in ws or ws in cs):
                            scores[comp] += 3.5
                            break

        # 2. Check thematic domains
        domain_matches = []
        for domain_name, domain_data in THEMATIC_DOMAINS.items():
            domain_score = 0
            for w in words:
                if w in domain_data["keywords"]:
                    domain_score += 6.0
            for ws in word_stems:
                for kw in domain_data["keywords"]:
                    kws = simple_stem_ru(kw)
                    if kws == ws:
                        domain_score += 4.0
                    elif len(kws) >= 4 and len(ws) >= 4 and (kws in ws or ws in kws):
                        domain_score += 2.5

            if domain_score > 0:
                domain_matches.append((domain_name, domain_score))
                # Boost domain primary and supporting objects
                for p in domain_data["primary"]:
                    scores[p] += domain_score * 2.0
                for s in domain_data["supporting"]:
                    scores[s] += domain_score * 0.8

        # Rank components by score
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        # Filter out 0-score components if possible, or pick top ones
        chosen_candidates = [comp for comp, sc in ranked if sc > 0]
        if len(chosen_candidates) < 3:
            # Fallback fill with harmonious objects
            fallbacks = ["лампа", "книга", "телефон", "монета", "цветы", "папка"]
            for f in fallbacks:
                if f not in chosen_candidates:
                    chosen_candidates.append(f)
                if len(chosen_candidates) >= 4:
                    break

        hero = chosen_candidates[0]
        secondary = [chosen_candidates[1]] if len(chosen_candidates) > 1 else []
        background = [chosen_candidates[2]] if len(chosen_candidates) > 2 else []

        if len(chosen_candidates) > 3 and scores[chosen_candidates[3]] > 2.0:
            background.append(chosen_candidates[3])

        # Decide composition preset based on count
        total_items = 1 + len(secondary) + len(background)
        if total_items >= 4:
            layout_preset = "hero_accent"
        elif total_items == 3:
            layout_preset = "triangular"
        else:
            layout_preset = "dynamic_diagonal"

        # Generate human-readable reasoning
        reasons = []
        if domain_matches:
            top_domain = sorted(domain_matches, key=lambda x: x[1], reverse=True)[0][0]
            domain_titles = {
                "FINANCE": "Финансы и сбережения",
                "EDUCATION": "Образование и знания",
                "CREATIVITY": "Творчество и идеи",
                "BUSINESS": "Бизнес и организация",
                "TECHNOLOGY": "Технологии и связь",
                "AUDIO_RELAX": "Музыка и фокус",
                "LOGIC_STRATEGY": "Логика и стратегия",
                "NATURE_HARMONY": "Природа и гармония",
            }
            reasons.append(f"Определена тематика: {domain_titles.get(top_domain, top_domain)}.")

        reasons.append(f"Главный фокус: «{hero}».")
        if secondary:
            reasons.append(f"Второй цветной акцент: «{', '.join(secondary)}».")
        if background:
            reasons.append(f"Фоновый монохромный контекст: «{', '.join(background)}».")

        return {
            "hero": hero,
            "secondary": secondary,
            "background": background,
            "all_components": [hero] + secondary + background,
            "scores": {k: round(v, 2) for k, v in ranked[:6]},
            "reasoning": " ".join(reasons),
            "layout_preset": layout_preset,
        }
