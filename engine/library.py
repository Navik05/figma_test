"""
SVG Component Library Manager
Manages illustration components, L and S sizes, main and background states,
dimensions, semantic metadata, and dynamic uploads.
"""

import os
import re
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional
from engine.palette import PaletteManager, normalize_color


COMPONENT_TAGS = {
    "книга": [
        "книга", "книги", "чтение", "читать", "учеба", "образование",
        "знания", "литература", "библиотека", "статья", "текст", "наука",
        "развитие", "учебник", "студент", "уроки", "мудрость", "книжный",
        "book", "read", "learning", "education", "knowledge", "library"
    ],
    "кошелёк": [
        "кошелек", "кошелёк", "деньги", "финансы", "финансовый", "бюджет",
        "сбережения", "накопления", "расходы", "доходы", "зарплата", "капитал",
        "банк", "счет", "оплата", "траты", "баланс", "экономия", "богатство",
        "кэш", "wallet", "money", "finance", "budget", "savings", "cash"
    ],
    "лампа": [
        "лампа", "свет", "освещение", "идея", "идеи", "инсайт", "озарение",
        "вдохновение", "мысль", "открытие", "креатив", "лампочка", "светильник",
        "ум", "гений", "решение", "lamp", "light", "idea", "insight", "inspiration"
    ],
    "монета": [
        "монета", "монеты", "денежка", "деньги", "прибыль", "доход", "процент",
        "проценты", "инвестиции", "вклад", "ценность", "дивиденды", "кэшбэк",
        "богатство", "золото", "крипта", "капитал", "coin", "coins", "profit",
        "revenue", "investment", "dividend"
    ],
    "наушники": [
        "наушники", "звук", "аудио", "музыка", "трек", "мелодия", "подкаст",
        "подкасты", "слушать", "релакс", "концентрация", "тишина", "радио",
        "плейлист", "стриминг", "звонок", "headphones", "sound", "audio", "music",
        "podcast", "listening"
    ],
    "пазлы": [
        "пазл", "пазлы", "паззл", "деталь", "детали", "сборка", "собрать",
        "структура", "система", "логика", "стратегия", "совместимость",
        "интеграция", "компоненты", "головоломка", "архитектура", "порядок",
        "puzzle", "logic", "strategy", "assembly", "integration"
    ],
    "папка": [
        "папка", "папки", "документ", "документы", "файлы", "архив", "дела",
        "кейс", "проект", "проекты", "организация", "отчет", "бухгалтерия",
        "канцелярия", "порядок", "договор", "folder", "documents", "files",
        "archive", "project", "organization"
    ],
    "ручка": [
        "ручка", "писать", "письмо", "запись", "заметка", "заметки", "подпись",
        "подписать", "контракт", "договор", "автор", "писатель", "правки",
        "чернила", "перо", "pen", "write", "writing", "notes", "signature"
    ],
    "телефон": [
        "телефон", "смартфон", "связь", "мобильный", "звонок", "звонки", "экран",
        "приложение", "чат", "сообщения", "мессенджер", "интернет", "онлайн",
        "гаджет", "соцсети", "девайс", "коммуникация", "phone", "mobile",
        "smartphone", "app", "call", "communication"
    ],
    "цветы": [
        "цветы", "цветок", "букет", "флора", "природа", "растение", "растения",
        "весна", "лето", "праздник", "подарок", "поздравление", "радость",
        "эмоции", "красота", "гармония", "уют", "жизнь", "flowers", "bouquet",
        "nature", "plant", "spring", "beauty", "gift"
    ]
}


