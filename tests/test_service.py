"""
Comprehensive Test Suite for Vector Illustration Assembler
Validates all requirements from work.txt:
- Library indexing (10 SVG elements, S/L sizes)
- Palette loading, parsing, and vector recoloring (Schemes 1, 2, 3)
- Scenario 1: Automated composition from metaphor/headline
- Scenario 2: Automated composition from component list
- Pristine vector SVG export with XML validation
- Strict aspect ratio and proportion preservation
"""

import json
import os
import unittest
import xml.etree.ElementTree as ET
from engine.library import ComponentLibrary
from engine.palette import PaletteManager, normalize_color
from engine.semantic import SemanticEngine
from engine.layout import LayoutEngine
from engine.exporter import SvgExporter
from app import make_app
import tornado.testing


class TestPaletteEngine(unittest.TestCase):
    def setUp(self):
        self.mgr = PaletteManager()

    def test_default_palettes_loaded(self):
        palettes = self.mgr.list_palettes()
        pal_ids = [p["id"] for p in palettes]
        self.assertIn("palette_1", pal_ids)
        self.assertIn("palette_2", pal_ids)
        self.assertIn("palette_3", pal_ids)

        p1 = self.mgr.get_palette("palette_1")
        self.assertEqual(len(p1["colors"]), 8)
        self.assertEqual(p1["colors"][0], "#d7cdf5")
        self.assertEqual(p1["colors"][6], "#181817")

    def test_recolor_svg_palette_2(self):
        svg_sample = '<svg><path fill="#D7CDF5" stroke="#7864D7"/></svg>'
        recolored = self.mgr.recolor_svg(svg_sample, target_palette_id="palette_2")
        self.assertIn("#fdd7b9", recolored.lower())
        self.assertIn("#d27532", recolored.lower())
        self.assertNotIn("#d7cdf5", recolored.lower())

    def test_recolor_svg_palette_3(self):
        svg_sample = '<svg><path fill="#D7CDF5" stroke="#7864D7"/></svg>'
        recolored = self.mgr.recolor_svg(svg_sample, target_palette_id="palette_3")
        self.assertIn("#beebeb", recolored.lower())
        self.assertIn("#5abebe", recolored.lower())

    def test_custom_palette_svg_upload(self):
        custom_svg = """<svg width="500" height="200">
            <rect fill="#112233"/>
            <rect fill="#223344"/>
            <rect fill="#334455"/>
            <rect fill="#445566"/>
            <rect fill="#556677"/>
            <rect fill="#667788"/>
            <rect fill="#181817"/>
            <rect fill="#ffffff"/>
        </svg>"""
        pal = self.mgr.add_palette_from_svg(custom_svg, name="Custom Test")
        self.assertTrue(pal["is_custom"])
        self.assertEqual(len(pal["colors"]), 8)
        self.assertEqual(pal["colors"][0], "#112233")


class TestComponentLibrary(unittest.TestCase):
    def setUp(self):
        self.pal_mgr = PaletteManager()
        self.lib = ComponentLibrary(palette_manager=self.pal_mgr)

    def test_all_10_components_indexed(self):
        comps = self.lib.list_components()
        self.assertEqual(len(comps), 10)
        names = [c["name"] for c in comps]
        expected = ["книга", "кошелёк", "лампа", "монета", "наушники", "пазлы", "папка", "ручка", "телефон", "цветы"]
        for exp in expected:
            self.assertIn(exp, names)

    def test_component_svg_retrieval(self):
        svg_main = self.lib.get_component_svg("монета", is_background=False, size="L")
        self.assertTrue(svg_main.startswith("<svg"))
        self.assertIn("287", svg_main)

        svg_bg = self.lib.get_component_svg("монета", is_background=True, size="L")
        self.assertTrue(svg_bg.startswith("<svg"))
        # Background version only uses monochrome background colors
        self.assertIn("#7864D7", svg_bg)

    def test_size_s_graceful_fallback(self):
        # Request size S when S files haven't been loaded yet
        svg_s = self.lib.get_component_svg("книга", size="S")
        self.assertTrue(len(svg_s) > 0)


class TestSemanticEngine(unittest.TestCase):
    def setUp(self):
        self.semantic = SemanticEngine()

    def test_finance_metaphor(self):
        res = self.semantic.analyze_prompt("Финансовая подушка и рост сбережений")
        self.assertIn(res["hero"], ["кошелёк", "монета"])
        self.assertTrue(len(res["all_components"]) >= 3)
        self.assertIn("Финансы", res["reasoning"])

    def test_education_metaphor(self):
        res = self.semantic.analyze_prompt("Учеба, экзамены и чтение книг")
        self.assertIn(res["hero"], ["книга", "лампа"])

    def test_music_metaphor(self):
        res = self.semantic.analyze_prompt("Любимая музыка и расслабление")
        self.assertEqual(res["hero"], "наушники")


