"""Icon generation reports per-target failures without hiding later targets."""
import importlib.util
import io
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest
from PIL import Image


@pytest.mark.parametrize("bom", [b"", b"\xef\xbb\xbf"])
@pytest.mark.parametrize("editor_export", [False, True])
def test_svg_readers_accept_bom_without_rewriting_assets(tmp_path, monkeypatch, bom, editor_export):
    monkeypatch.setitem(sys.modules, "resvg_py", ModuleType("resvg_py"))
    script = Path(__file__).resolve().parents[2] / "scripts/generate_icons.py"
    spec = importlib.util.spec_from_file_location("icon_readers_under_test", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    path = tmp_path / "art.svg"
    element = '<path d="M0 0 L1 1" aria-label="café 東京"/>'
    declaration = '<?xml version="1.0" encoding="UTF-8"?>\n' if editor_export else ""
    namespaces = ' xmlns="http://www.w3.org/2000/svg" xmlns:editor="urn:editor"'
    metadata = '<editor:namedview editor:zoom="1"/>' if editor_export else ""
    document = f'<svg{namespaces} viewBox="0 0 20 30">{metadata}{element}</svg>'
    raw = bom + (declaration + document).encode("utf-8")
    path.write_bytes(raw)
    art = SimpleNamespace(backgrounds=tmp_path, colors=None)
    inner, width, height = module.background_inner(art, path.name)
    composed = ET.fromstring(f'<svg xmlns="http://www.w3.org/2000/svg">{inner}</svg>')
    assert (width, height) == (20, 30)
    assert [ET.tostring(child) for child in composed] == [
        ET.tostring(child) for child in ET.fromstring(document)
    ]
    assert path.read_bytes() == raw
    path.write_bytes(bom + b"<svg/>")
    with pytest.raises(AssertionError, match="viewBox"):
        module.background_inner(art, path.name)


@pytest.mark.parametrize("failure", [None, "render", "directory", "verify"])
def test_write_status_includes_every_target(tmp_path, monkeypatch, capsys, failure):
    # The renderer is build-only. This test injects failures at its byte boundary.
    monkeypatch.setitem(sys.modules, "resvg_py", ModuleType("resvg_py"))
    script = Path(__file__).resolve().parents[2] / "scripts" / "generate_icons.py"
    spec = importlib.util.spec_from_file_location("icon_generator_under_test", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    source = tmp_path / "immutable source"
    source.mkdir()
    monkeypatch.setattr(module, "IconArt", lambda root: root)
    monkeypatch.setattr(sys, "argv", [str(script), "--source", str(source), "--out", str(tmp_path)])

    image = io.BytesIO()
    Image.new("RGBA", (2, 2), (0, 0, 0, 0)).save(image, "PNG")
    good_bytes = image.getvalue()
    first = "blocked/icon.png" if failure == "directory" else "first.png"
    if failure == "directory":
        (tmp_path / "blocked").write_text("not a directory", encoding="utf-8")
    monkeypatch.setattr(module, "TARGETS", [(first, "png", "first"), ("last.png", "png", "last")])

    def target_bytes(art, kind, target):
        assert art == source
        assert not list(source.iterdir())
        if target == "first":
            if failure == "render":
                raise RuntimeError("injected render failure")
            if failure == "verify":
                return b"not an image"
        return good_bytes

    monkeypatch.setattr(module, "target_bytes", target_bytes)
    code = 0
    try:
        module.main()
    except SystemExit as stopped:
        code = stopped.code
    assert bool(code) is (failure is not None)
    assert (tmp_path / "last.png").read_bytes() == good_bytes
    output = capsys.readouterr().out
    assert "last.png: PNG (2, 2)" in output
    assert ("FAILED" in output) is (failure is not None)


@pytest.mark.parametrize("platform", ["", "mac-"])
@pytest.mark.parametrize("appearance,mark", [("light", "light"), ("dark", "dark")])
@pytest.mark.parametrize("colors", [None, ("#f5cc32", "#443808"), ("#e34850", "#4a1117")])
def test_icon_mark_sits_centered_on_the_plain_tile_inside_the_outer_silhouette(monkeypatch, platform, appearance, mark, colors):
    """The tile keeps the background's own geometry and fill with no stroke
    (the ring is disabled), and the hammer layer is centered in its box and
    clipped to that outline — fully inside the tile, never dragged past it."""
    monkeypatch.setitem(sys.modules, "resvg_py", ModuleType("resvg_py"))
    source = Path(__file__).resolve().parents[2]
    spec = importlib.util.spec_from_file_location("icon_geometry_under_test", source / "scripts/generate_icons.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.BORDER_ENABLED is False
    art = SimpleNamespace(
        backgrounds=source / "assets/backgrounds", colors=colors, commit="0123456",
        bboxes={mark: (0, 0, 100, 90)},
        _mark_uri="data:image/png;base64,AAAA", _mark_size=(100, 90),
    )
    name = f"squircle-{platform}{appearance}.svg"
    ns = {"svg": "http://www.w3.org/2000/svg"}
    original = ET.parse(art.backgrounds / name).find("svg:rect", ns)
    result = ET.fromstring(module.compose_svg(art, mark, name))
    tile = result.find("svg:rect", ns)
    assert original is not None and tile is not None
    geometry = tuple(float(original.attrib[key]) for key in ("x", "y", "width", "height", "rx"))
    assert tuple(float(tile.attrib[key]) for key in ("x", "y", "width", "height", "rx")) == geometry
    assert tile.get("stroke") is None and tile.get("stroke-width") is None
    expected_fill = (colors or ("#ffffff", module.DARK_HEX))[appearance == "dark"]
    assert tile.get("fill") == expected_fill
    clip = result.find("svg:defs/svg:clipPath/svg:rect", ns)
    assert clip is not None
    assert tuple(float(clip.attrib[key]) for key in ("x", "y", "width", "height", "rx")) == geometry
    group = result[-1]
    layer = group[-1]
    layers = [child for child in group if child.tag == f"{{{ns['svg']}}}image"]
    assert layers == [layer], "one mark layer, not a duplicate strip"
    # The commit badge rides inside the same clip, so its anti-aliased edge can
    # never add alpha outside the plate (visible at targetsize-16..30).
    assert [child.tag for child in group[:-1]] == [f"{{{ns['svg']}}}g"]
    assert layer.get("preserveAspectRatio") == "xMidYMid meet"
    assert layer.get("href") == art._mark_uri
    assert tuple(float(layer.attrib[key]) for key in ("x", "y", "width", "height")) == module.MARK_BOXES[name]
    clip_path = result.find("svg:defs/svg:clipPath", ns)
    assert clip_path is not None
    assert group.get("clip-path") == f"url(#{clip_path.attrib['id']})"
    assert layer.get("overflow") is None
    assert len(result.findall(".//svg:path", ns)) == 1  # the badge only; the mark is raster
    # The mark's bottom edge lands centered in the box, inside the tile.
    _x, y, _width, height, _ = geometry
    _, _by, bw, bh = art.bboxes[mark]
    box_y, box_h = module.MARK_BOXES[name][1], module.MARK_BOXES[name][3]
    scale = min(module.MARK_BOXES[name][2] / bw, box_h / bh)
    lowest_tile_y = box_y + (box_h + bh * scale) / 2  # xMidYMid: centered
    assert lowest_tile_y < y + height


def test_mark_layer_embeds_the_raster_hammer(tmp_path, monkeypatch):
    import base64

    monkeypatch.setitem(sys.modules, "resvg_py", ModuleType("resvg_py"))
    script = Path(__file__).resolve().parents[2] / "scripts/generate_icons.py"
    spec = importlib.util.spec_from_file_location("icon_markup_under_test", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    path = tmp_path / "thor-hammer.png"
    Image.new("RGBA", (40, 58), (242, 195, 77, 255)).save(path, "PNG")
    art = SimpleNamespace(mark_file=path, _mark_uri=None, _mark_size=None, bboxes={})
    layer = module.mark_layer(art, "dark", (10.0, 20.0, 300.0, 300.0))
    element = ET.fromstring(layer)
    assert element.tag == "image"
    href = element.get("href")
    assert href is not None and href.startswith("data:image/png;base64,")
    assert base64.b64decode(href.split(",", 1)[1]) == path.read_bytes()
    assert module.mark_bbox(art, "dark") == (0.0, 0.0, 40.0, 58.0)


def test_icon_art_builds_masters_from_the_committed_hammer_png():
    """The generator's hammer source is the PNG the repo actually ships; a
    stale source name crashes the Nix thor-icons build when the art is read."""
    source = Path(__file__).resolve().parents[2]
    spec = importlib.util.spec_from_file_location("icon_art_sources_under_test", source / "scripts/generate_icons.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    art = module.IconArt(source)
    assert art.mark_file.exists()
    assert art.marks["light"] == art.marks["dark"] == art.mark_file
    for master in (art.master, art.master_dark, art.master_mac, art.master_mac_dark):
        assert master.startswith("<svg") and "data:image/png;base64," in master