class ComponentLibrary:
    """Manages illustration library components with Size L and S support."""

    def __init__(
        self,
        main_dir_l: str = "главные объекты",
        bg_dir_l: str = "фоновые объекты",
        main_dir_s: str = "главные объекты_S",
        bg_dir_s: str = "фоновые объекты_S",
        palette_manager: Optional[PaletteManager] = None
    ):
        self.main_dir_l = main_dir_l
        self.bg_dir_l = bg_dir_l
        self.main_dir_s = main_dir_s
        self.bg_dir_s = bg_dir_s
        self.palette_mgr = palette_manager or PaletteManager()
        
        # Ensure S directories exist so users can upload S files
        os.makedirs(self.main_dir_s, exist_ok=True)
        os.makedirs(self.bg_dir_s, exist_ok=True)

        self._cache: Dict[str, dict] = {}
        self.refresh()

    def refresh(self):
        """Scan directory and index all available components."""
        self._cache = {}
        if not os.path.exists(self.main_dir_l):
            return

        for filename in sorted(os.listdir(self.main_dir_l)):
            if not filename.endswith(".svg"):
                continue

            name = os.path.splitext(filename)[0]
            main_path_l = os.path.join(self.main_dir_l, filename)
            bg_path_l = os.path.join(self.bg_dir_l, filename)

            main_path_s = os.path.join(self.main_dir_s, filename)
            bg_path_s = os.path.join(self.bg_dir_s, filename)

            has_size_s = os.path.exists(main_path_s)

            # Parse dimensions from L
            w, h, vb = self._get_svg_meta(main_path_l)

            tags = COMPONENT_TAGS.get(name, [name])

            self._cache[name] = {
                "name": name,
                "filename": filename,
                "width": w,
                "height": h,
                "viewBox": vb,
                "aspect_ratio": round(w / h, 4) if h else 1.0,
                "tags": tags,
                "has_size_l": True,
                "has_size_s": has_size_s,
                "main_path_l": main_path_l,
                "bg_path_l": bg_path_l if os.path.exists(bg_path_l) else None,
                "main_path_s": main_path_s if has_size_s else None,
                "bg_path_s": bg_path_s if os.path.exists(bg_path_s) else None,
            }

    def _get_svg_meta(self, filepath: str) -> tuple:
        """Extract width, height, and viewBox from SVG file."""
        try:
            tree = ET.parse(filepath)
            root = tree.getroot()
            vb = root.attrib.get("viewBox", "")
            w = float(root.attrib.get("width", 0))
            h = float(root.attrib.get("height", 0))

            if (not w or not h) and vb:
                parts = [float(x) for x in vb.split()]
                if len(parts) == 4:
                    w = parts[2]
                    h = parts[3]

            if not vb and w and h:
                vb = f"0 0 {int(w)} {int(h)}"

            return w or 500.0, h or 500.0, vb or "0 0 500 500"
        except Exception as e:
            print(f"Error parsing meta for {filepath}: {e}")
            return 500.0, 500.0, "0 0 500 500"

    def list_components(self, active_size: str = "L") -> List[dict]:
        """Return list of component metadata, indicating size availability."""
        result = []
        for c in self._cache.values():
            result.append({
                "name": c["name"],
                "width": c["width"],
                "height": c["height"],
                "aspect_ratio": c["aspect_ratio"],
                "viewBox": c["viewBox"],
                "tags": c["tags"],
                "has_size_l": c["has_size_l"],
                "has_size_s": c["has_size_s"],
                "active_size_available": (c["has_size_s"] if active_size.upper() == "S" else c["has_size_l"]),
            })
        return result

    def get_component_svg(
        self,
        name: str,
        is_background: bool = False,
        size: str = "L",
        palette_id: str = "palette_1"
    ) -> str:
        """
        Get SVG markup for component, applying size, role, and palette recoloring.
        """
        comp = self._cache.get(name)
        if not comp:
            return ""

        size_up = size.upper()
        # Pick file path
        if size_up == "S" and comp["has_size_s"]:
            if is_background and comp["bg_path_s"]:
                path = comp["bg_path_s"]
            else:
                path = comp["main_path_s"]
        else:
            if is_background and comp["bg_path_l"]:
                path = comp["bg_path_l"]
            else:
                path = comp["main_path_l"]

        if not path or not os.path.exists(path):
            return ""

        with open(path, "r", encoding="utf-8") as f:
            svg_content = f.read()

        # If background requested but only main was available, auto-synthesize
        if is_background and ((size_up == "S" and not comp["bg_path_s"]) or (size_up != "S" and not comp["bg_path_l"])):
            svg_content = self.convert_to_monochrome(svg_content)

        # Apply palette recoloring
        if palette_id and palette_id != "palette_1":
            svg_content = self.palette_mgr.recolor_svg(svg_content, target_palette_id=palette_id)

        return svg_content

    def convert_to_monochrome(self, svg_content: str) -> str:
        """Synthesize 2-tone background monochrome version from any SVG."""
        def repl(m):
            c = m.group(0).lower()
            if c in ("#181817", "#000000", "black"):
                return "#7864D7"
            return "#D7CDF5"

        return re.sub(r"#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})|\bwhite\b|\bblack\b", repl, svg_content)

    def add_component(
        self,
        name: str,
        main_svg: str,
        bg_svg: Optional[str] = None,
        size: str = "L",
        tags: Optional[List[str]] = None
    ) -> dict:
        """Save a new SVG component to the library."""
        size_up = size.upper()
        main_dir = self.main_dir_s if size_up == "S" else self.main_dir_l
        bg_dir = self.bg_dir_s if size_up == "S" else self.bg_dir_l

        safe_name = re.sub(r'[/\\?%*:|"<>]', "", name.strip())
        filename = f"{safe_name}.svg"

        main_path = os.path.join(main_dir, filename)
        with open(main_path, "w", encoding="utf-8") as f:
            f.write(main_svg)

        bg_path = os.path.join(bg_dir, filename)
        if not bg_svg:
            bg_svg = self.convert_to_monochrome(main_svg)
        with open(bg_path, "w", encoding="utf-8") as f:
            f.write(bg_svg)

        if tags:
            current_tags = COMPONENT_TAGS.get(safe_name, [safe_name])
            current_tags.extend(tags)
            COMPONENT_TAGS[safe_name] = list(set(current_tags))

        self.refresh()
        return self._cache.get(safe_name, {})
