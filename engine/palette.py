"""
Color Palette and Vector Recoloring Engine
Handles parsing palettes from SVGs, managing built-in and custom schemes,
and recoloring vector illustrations according to strict slot mappings.
"""

import os
import re
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Tuple

try:
    ET.register_namespace("", "http://www.w3.org/2000/svg")
except Exception:
    pass


def normalize_color(color: str) -> str:
    """Normalize color to lowercase 6-digit hex string or keyword."""
    if not color:
        return ""
    c = color.strip().lower()
    if c == "white":
        return "#ffffff"
    if c == "black":
        return "#000000"
    if len(c) == 4 and c.startswith("#"):
        return f"#{c[1]*2}{c[2]*2}{c[3]*2}".lower()
    return c.lower()


class PaletteManager:
    """
    Manages illustration color schemes and performs vector recoloring.
    Slot 0: Background light
    Slot 1: Accent 1 (yellow/peach/pink)
    Slot 2: Background medium
    Slot 3: Accent 2 (coral/teal/blue)
    Slot 4: Background dark / Accent
    Slot 5: Accent 3 (soft tone)
    Slot 6: Outline / Ink (#181817)
    Slot 7: White (#ffffff)
    """

    def __init__(self, palettes_dir: str = "цветовая палитра"):
        self.palettes_dir = palettes_dir
        self.palettes: Dict[str, dict] = {}
        self.load_default_palettes()

    def parse_palette_svg(self, filepath: str) -> List[str]:
        """Parse 8 swatches from palette SVG in grid order."""
        tree = ET.parse(filepath)
        root = tree.getroot()
        swatches = []
        for el in root.iter():
            tag = el.tag.split("}")[-1]
            if tag in ("rect", "path"):
                fill = el.attrib.get("fill", "").strip()
                if not fill and tag == "path":
                    fill = "white"
                if fill and fill != "none":
                    x = float(el.attrib.get("x", 0))
                    y = float(el.attrib.get("y", 0))
                    if tag == "path" and "d" in el.attrib:
                        m = re.search(r"M([0-9.]+)\s+([0-9.]+)", el.attrib["d"])
                        if m:
                            x = float(m.group(1))
                            y = float(m.group(2))
                    swatches.append({"x": x, "y": y, "color": fill})

        # Sort by y-band (row), then x (col)
        swatches.sort(key=lambda s: (round(s["y"] / 50) * 50, s["x"]))
        return [normalize_color(s["color"]) for s in swatches]

    def load_default_palettes(self):
        """Load default Palettes 1, 2, 3 from the workspace directory."""
        # Built-in canonical fallback definitions in case files move
        default_data = [
            {
                "id": "palette_1",
                "name": "Сиреневая пастель (Схема 1)",
                "svg_file": "цвета1.svg",
                "bg_file": "фон1.svg",
                "fallback_colors": [
                    "#d7cdf5", "#f9ecb0", "#aa9bf0", "#f9a3aa",
                    "#7864d7", "#ffe3e1", "#181817", "#ffffff"
                ],
            },
            {
                "id": "palette_2",
                "name": "Персик и бирюза (Схема 2)",
                "svg_file": "цвета2.svg",
                "bg_file": "фон2.svg",
                "fallback_colors": [
                    "#fdd7b9", "#f9ecb0", "#fac896", "#80dada",
                    "#d27532", "#beebeb", "#181817", "#ffffff"
                ],
            },
            {
                "id": "palette_3",
                "name": "Мята, ультрамарин и роза (Схема 3)",
                "svg_file": "цвета3.svg",
                "bg_file": "фон3.svg",
                "fallback_colors": [
                    "#beebeb", "#ffd4f2", "#80dada", "#6d7bfc",
                    "#5abebe", "#b6c6fe", "#181817", "#ffffff"
                ],
            },
        ]

        for item in default_data:
            svg_path = os.path.join(self.palettes_dir, item["svg_file"])
            bg_path = os.path.join(self.palettes_dir, item["bg_file"])

            colors = item["fallback_colors"]
            if os.path.exists(svg_path):
                try:
                    parsed = self.parse_palette_svg(svg_path)
                    if len(parsed) >= 8:
                        colors = parsed[:8]
                except Exception as e:
                    print(f"Error parsing {svg_path}: {e}")

            bg_svg = ""
            if os.path.exists(bg_path):
                with open(bg_path, "r", encoding="utf-8") as f:
                    bg_svg = f.read()

            self.palettes[item["id"]] = {
                "id": item["id"],
                "name": item["name"],
                "colors": colors,
                "bg_file": item["bg_file"],
                "bg_svg": bg_svg,
                "is_custom": False,
            }

    def get_palette(self, palette_id: str) -> dict:
        """Get palette by ID with fallback to palette_1."""
        return self.palettes.get(palette_id, self.palettes.get("palette_1"))

    def list_palettes(self) -> List[dict]:
        """List all available palettes with metadata and color previews."""
        result = []
        for p in self.palettes.values():
            result.append({
                "id": p["id"],
                "name": p["name"],
                "colors": p["colors"],
                "bg_color": p["colors"][0],
                "accent_color": p["colors"][4],
                "is_custom": p.get("is_custom", False),
            })
        return result

    def add_custom_palette(self, name: str, colors: List[str], bg_svg: str = "") -> dict:
        """Register a user-defined custom palette."""
        norm_colors = [normalize_color(c) for c in colors]
        while len(norm_colors) < 8:
            norm_colors.append("#ffffff")
        norm_colors = norm_colors[:8]

        pal_id = f"custom_{len(self.palettes) + 1}_{re.sub(r'[^a-zA-Z0-9]', '_', name.lower())[:10]}"
        pal = {
            "id": pal_id,
            "name": name,
            "colors": norm_colors,
            "bg_file": None,
            "bg_svg": bg_svg,
            "is_custom": True,
        }
        self.palettes[pal_id] = pal
        return pal

    def add_palette_from_svg(self, svg_content: str, name: str = "Пользовательская палитра") -> dict:
        """Parse swatches from uploaded SVG string and register as new palette."""
        # Save temp or parse directly
        tree = ET.fromstring(svg_content)
        swatches = []
        for el in tree.iter():
            tag = el.tag.split("}")[-1]
            if tag in ("rect", "path", "circle"):
                fill = el.attrib.get("fill", "").strip()
                if not fill and tag == "path":
                    fill = "white"
                if fill and fill != "none":
                    x = float(el.attrib.get("x", 0))
                    y = float(el.attrib.get("y", 0))
                    if tag == "path" and "d" in el.attrib:
                        m = re.search(r"M([0-9.]+)\s+([0-9.]+)", el.attrib["d"])
                        if m:
                            x = float(m.group(1))
                            y = float(m.group(2))
                    swatches.append({"x": x, "y": y, "color": fill})

        if not swatches:
            # Fallback: regex search for all hex codes
            hex_found = re.findall(r"#[0-9a-fA-F]{6}|#[0-9a-fA-F]{3}", svg_content)
            unique_hex = []
            for h in hex_found:
                nh = normalize_color(h)
                if nh not in unique_hex:
                    unique_hex.append(nh)
            colors = unique_hex[:8]
        else:
            swatches.sort(key=lambda s: (round(s["y"] / 50) * 50, s["x"]))
            colors = [normalize_color(s["color"]) for s in swatches]

        return self.add_custom_palette(name, colors, bg_svg="")

    def recolor_svg(
        self,
        svg_content: str,
        target_palette_id: str,
        source_palette_id: str = "palette_1",
    ) -> str:
        """
        Recolor SVG content from source palette mapping to target palette.
        Ensures strict 1:1 color slot substitution.
        """
        if not target_palette_id or target_palette_id == source_palette_id:
            # Still ensure normalize case
            if target_palette_id == "palette_1" and source_palette_id == "palette_1":
                return svg_content

        src_pal = self.get_palette(source_palette_id)
        tgt_pal = self.get_palette(target_palette_id)

        src_colors = [normalize_color(c) for c in src_pal["colors"]]
        tgt_colors = [normalize_color(c) for c in tgt_pal["colors"]]

        # Build replacement mapping
        color_map: Dict[str, str] = {}
        for s, t in zip(src_colors, tgt_colors):
            color_map[s] = t

        # Also support named colors in source
        color_map["white"] = tgt_colors[7] if len(tgt_colors) > 7 else "#ffffff"
        color_map["black"] = tgt_colors[6] if len(tgt_colors) > 6 else "#181817"

        # Regex replacement that preserves case/format in attributes
        def replacer(match):
            raw = match.group(0)
            norm = normalize_color(raw)
            return color_map.get(norm, raw)

        # Match hex colors or keywords 'white'/'black'
        pattern = re.compile(
            r"#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})|\bwhite\b|\bblack\b",
            re.IGNORECASE,
        )
        return pattern.sub(replacer, svg_content)

    def get_background_svg(
        self,
        palette_id: str,
        width: int = 1000,
        height: int = 1000,
    ) -> str:
        """
        Get background pattern SVG recolored to the palette and fitted to dimensions.
        """
        pal = self.get_palette(palette_id)
        bg_svg = pal.get("bg_svg", "")

        bg_light = pal["colors"][0]

        if not bg_svg:
            # Generate solid or clean decorative background for custom palette
            accent = pal["colors"][4]
            sec = pal["colors"][2]
            return f"""<g id="canvas_background">
  <rect width="{width}" height="{height}" fill="{bg_light}"/>
  <circle cx="{width*0.1}" cy="{height*0.2}" r="{min(width,height)*0.15}" fill="{sec}" opacity="0.3"/>
  <circle cx="{width*0.85}" cy="{height*0.8}" r="{min(width,height)*0.2}" fill="{accent}" opacity="0.2"/>
</g>"""

        # Recolor the background SVG to the active palette if it came from palette_1 or another
        # Default bg_file was in its own colors, but if custom palette is chosen or scheme switched:
        recolored = self.recolor_svg(bg_svg, palette_id, source_palette_id="palette_1")

        # Extract inner elements
        try:
            tree = ET.fromstring(recolored)
            # Remove root <svg> tags, keep inner content wrapped in a responsive group
            inner = ""
            for child in tree:
                inner += ET.tostring(child, encoding="unicode")
            
            # Extract defs if any
            defs = ""
            for el in tree.findall(".//{http://www.w3.org/2000/svg}defs"):
                defs += ET.tostring(el, encoding="unicode")

            # Return as clean background group with responsive preserveAspectRatio
            return f"""<g id="canvas_background">
  <rect width="{width}" height="{height}" fill="{bg_light}"/>
  <svg x="0" y="0" width="{width}" height="{height}" viewBox="0 0 1000 1000" preserveAspectRatio="xMidYMid slice">
    {defs}
    {inner}
  </svg>
</g>"""
        except Exception as e:
            print(f"Error adapting bg SVG: {e}")
            return f"""<g id="canvas_background">
  <rect width="{width}" height="{height}" fill="{bg_light}"/>
</g>"""
