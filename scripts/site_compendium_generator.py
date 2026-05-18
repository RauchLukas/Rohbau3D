#!/usr/bin/env python3
"""
Create one compendium PDF per site from a dataset tree like:

base_dir/
  site_00/
    scene_00000/
      panorama/
        color.png
        depth.png
        intensity.png
        normal.png
        class.png
        instance.png

For each site, one PDF is created with one page per scene.
Each page follows a dark layout inspired by the uploaded mockup.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple

from PIL import Image
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas


FEATURES: List[str] = [
    "color",
    "depth",
    "intensity",
    "normal",
    "class",
    "instance",
]

BG_COLOR = HexColor("#0D1117")
FG_COLOR = HexColor("#D9D9D9")
FONT_NAME = "Helvetica"
FONT_SIZE = 18

PAGE_SIZE = A4
PAGE_WIDTH, PAGE_HEIGHT = PAGE_SIZE

RIGHT_MARGIN = 9 * mm
LEFT_MARGIN = 16 * mm
TOP_MARGIN = 16 * mm
BOTTOM_MARGIN = 10 * mm
HEADER_GAP = 8 * mm
IMAGE_WIDTH = 15 * cm
LABEL_COLUMN_WIDTH = 18 * mm
LABEL_GAP = 3 * mm
ROW_GAP = 2.5 * mm
IMAGE_STROKE = 0.0


class SceneRecord:
    def __init__(self, site_name: str, scene_name: str, panorama_dir: Path):
        self.site_name = site_name
        self.scene_name = scene_name
        self.panorama_dir = panorama_dir

    def feature_path(self, feature: str) -> Path:
        return self.panorama_dir / f"{feature}.png"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create one compendium PDF per site from site/scene/panorama folders.")
    parser.add_argument(
        "base_dir",
        type=Path,
        help="Root directory that contains site folders.",
    )
    parser.add_argument(
        "export_dir",
        type=Path,
        help="Directory where the per-site PDF files will be written.",
    )
    parser.add_argument(
        "--site-pattern",
        default="site_*",
        help="Glob pattern used to find site folders. Default: site_*",
    )
    parser.add_argument(
        "--scene-pattern",
        default="scene*",
        help="Glob pattern used to find scene folders inside each site. Default: scene*",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing PDF files.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging.",
    )
    return parser.parse_args()


def setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="[%(levelname)s] %(message)s")


def sorted_dirs(paths: Iterable[Path]) -> List[Path]:
    return sorted((p for p in paths if p.is_dir()), key=lambda p: p.name)


def discover_sites(base_dir: Path, site_pattern: str) -> List[Path]:
    return sorted_dirs(base_dir.glob(site_pattern))


def discover_scenes(site_dir: Path, scene_pattern: str) -> List[SceneRecord]:
    scenes: List[SceneRecord] = []
    for scene_dir in sorted_dirs(site_dir.glob(scene_pattern)):
        panorama_dir = scene_dir / "panorama"
        if panorama_dir.is_dir():
            scenes.append(
                SceneRecord(
                    site_dir.name,
                    scene_dir.name,
                    panorama_dir))
        else:
            logging.warning(
                "Skipping %s because panorama/ is missing",
                scene_dir)
    return scenes


def fit_preserving_aspect(img_w: int, img_h: int,
                          max_w: float, max_h: float) -> Tuple[float, float]:
    if img_w <= 0 or img_h <= 0:
        return max_w, max_h
    scale = min(max_w / img_w, max_h / img_h)
    return img_w * scale, img_h * scale


def draw_background(pdf: canvas.Canvas) -> None:
    pdf.setFillColor(BG_COLOR)
    pdf.setStrokeColor(BG_COLOR)
    pdf.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=1, stroke=0)


def draw_header(pdf: canvas.Canvas, scene: SceneRecord) -> float:
    header_text = f"{scene.site_name} | {scene.scene_name}"
    pdf.setFillColor(FG_COLOR)
    pdf.setFont(FONT_NAME, FONT_SIZE)

    text_width = stringWidth(header_text, FONT_NAME, FONT_SIZE)
    x = PAGE_WIDTH - RIGHT_MARGIN - text_width
    y_top = PAGE_HEIGHT - TOP_MARGIN
    pdf.drawString(x, y_top - FONT_SIZE, header_text)
    return y_top - FONT_SIZE - HEADER_GAP


def draw_rotated_label(
    pdf: canvas.Canvas,
    label: str,
    center_x: float,
    center_y: float,
) -> None:
    pdf.saveState()
    pdf.translate(center_x, center_y)
    pdf.rotate(90)
    pdf.setFillColor(FG_COLOR)
    pdf.setFont(FONT_NAME, FONT_SIZE)
    label_width = stringWidth(label, FONT_NAME, FONT_SIZE)
    pdf.drawString(-label_width / 2.0, -FONT_SIZE / 3.0, label)
    pdf.restoreState()


def draw_placeholder(
        pdf: canvas.Canvas,
        x: float,
        y: float,
        w: float,
        h: float,
        message: str) -> None:
    pdf.saveState()
    pdf.setFillColor(BG_COLOR)
    pdf.setStrokeColor(FG_COLOR)
    pdf.setLineWidth(0.6)
    pdf.rect(x, y, w, h, fill=0, stroke=1)
    pdf.setFillColor(FG_COLOR)
    pdf.setFont(FONT_NAME, 11)
    text = f"Missing: {message}"
    tw = stringWidth(text, FONT_NAME, 11)
    pdf.drawString(x + max((w - tw) / 2.0, 4), y + h / 2.0 - 4, text)
    pdf.restoreState()


def draw_feature_image(
    pdf: canvas.Canvas,
    image_path: Path,
    x_right: float,
    y_top: float,
    max_w: float,
    row_h: float,
) -> Tuple[float, float, float, float]:
    x_left = x_right - max_w
    y_bottom = y_top - row_h

    if not image_path.is_file():
        draw_placeholder(pdf, x_left, y_bottom, max_w, row_h, image_path.name)
        return x_left, y_bottom, max_w, row_h

    try:
        with Image.open(image_path) as img:
            img_w, img_h = img.size
        draw_w, draw_h = fit_preserving_aspect(img_w, img_h, max_w, row_h)
        draw_x = x_right - draw_w
        draw_y = y_bottom + (row_h - draw_h) / 2.0
        pdf.drawImage(
            ImageReader(str(image_path)),
            draw_x,
            draw_y,
            width=draw_w,
            height=draw_h,
            preserveAspectRatio=True,
            mask="auto",
        )
        return draw_x, draw_y, draw_w, draw_h
    except Exception as exc:
        logging.warning("Could not draw %s: %s", image_path, exc)
        draw_placeholder(pdf, x_left, y_bottom, max_w, row_h, image_path.name)
        return x_left, y_bottom, max_w, row_h


def draw_scene_page(pdf: canvas.Canvas, scene: SceneRecord) -> None:
    draw_background(pdf)
    y_after_header = draw_header(pdf, scene)

    usable_height = y_after_header - BOTTOM_MARGIN
    total_gap = ROW_GAP * (len(FEATURES) - 1)
    row_h = (usable_height - total_gap) / len(FEATURES)

    image_right = PAGE_WIDTH - RIGHT_MARGIN
    label_center_x = image_right - IMAGE_WIDTH - \
        LABEL_GAP - (LABEL_COLUMN_WIDTH / 2.0)

    current_y_top = y_after_header
    for feature in FEATURES:
        image_path = scene.feature_path(feature)
        draw_x, draw_y, draw_w, draw_h = draw_feature_image(
            pdf=pdf,
            image_path=image_path,
            x_right=image_right,
            y_top=current_y_top,
            max_w=IMAGE_WIDTH,
            row_h=row_h,
        )

        center_y = current_y_top - (row_h / 2.0)
        draw_rotated_label(pdf, feature.capitalize(), label_center_x, center_y)

        current_y_top -= row_h + ROW_GAP

    pdf.showPage()


def create_site_pdf(
        site_dir: Path,
        scenes: Sequence[SceneRecord],
        export_dir: Path,
        overwrite: bool) -> Optional[Path]:
    if not scenes:
        logging.warning("No valid scenes found for %s", site_dir.name)
        return None

    export_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = export_dir / f"{site_dir.name}_compendium.pdf"

    if pdf_path.exists() and not overwrite:
        logging.info("Skipping existing PDF: %s", pdf_path)
        return pdf_path

    logging.info("Creating %s with %d pages", pdf_path, len(scenes))
    pdf = canvas.Canvas(str(pdf_path), pagesize=PAGE_SIZE)
    pdf.setTitle(f"{site_dir.name} Compendium")
    pdf.setAuthor("OpenAI ChatGPT")
    pdf.setSubject(f"Compendium for {site_dir.name}")

    for scene in scenes:
        draw_scene_page(pdf, scene)

    pdf.save()
    return pdf_path


def main() -> int:
    args = parse_args()
    setup_logging(args.verbose)

    base_dir = args.base_dir.expanduser().resolve()
    export_dir = args.export_dir.expanduser().resolve()

    if not base_dir.is_dir():
        logging.error(
            "Base directory does not exist or is not a directory: %s",
            base_dir)
        return 1

    site_dirs = discover_sites(base_dir, args.site_pattern)
    if not site_dirs:
        logging.error(
            "No site folders found in %s with pattern '%s'",
            base_dir,
            args.site_pattern)
        return 1

    created = 0
    for site_dir in site_dirs:
        scenes = discover_scenes(site_dir, args.scene_pattern)
        pdf_path = create_site_pdf(
            site_dir, scenes, export_dir, args.overwrite)
        if pdf_path is not None:
            created += 1

    logging.info("Done. Processed %d site(s).", created)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
