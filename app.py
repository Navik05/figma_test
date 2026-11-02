"""
Vector Illustration Assembly Web Service
Main application server powered by Tornado.
Implements REST API for library management, automated composition (Scenarios 1 & 2),
palette recoloring, and pristine vector SVG export.
"""

import json
import os
import sys
import tornado.ioloop
import tornado.web
from engine.library import ComponentLibrary
from engine.palette import PaletteManager
from engine.semantic import SemanticEngine
from engine.layout import LayoutEngine
from engine.exporter import SvgExporter


PORT = 8080


class BaseHandler(tornado.web.RequestHandler):
    """Base handler with CORS and JSON parsing support."""

    def set_default_headers(self):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "Content-Type, X-Requested-With")
        self.set_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")

    def options(self, *args, **kwargs):
        self.set_status(204)
        self.finish()

    def get_json_body(self) -> dict:
        try:
            if not self.request.body:
                return {}
            return json.loads(self.request.body.decode("utf-8"))
        except Exception as e:
            print(f"Error parsing JSON body: {e}")
            return {}

    def write_json(self, data: dict, status: int = 200):
        self.set_status(status)
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.write(json.dumps(data, ensure_ascii=False, indent=2))


class StatusHandler(BaseHandler):
    def get(self):
        self.write_json({
            "status": "ok",
            "service": "Vector Illustration Assembler",
            "version": "1.0.0",
            "supported_sizes": ["L", "S"],
            "active_size_default": "L",
        })


class LibraryHandler(BaseHandler):
    def initialize(self, library: ComponentLibrary):
        self.library = library

    def get(self):
        active_size = self.get_argument("size", "L")
        components = self.library.list_components(active_size=active_size)
        self.write_json({
            "size": active_size,
            "count": len(components),
            "components": components,
        })

    def post(self):
        """Upload a new SVG component to the library."""
        # Support multipart form-data or JSON payload
        name = self.get_argument("name", "")
        size = self.get_argument("size", "L")
        tags_str = self.get_argument("tags", "")
        tags = [t.strip() for t in tags_str.split(",") if t.strip()]

        main_svg = ""
        bg_svg = None

        if "main_file" in self.request.files:
            file_obj = self.request.files["main_file"][0]
            main_svg = file_obj["body"].decode("utf-8")
            if not name:
                name = os.path.splitext(file_obj["filename"])[0]

        if "bg_file" in self.request.files:
            bg_file_obj = self.request.files["bg_file"][0]
            bg_svg = bg_file_obj["body"].decode("utf-8")

        # Fallback to JSON body if not multipart
        if not main_svg:
            body = self.get_json_body()
            name = body.get("name", name)
            size = body.get("size", size)
            tags = body.get("tags", tags)
            main_svg = body.get("main_svg", "")
            bg_svg = body.get("bg_svg", None)

        if not name or not main_svg:
            self.write_json({"error": "Missing component name or SVG content"}, status=400)
            return

        saved = self.library.add_component(
            name=name, main_svg=main_svg, bg_svg=bg_svg, size=size, tags=tags
        )
        self.write_json({
            "success": True,
            "message": f"Компонент '{name}' успешно добавлен в библиотеку (размер {size}).",
            "component": saved,
        })


class ComponentSvgHandler(BaseHandler):
    def initialize(self, library: ComponentLibrary):
        self.library = library

    def get(self):
        name = self.get_argument("name", "")
        is_bg = self.get_argument("is_bg", "0") in ("1", "true", "True")
        size = self.get_argument("size", "L")
        palette_id = self.get_argument("palette", "palette_1")

        svg = self.library.get_component_svg(
            name=name, is_background=is_bg, size=size, palette_id=palette_id
        )
        if not svg:
            self.set_status(404)
            self.write("Component not found")
            return

        self.set_header("Content-Type", "image/svg+xml; charset=UTF-8")
        self.write(svg)


