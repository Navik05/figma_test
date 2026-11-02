"""
SVG Export and Assembly Engine
Constructs production-grade, editable vector SVG documents preserving
exact original geometries, layer orders, color mappings, and isolated namespaces.
"""

import re
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional
from engine.library import ComponentLibrary
from engine.palette import PaletteManager

# Ensure default SVG namespace is clean without ns0: prefix
try:
    ET.register_namespace("", "http://www.w3.org/2000/svg")
except Exception:
    pass


class SvgExporter:
    """Builds clean, collision-free, fully editable vector SVG compositions."""

    def __init__(self, library: ComponentLibrary, palette_manager: PaletteManager):
        self.library = library
        self.palette_mgr = palette_manager

    def build_composition_svg(
        self,
        canvas_width: int,
        canvas_height: int,
        items: List[Dict[str, any]],
        palette_id: str = "palette_1",
        background_type: str = "pattern",  # 'pattern', 'solid', 'white', 'transparent'
        size: str = "L"
    ) -> str:
        """
        Assemble all layers and objects into a standalone vector SVG document.
        """
        canvas_width = int(canvas_width)
        canvas_height = int(canvas_height)

        # Sort items strictly by z_index
        sorted_items = sorted(items, key=lambda it: it.get("z_index", 0))

        svg_parts = []
        all_defs = []

        # 1. Background layer
        if background_type == "pattern":
            bg_markup = self.palette_mgr.get_background_svg(
                palette_id=palette_id, width=canvas_width, height=canvas_height
            )
            svg_parts.append(bg_markup)
        elif background_type == "solid":
            pal = self.palette_mgr.get_palette(palette_id)
            bg_color = pal["colors"][0]
            svg_parts.append(f'<rect width="{canvas_width}" height="{canvas_height}" fill="{bg_color}"/>')
        elif background_type == "white":
            svg_parts.append(f'<rect width="{canvas_width}" height="{canvas_height}" fill="#ffffff"/>')

        # 2. Composition objects
        for item in sorted_items:
            name = item["name"]
            is_bg = item.get("is_background", False)
            item_id = item.get("id", f"obj_{name}")
            x = float(item.get("x", 0))
            y = float(item.get("y", 0))
            scale = float(item.get("scale", 1.0))
            rotation = float(item.get("rotation", 0))

            raw_svg = self.library.get_component_svg(
                name=name,
                is_background=is_bg,
                size=size,
                palette_id=palette_id
            )
            if not raw_svg:
                continue

            # Prefix IDs in raw SVG to avoid cross-element collisions (like clipPaths)
            prefixed_svg = self._prefix_ids(raw_svg, item_id)

            # Extract inner content and defs
            inner_markup, defs_markup, nat_w, nat_h = self._extract_inner(prefixed_svg)
            if defs_markup:
                all_defs.append(defs_markup)

            # Center rotation pivot on object center
            cx = nat_w / 2.0
            cy = nat_h / 2.0

            # Transform: translate, then rotate around center, then scale
            transform = f"translate({x:.2f}, {y:.2f}) rotate({rotation:.2f}, {cx * scale:.2f}, {cy * scale:.2f}) scale({scale:.4f})"

            layer_class = "background-object" if is_bg else "main-object"
            svg_parts.append(
                f'<g id="{item_id}" class="illustration-component {layer_class}" data-name="{name}" transform="{transform}">\n'
                f"{inner_markup}\n"
                f"</g>"
            )

        # Assemble full document
        defs_block = ""
        if all_defs:
            defs_block = "<defs>\n" + "\n".join(all_defs) + "\n</defs>\n"

        content_body = "\n".join(svg_parts)

        return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {canvas_width} {canvas_height}" width="{canvas_width}" height="{canvas_height}" fill="none">
{defs_block}
{content_body}
</svg>"""

    def _prefix_ids(self, svg_text: str, prefix: str) -> str:
        """Namespace all id attributes and url references."""
        # Find all id="..."
        id_matches = set(re.findall(r'\bid=["\']([^"\']+)["\']', svg_text))
        result = svg_text
        for orig_id in id_matches:
            new_id = f"{prefix}_{orig_id}"
            result = result.replace(f'id="{orig_id}"', f'id="{new_id}"')
            result = result.replace(f"id='{orig_id}'", f"id='{new_id}'")
            result = result.replace(f'url(#{orig_id})', f'url(#{new_id})')
            result = result.replace(f"url('#{orig_id}')", f"url('#{new_id}')")
            result = result.replace(f'href="#{orig_id}"', f'href="#{new_id}"')
        return result

    def _extract_inner(self, svg_text: str) -> tuple:
        """Extract inner content, defs, and dimensions from an SVG element string."""
        try:
            tree = ET.fromstring(svg_text)
            w = float(tree.attrib.get("width", 500))
            h = float(tree.attrib.get("height", 500))

            defs_markup = ""
            inner_markup = ""

            for child in tree:
                tag = child.tag.split("}")[-1]
                if tag == "defs":
                    for d_child in child:
                        defs_markup += ET.tostring(d_child, encoding="unicode") + "\n"
                else:
                    inner_markup += ET.tostring(child, encoding="unicode") + "\n"

            return inner_markup.strip(), defs_markup.strip(), w, h
        except Exception as e:
            print(f"Error parsing inner SVG: {e}")
            # Fallback regex extraction
            body = re.sub(r"^<svg[^>]*>", "", svg_text.strip(), flags=re.IGNORECASE)
            body = re.sub(r"</svg>$", "", body.strip(), flags=re.IGNORECASE)
            return body.strip(), "", 500.0, 500.0
