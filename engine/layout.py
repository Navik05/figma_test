"""
Layout and Composition Engine (Scenarios 1 & 2)
Generates harmonious, balanced vector arrangements while strictly preserving
relative proportions and aspect ratios.
"""

import math
import random
from typing import Dict, List, Optional


class LayoutEngine:
    """Calculates balanced coordinates, scales, rotations, and layering for compositions."""

    PRESETS = ["hero_accent", "triangular", "dynamic_diagonal", "editorial_split", "still_life"]

    def __init__(self):
        pass

    def compose_scene(
        self,
        items: List[Dict[str, any]],
        canvas_width: int = 1000,
        canvas_height: int = 1000,
        preset: Optional[str] = None,
        seed: Optional[int] = None
    ) -> List[Dict[str, any]]:
        """
        Arrange items on canvas using chosen preset or automated selection.
        Each item has: name, natural_width, natural_height, is_background.
        """
        if not items:
            return []

        rng = random.Random(seed) if seed is not None else random.Random()

        if not preset or preset not in self.PRESETS:
            count = len(items)
            if count == 1:
                preset = "hero_accent"
            elif count == 2:
                preset = "editorial_split"
            elif count == 3:
                preset = "triangular"
            elif count >= 4:
                preset = rng.choice(["hero_accent", "dynamic_diagonal", "still_life"])

        # Baseline uniform scale factor so objects maintain relative proportions
        # Largest dimension reference is ~1400px; on 1000px canvas, base scale is ~0.45
        ref_dim = min(canvas_width, canvas_height)
        base_scale = (ref_dim / 1000.0) * 0.44

        # Separate main and background items
        main_items = [it for it in items if not it.get("is_background", False)]
        bg_items = [it for it in items if it.get("is_background", False)]

        # If all items are same type, make first one main
        if not main_items and bg_items:
            main_items = [bg_items.pop(0)]
            main_items[0]["is_background"] = False

        placed_items = []
        ordered_all = main_items + bg_items

        if preset == "triangular":
            placed_items = self._layout_triangular(
                main_items, bg_items, canvas_width, canvas_height, base_scale, rng
            )
        elif preset == "dynamic_diagonal":
            placed_items = self._layout_diagonal(
                main_items, bg_items, canvas_width, canvas_height, base_scale, rng
            )
        elif preset == "editorial_split":
            placed_items = self._layout_editorial(
                main_items, bg_items, canvas_width, canvas_height, base_scale, rng
            )
        elif preset == "still_life":
            placed_items = self._layout_still_life(
                main_items, bg_items, canvas_width, canvas_height, base_scale, rng
            )
        else:  # hero_accent
            placed_items = self._layout_hero_accent(
                main_items, bg_items, canvas_width, canvas_height, base_scale, rng
            )

        # Assign unique element IDs and normalize z-indexes
        # Background objects always have lower z-indexes (0..M), main objects have (M+1..N)
        bg_placed = [p for p in placed_items if p["is_background"]]
        main_placed = [p for p in placed_items if not p["is_background"]]

        final_list = []
        current_z = 0
        for p in bg_placed:
            p["z_index"] = current_z
            current_z += 1
            final_list.append(p)

        for p in main_placed:
            p["z_index"] = current_z
            current_z += 1
            final_list.append(p)

        for idx, item in enumerate(final_list):
            item["id"] = f"elem_{idx + 1}_{item['name']}"

        return final_list

    def _layout_hero_accent(self, main_items, bg_items, cw, ch, base_scale, rng):
        result = []
        hero = main_items[0] if main_items else bg_items[0]
        # Hero placed near center
        hero_scale = base_scale * 1.15
        hw = hero["natural_width"] * hero_scale
        hh = hero["natural_height"] * hero_scale
        hx = (cw - hw) / 2.0 + rng.uniform(-cw * 0.05, cw * 0.05)
        hy = (ch - hh) / 2.0 + rng.uniform(-ch * 0.04, ch * 0.04)
        hrot = rng.uniform(-6, 6)

        result.append({
            "name": hero["name"],
            "is_background": hero.get("is_background", False),
            "x": round(hx, 1),
            "y": round(hy, 1),
            "scale": round(hero_scale, 4),
            "rotation": round(hrot, 1),
            "natural_width": hero["natural_width"],
            "natural_height": hero["natural_height"],
            "viewBox": hero.get("viewBox", f"0 0 {hero['natural_width']} {hero['natural_height']}"),
        })

        # Secondary main items: placed near hero with slight overlap or side anchoring
        sec_positions = [
            (cw * 0.12, ch * 0.52, rng.uniform(-12, -4), base_scale * 0.95),
            (cw * 0.58, ch * 0.55, rng.uniform(4, 12), base_scale * 0.90),
            (cw * 0.50, ch * 0.12, rng.uniform(-8, 8), base_scale * 0.85),
        ]
        for idx, it in enumerate(main_items[1:]):
            pos = sec_positions[idx % len(sec_positions)]
            result.append({
                "name": it["name"],
                "is_background": False,
                "x": round(pos[0] + rng.uniform(-20, 20), 1),
                "y": round(pos[1] + rng.uniform(-20, 20), 1),
                "scale": round(pos[3], 4),
                "rotation": round(pos[2], 1),
                "natural_width": it["natural_width"],
                "natural_height": it["natural_height"],
                "viewBox": it.get("viewBox", f"0 0 {it['natural_width']} {it['natural_height']}"),
            })

        # Background items: float in opposite corners to frame the composition
        bg_anchors = [
            (cw * 0.08, ch * 0.10, rng.uniform(-15, -5), base_scale * 0.75),
            (cw * 0.68, ch * 0.15, rng.uniform(5, 18), base_scale * 0.78),
            (cw * 0.65, ch * 0.62, rng.uniform(-10, 10), base_scale * 0.72),
            (cw * 0.15, ch * 0.65, rng.uniform(10, 25), base_scale * 0.70),
        ]
        for idx, it in enumerate(bg_items):
            anc = bg_anchors[idx % len(bg_anchors)]
            result.append({
                "name": it["name"],
                "is_background": True,
                "x": round(anc[0] + rng.uniform(-15, 15), 1),
                "y": round(anc[1] + rng.uniform(-15, 15), 1),
                "scale": round(anc[3], 4),
                "rotation": round(anc[2], 1),
                "natural_width": it["natural_width"],
                "natural_height": it["natural_height"],
                "viewBox": it.get("viewBox", f"0 0 {it['natural_width']} {it['natural_height']}"),
            })

        return result

    def _layout_triangular(self, main_items, bg_items, cw, ch, base_scale, rng):
        result = []
        all_items = main_items + bg_items
        count = len(all_items)

        # Top apex and bottom-left, bottom-right base
        positions = [
            (cw * 0.28, ch * 0.12, rng.uniform(-4, 4), base_scale * 1.05),
            (cw * 0.10, ch * 0.48, rng.uniform(-12, -2), base_scale * 0.95),
            (cw * 0.52, ch * 0.45, rng.uniform(4, 14), base_scale * 0.95),
            (cw * 0.65, ch * 0.15, rng.uniform(8, 20), base_scale * 0.75),
            (cw * 0.35, ch * 0.65, rng.uniform(-8, 8), base_scale * 0.80),
        ]

        for idx, it in enumerate(all_items):
            pos = positions[idx % len(positions)]
            result.append({
                "name": it["name"],
                "is_background": it.get("is_background", False),
                "x": round(pos[0] + rng.uniform(-15, 15), 1),
                "y": round(pos[1] + rng.uniform(-15, 15), 1),
                "scale": round(pos[3], 4),
                "rotation": round(pos[2], 1),
                "natural_width": it["natural_width"],
                "natural_height": it["natural_height"],
                "viewBox": it.get("viewBox", f"0 0 {it['natural_width']} {it['natural_height']}"),
            })

        return result

    def _layout_diagonal(self, main_items, bg_items, cw, ch, base_scale, rng):
        result = []
        all_items = main_items + bg_items
        count = max(len(all_items), 1)

        # Diagonal from bottom-left to top-right
        for idx, it in enumerate(all_items):
            t = (idx + 0.5) / count
            x = cw * 0.12 + t * (cw * 0.55)
            y = ch * 0.65 - t * (ch * 0.50)
            is_bg = it.get("is_background", False)
            scale = base_scale * (0.85 if is_bg else 1.05)
            rot = rng.uniform(-12, 15)

            result.append({
                "name": it["name"],
                "is_background": is_bg,
                "x": round(x + rng.uniform(-20, 20), 1),
                "y": round(y + rng.uniform(-20, 20), 1),
                "scale": round(scale, 4),
                "rotation": round(rot, 1),
                "natural_width": it["natural_width"],
                "natural_height": it["natural_height"],
                "viewBox": it.get("viewBox", f"0 0 {it['natural_width']} {it['natural_height']}"),
            })

        return result

    def _layout_editorial(self, main_items, bg_items, cw, ch, base_scale, rng):
        result = []
        # Main cluster anchored on left (or right), leaving generous negative space
        all_items = main_items + bg_items

        cluster_x = cw * 0.12
        cluster_y = ch * 0.22

        for idx, it in enumerate(all_items):
            is_bg = it.get("is_background", False)
            offset_x = (idx % 2) * (cw * 0.22)
            offset_y = (idx // 2) * (ch * 0.28)
            scale = base_scale * (0.80 if is_bg else 1.1)

            result.append({
                "name": it["name"],
                "is_background": is_bg,
                "x": round(cluster_x + offset_x + rng.uniform(-15, 15), 1),
                "y": round(cluster_y + offset_y + rng.uniform(-15, 15), 1),
                "scale": round(scale, 4),
                "rotation": round(rng.uniform(-8, 10), 1),
                "natural_width": it["natural_width"],
                "natural_height": it["natural_height"],
                "viewBox": it.get("viewBox", f"0 0 {it['natural_width']} {it['natural_height']}"),
            })

        return result

    def _layout_still_life(self, main_items, bg_items, cw, ch, base_scale, rng):
        result = []
        # Organically clustered like items resting on a table
        all_items = main_items + bg_items

        cx = cw * 0.45
        cy = ch * 0.50

        for idx, it in enumerate(all_items):
            angle = (idx * (2 * math.pi / max(len(all_items), 1))) + rng.uniform(-0.3, 0.3)
            dist = rng.uniform(cw * 0.10, cw * 0.24) if idx > 0 else 0
            x = cx + math.cos(angle) * dist - (it["natural_width"] * base_scale * 0.5)
            y = cy + math.sin(angle) * dist - (it["natural_height"] * base_scale * 0.5)

            is_bg = it.get("is_background", False)
            scale = base_scale * (0.80 if is_bg else 1.05)

            result.append({
                "name": it["name"],
                "is_background": is_bg,
                "x": round(x, 1),
                "y": round(y, 1),
                "scale": round(scale, 4),
                "rotation": round(rng.uniform(-14, 14), 1),
                "natural_width": it["natural_width"],
                "natural_height": it["natural_height"],
                "viewBox": it.get("viewBox", f"0 0 {it['natural_width']} {it['natural_height']}"),
            })

        return result