class PalettesHandler(BaseHandler):
    def initialize(self, palette_mgr: PaletteManager):
        self.palette_mgr = palette_mgr

    def get(self):
        palettes = self.palette_mgr.list_palettes()
        self.write_json({"palettes": palettes})

    def post(self):
        """Upload custom palette SVG or colors."""
        if "file" in self.request.files:
            file_obj = self.request.files["file"][0]
            svg_content = file_obj["body"].decode("utf-8")
            name = self.get_argument("name", os.path.splitext(file_obj["filename"])[0])
            pal = self.palette_mgr.add_palette_from_svg(svg_content, name=name)
            self.write_json({"success": True, "palette": pal})
            return

        body = self.get_json_body()
        name = body.get("name", "Пользовательская палитра")
        colors = body.get("colors", [])
        svg_content = body.get("svg_content", "")

        if svg_content:
            pal = self.palette_mgr.add_palette_from_svg(svg_content, name=name)
        elif colors:
            pal = self.palette_mgr.add_custom_palette(name=name, colors=colors)
        else:
            self.write_json({"error": "Missing palette colors or SVG file"}, status=400)
            return

        self.write_json({"success": True, "palette": pal})


class ComposeMetaphorHandler(BaseHandler):
    """Scenario 1: Automated composition from headline or metaphor."""

    def initialize(
        self,
        library: ComponentLibrary,
        semantic: SemanticEngine,
        layout: LayoutEngine,
        exporter: SvgExporter
    ):
        self.library = library
        self.semantic = semantic
        self.layout = layout
        self.exporter = exporter

    def post(self):
        body = self.get_json_body()
        prompt = body.get("prompt", "")
        cw = int(body.get("canvas_width", 1000))
        ch = int(body.get("canvas_height", 1000))
        size = body.get("size", "L")
        palette_id = body.get("palette_id", "palette_1")
        bg_type = body.get("background_type", "pattern")
        preset = body.get("preset", None)
        seed = body.get("seed", None)

        # 1. Semantic analysis
        analysis = self.semantic.analyze_prompt(prompt)
        hero = analysis["hero"]
        secondary = analysis["secondary"]
        background = analysis["background"]
        reasoning = analysis["reasoning"]
        chosen_preset = preset or analysis.get("layout_preset", "triangular")

        # 2. Gather item metadata
        items_to_layout = []
        hero_comp = self.library._cache.get(hero)
        if hero_comp:
            items_to_layout.append({
                "name": hero,
                "is_background": False,
                "natural_width": hero_comp["width"],
                "natural_height": hero_comp["height"],
                "viewBox": hero_comp["viewBox"],
            })

        for s_name in secondary:
            comp = self.library._cache.get(s_name)
            if comp:
                items_to_layout.append({
                    "name": s_name,
                    "is_background": False,
                    "natural_width": comp["width"],
                    "natural_height": comp["height"],
                    "viewBox": comp["viewBox"],
                })

        for b_name in background:
            comp = self.library._cache.get(b_name)
            if comp:
                items_to_layout.append({
                    "name": b_name,
                    "is_background": True,
                    "natural_width": comp["width"],
                    "natural_height": comp["height"],
                    "viewBox": comp["viewBox"],
                })

        # 3. Layout engine
        placed_items = self.layout.compose_scene(
            items=items_to_layout,
            canvas_width=cw,
            canvas_height=ch,
            preset=chosen_preset,
            seed=seed,
        )

        # 4. Generate vector SVG
        svg_content = self.exporter.build_composition_svg(
            canvas_width=cw,
            canvas_height=ch,
            items=placed_items,
            palette_id=palette_id,
            background_type=bg_type,
            size=size,
        )

        self.write_json({
            "scenario": "metaphor",
            "prompt": prompt,
            "reasoning": reasoning,
            "preset": chosen_preset,
            "hero": hero,
            "secondary": secondary,
            "background": background,
            "items": placed_items,
            "svg": svg_content,
        })