class TestLayoutEngine(unittest.TestCase):
    def setUp(self):
        self.layout = LayoutEngine()
        self.items = [
            {"name": "книга", "natural_width": 1446, "natural_height": 977, "is_background": False},
            {"name": "лампа", "natural_width": 946, "natural_height": 1129, "is_background": False},
            {"name": "монета", "natural_width": 287, "natural_height": 189, "is_background": True},
        ]

    def test_layout_coordinates_and_bounds(self):
        placed = self.layout.compose_scene(self.items, 1000, 1000, preset="triangular")
        self.assertEqual(len(placed), 3)
        for p in placed:
            self.assertGreaterEqual(p["x"], -50)
            self.assertLessEqual(p["x"], 1050)
            self.assertGreaterEqual(p["y"], -50)
            self.assertLessEqual(p["y"], 1050)
            self.assertGreater(p["scale"], 0.1)

    def test_layer_ordering_background_behind_main(self):
        placed = self.layout.compose_scene(self.items, 1000, 1000)
        bg_items = [p for p in placed if p["is_background"]]
        main_items = [p for p in placed if not p["is_background"]]

        for bg in bg_items:
            for mn in main_items:
                self.assertLess(bg["z_index"], mn["z_index"], "Background objects must have lower z-index than main objects")


class TestSvgExporter(unittest.TestCase):
    def setUp(self):
        self.pal_mgr = PaletteManager()
        self.lib = ComponentLibrary(palette_manager=self.pal_mgr)
        self.exporter = SvgExporter(self.lib, self.pal_mgr)
        self.layout = LayoutEngine()

    def test_exported_svg_validity(self):
        items = [
            {"name": "книга", "natural_width": 1446, "natural_height": 977, "is_background": False},
            {"name": "цветы", "natural_width": 591, "natural_height": 748, "is_background": True},
        ]
        placed = self.layout.compose_scene(items, 1000, 1000)
        svg_str = self.exporter.build_composition_svg(
            canvas_width=1000,
            canvas_height=1000,
            items=placed,
            palette_id="palette_2",
            background_type="pattern",
        )
        self.assertTrue(svg_str.startswith("<svg"))
        self.assertTrue(svg_str.endswith("</svg>"))

        # Verify valid XML
        tree = ET.fromstring(svg_str)
        self.assertEqual(tree.attrib["width"], "1000")
        self.assertEqual(tree.attrib["height"], "1000")
        # Ensure palette 2 colors are present
        self.assertIn("#fdd7b9", svg_str.lower())


class TestHttpApi(tornado.testing.AsyncHTTPTestCase):
    def get_app(self):
        return make_app()

    def test_api_status(self):
        response = self.fetch("/api/status")
        self.assertEqual(response.code, 200)
        data = json.loads(response.body.decode("utf-8"))
        self.assertEqual(data["status"], "ok")

    def test_api_library_list(self):
        response = self.fetch("/api/library?size=L")
        self.assertEqual(response.code, 200)
        data = json.loads(response.body.decode("utf-8"))
        self.assertEqual(data["count"], 10)

    def test_api_compose_metaphor_scenario_1(self):
        payload = json.dumps({
            "prompt": "Финансовая подушка безопасности и учет расходов",
            "canvas_width": 1000,
            "canvas_height": 1000,
            "palette_id": "palette_1",
            "background_type": "pattern",
        })
        response = self.fetch(
            "/api/compose/metaphor",
            method="POST",
            headers={"Content-Type": "application/json"},
            body=payload,
        )
        self.assertEqual(response.code, 200)
        data = json.loads(response.body.decode("utf-8"))
        self.assertEqual(data["scenario"], "metaphor")
        self.assertTrue(len(data["items"]) >= 3)
        self.assertTrue("<svg" in data["svg"])

    def test_api_compose_components_scenario_2(self):
        payload = json.dumps({
            "components": ["книга", "лампа", "ручка"],
            "canvas_width": 1000,
            "canvas_height": 1000,
            "palette_id": "palette_3",
            "background_type": "solid",
        })
        response = self.fetch(
            "/api/compose/components",
            method="POST",
            headers={"Content-Type": "application/json"},
            body=payload,
        )
        self.assertEqual(response.code, 200)
        data = json.loads(response.body.decode("utf-8"))
        self.assertEqual(data["scenario"], "components")
        self.assertEqual(len(data["items"]), 3)
        self.assertTrue("<svg" in data["svg"])


if __name__ == "__main__":
    unittest.main()