class ComposeComponentsHandler(BaseHandler):
    """Scenario 2: Automated composition from specific chosen component names."""

    def initialize(
        self,
        library: ComponentLibrary,
        layout: LayoutEngine,
        exporter: SvgExporter
    ):
        self.library = library
        self.layout = layout
        self.exporter = exporter

    def post(self):
        body = self.get_json_body()
        components = body.get("components", [])  # List of names or dicts
        cw = int(body.get("canvas_width", 1000))
        ch = int(body.get("canvas_height", 1000))
        size = body.get("size", "L")
        palette_id = body.get("palette_id", "palette_1")
        bg_type = body.get("background_type", "pattern")
        preset = body.get("preset", None)
        seed = body.get("seed", None)

        if not components:
            self.write_json({"error": "No components specified"}, status=400)
            return

        items_to_layout = []
        for idx, comp_entry in enumerate(components):
            if isinstance(comp_entry, str):
                name = comp_entry.strip()
                # Default: first 2 are main, subsequent are background
                is_bg = (idx >= 2)
            else:
                name = comp_entry.get("name", "").strip()
                is_bg = comp_entry.get("is_background", (idx >= 2))

            comp_meta = self.library._cache.get(name)
            if comp_meta:
                items_to_layout.append({
                    "name": name,
                    "is_background": is_bg,
                    "natural_width": comp_meta["width"],
                    "natural_height": comp_meta["height"],
                    "viewBox": comp_meta["viewBox"],
                })

        placed_items = self.layout.compose_scene(
            items=items_to_layout,
            canvas_width=cw,
            canvas_height=ch,
            preset=preset,
            seed=seed,
        )

        svg_content = self.exporter.build_composition_svg(
            canvas_width=cw,
            canvas_height=ch,
            items=placed_items,
            palette_id=palette_id,
            background_type=bg_type,
            size=size,
        )

        self.write_json({
            "scenario": "components",
            "items": placed_items,
            "svg": svg_content,
        })


class ExportSvgHandler(BaseHandler):
    """Exports full pristine vector SVG document."""

    def initialize(self, exporter: SvgExporter):
        self.exporter = exporter

    def post(self):
        body = self.get_json_body()
        cw = int(body.get("canvas_width", 1000))
        ch = int(body.get("canvas_height", 1000))
        items = body.get("items", [])
        palette_id = body.get("palette_id", "palette_1")
        bg_type = body.get("background_type", "pattern")
        size = body.get("size", "L")
        download = body.get("download", False)

        svg = self.exporter.build_composition_svg(
            canvas_width=cw,
            canvas_height=ch,
            items=items,
            palette_id=palette_id,
            background_type=bg_type,
            size=size,
        )

        if download or self.get_argument("download", "0") == "1":
            self.set_header("Content-Type", "image/svg+xml; charset=UTF-8")
            self.set_header("Content-Disposition", 'attachment; filename="illustration.svg"')
            self.write(svg)
        else:
            self.write_json({"svg": svg})


def make_app():
    palette_mgr = PaletteManager()
    library = ComponentLibrary(palette_manager=palette_mgr)
    semantic = SemanticEngine()
    layout = LayoutEngine()
    exporter = SvgExporter(library=library, palette_manager=palette_mgr)

    static_path = os.path.join(os.path.dirname(__file__), "static")

    return tornado.web.Application(
        [
            (r"/api/status", StatusHandler),
            (r"/api/library", LibraryHandler, dict(library=library)),
            (r"/api/component/svg", ComponentSvgHandler, dict(library=library)),
            (r"/api/palettes", PalettesHandler, dict(palette_mgr=palette_mgr)),
            (
                r"/api/compose/metaphor",
                ComposeMetaphorHandler,
                dict(library=library, semantic=semantic, layout=layout, exporter=exporter),
            ),
            (
                r"/api/compose/components",
                ComposeComponentsHandler,
                dict(library=library, layout=layout, exporter=exporter),
            ),
            (r"/api/export/svg", ExportSvgHandler, dict(exporter=exporter)),
            # Serve index.html at root
            (r"/", tornado.web.RedirectHandler, dict(url="/static/index.html")),
            (
                r"/static/(.*)",
                tornado.web.StaticFileHandler,
                dict(path=static_path, default_filename="index.html"),
            ),
        ],
        debug=True,
    )


if __name__ == "__main__":
    app = make_app()
    target_port = PORT
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        target_port = int(sys.argv[1])
    elif "PORT" in os.environ:
        try:
            target_port = int(os.environ["PORT"])
        except ValueError:
            pass

    bound_port = None
    for p in range(target_port, target_port + 20):
        try:
            app.listen(p)
            bound_port = p
            break
        except OSError as e:
            if e.errno == 98:  # Address already in use
                continue
            raise

    if bound_port is None:
        print(f"❌ Не удалось занять ни один порт в диапазоне {target_port}..{target_port+20}")
        sys.exit(1)

    print(f"🚀 Сервис запущен на http://localhost:{bound_port}")
    tornado.ioloop.IOLoop.current().start()
