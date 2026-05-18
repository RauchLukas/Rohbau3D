from __future__ import annotations

import os
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import numpy as np
from PIL import Image

from rohbau3d.misc.config import load_config

ROHBAU3D_HEADER = """
    ____        __    __               _____ ____     __  __      __
   / __ \\____  / /_  / /_  ____ ___  _|__  // __ \\   / / / /_  __/ /_
  / /_/ / __ \\/ __ \\/ __ \\/ __ `/ / / //_ </ / / /  / /_/ / / / / __ \
 / _, _/ /_/ / / / / /_/ / /_/ / /_/ /__/ / /_/ /  / __  / /_/ / /_/ /
/_/ |_|\\____/_/ /_/_.___/\\__,_/\\__,_/____/_____/  /_/ /_/\\__,_/_.___/
>>> Rohbau3D Hub <<<
\n"""

ROHBAU3D_COLOR_MAP = {
    0: "#727274",
    1: "#FDA9A9",
    2: "#C78282",
    3: "#007AFF",
    4: "#3B9148",
    5: "#8686C0",
    6: "#89D6E4",
    7: "#911EB4",
    8: "#FF7300",
    9: "#2121E2",
    10: "#FF2D5A",
    11: "#93E09B",
    12: "#990000",
    13: "#FAA940",
    14: "#FF18E0",
    15: "#FFE119",
    16: "#B6CA00",
    17: "#00FF0D",
}

_CUBE_FACES = ("pos_x", "neg_x", "pos_y", "neg_y", "pos_z", "neg_z")
_PROGRESS_EVERY = 10


@dataclass
class SceneData:
    site_name: str
    scene_name: str
    scene_dir: Path
    coord: np.ndarray
    color: np.ndarray | None
    intensity: np.ndarray | None
    normal: np.ndarray | None
    class_id: np.ndarray | None
    instance_id: np.ndarray | None


@dataclass(frozen=True)
class RenderOptions:
    output_root: Path
    render_pano: bool
    render_cube: bool
    pano_width: int
    pano_height: int
    cube_size: int
    selected_features: tuple


def _format_duration(seconds: float) -> str:
    seconds = int(max(seconds, 0))

    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    if hours:
        return f"{hours}h {minutes}m {seconds}s"
    if minutes:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"


class _ProgressLogger:
    def __init__(self, *, total: int, log: logging.Logger) -> None:
        self.total = total
        self.log = log
        self.start_time = time.monotonic()

    def maybe_log(self, *, done: int, failed: int) -> None:
        if done <= 0:
            return

        if done % _PROGRESS_EVERY != 0:
            return

        self._log_progress(done=done, failed=failed)

    def finish(self, *, done: int, failed: int) -> None:
        elapsed = time.monotonic() - self.start_time
        rate = done / elapsed if elapsed > 0 else 0.0

        self.log.info(
            "Rendering finished: %d/%d scenes completed, %d failed, elapsed %s, average %.2f scenes/s.",
            done,
            self.total,
            failed,
            _format_duration(elapsed),
            rate,
        )

    def _log_progress(self, *, done: int, failed: int) -> None:
        elapsed = time.monotonic() - self.start_time
        rate = done / elapsed if elapsed > 0 else 0.0
        remaining = max(self.total - done, 0)
        eta = remaining / rate if rate > 0 else 0.0
        percent = 100.0 * done / self.total if self.total else 100.0

        self.log.info(
            "Progress: %d/%d scenes completed, %d failed, %.1f%%, %.2f scenes/s, elapsed %s, ETA %s.",
            done,
            self.total,
            failed,
            percent,
            rate,
            _format_duration(elapsed),
            _format_duration(eta),
        )


def _hex_to_rgb(hex_color: str) -> np.ndarray:
    h = hex_color.lstrip("#")
    return np.array([int(h[0:2], 16), int(h[2:4], 16),
                    int(h[4:6], 16)], dtype=np.uint8)


def _build_class_lut() -> Dict[int, np.ndarray]:
    return {k: _hex_to_rgb(v) for k, v in ROHBAU3D_COLOR_MAP.items()}


def _stable_instance_color(instance_id: int) -> np.ndarray:
    if instance_id == 0:
        return _hex_to_rgb(ROHBAU3D_COLOR_MAP[0])
    rng = np.random.default_rng(seed=int(instance_id))
    return rng.integers(32, 256, size=3, dtype=np.uint8)


def _to_uint8_rgb(color: np.ndarray) -> np.ndarray:
    if color.dtype == np.uint8:
        return color
    c = color.astype(np.float32)
    if c.max() <= 1.0:
        c = c * 255.0
    return np.clip(c, 0.0, 255.0).astype(np.uint8)


def _normalize_to_uint8(values: np.ndarray) -> np.ndarray:
    v = values.astype(np.float32).reshape(-1)
    if v.size == 0:
        return np.zeros((0,), dtype=np.uint8)
    vmin = float(np.nanmin(v))
    vmax = float(np.nanmax(v))
    if not np.isfinite(vmin) or not np.isfinite(
            vmax) or abs(vmax - vmin) < 1e-12:
        return np.zeros_like(v, dtype=np.uint8)
    out = (v - vmin) / (vmax - vmin)
    return np.clip(np.round(out * 255.0), 0.0, 255.0).astype(np.uint8)


def _colorize_class(class_ids: np.ndarray,
                    lut: Dict[int, np.ndarray]) -> np.ndarray:
    ids = class_ids.astype(np.int64).reshape(-1)
    out = np.zeros((ids.shape[0], 3), dtype=np.uint8)
    for cid in np.unique(ids):
        out[ids == cid] = lut.get(int(cid), np.array(
            [255, 255, 255], dtype=np.uint8))
    return out


def _colorize_instance(instance_ids: np.ndarray) -> np.ndarray:
    ids = instance_ids.astype(np.int64).reshape(-1)
    out = np.zeros((ids.shape[0], 3), dtype=np.uint8)
    for iid in np.unique(ids):
        out[ids == iid] = _stable_instance_color(int(iid))
    return out


def _discover_scenes(
        data_root: Path,
        site: str | None,
        scene: str | None) -> List[Path]:

    # automatically handle nested "rohbau3d" subdirectories
    while (data_root / "rohbau3d").is_dir():
        data_root = data_root / "rohbau3d"

    site_dirs = sorted(
        [p for p in data_root.iterdir() if p.is_dir() and p.name.startswith("site_")],
        key=lambda p: p.name,
    )

    if site is not None and "all" not in site:
        site_dirs = [p for p in site_dirs if p.name == site]

    scenes: List[Path] = []

    for site_dir in site_dirs:
        local_scenes = sorted(
            [p for p in site_dir.iterdir() if p.is_dir() and p.name.startswith("scene_")],
            key=lambda p: p.name,
        )

        if scene is not None and "all" not in scene:
            local_scenes = [p for p in local_scenes if p.name == scene]

        scenes.extend(local_scenes)

    return scenes


def _load_scene(scene_dir: Path) -> SceneData:
    def _load(name: str) -> np.ndarray | None:
        p = scene_dir / f"{name}.npy"
        return np.load(p) if p.exists() else None

    coord = _load("coord")
    if coord is None:
        raise FileNotFoundError(f"Missing coord.npy in {scene_dir}")

    site_name = scene_dir.parent.name

    return SceneData(
        site_name=site_name,
        scene_name=scene_dir.name,
        scene_dir=scene_dir,
        coord=coord.astype(np.float32),
        color=_load("color"),
        intensity=_load("intensity"),
        normal=_load("normal"),
        class_id=_load("class"),
        instance_id=_load("instance"),
    )


def _save_png(path: Path, image: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(image).save(path)


def _best_point_per_pixel(
        linear_pix: np.ndarray,
        depth: np.ndarray,
        num_pixels: int) -> np.ndarray:
    best_depth = np.full((num_pixels,), np.inf, dtype=np.float32)
    best_point = np.full((num_pixels,), -1, dtype=np.int64)

    order = np.argsort(depth)
    sorted_pix = linear_pix[order]
    _, first_pos = np.unique(sorted_pix, return_index=True)

    selected = order[first_pos]
    pix = linear_pix[selected]

    best_point[pix] = selected
    best_depth[pix] = depth[selected]

    return best_point


def _project_equirectangular(
    coord: np.ndarray,
    width: int,
    height: int,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    x = coord[:, 0]
    y = coord[:, 1]
    z = coord[:, 2]

    r = np.linalg.norm(coord, axis=1) + 1e-12
    yaw = np.arctan2(y, x)
    pitch = np.arcsin(np.clip(z / r, -1.0, 1.0))

    u = ((yaw + np.pi) / (2.0 * np.pi) * (width - 1)).astype(np.int32)
    v = ((np.pi / 2.0 - pitch) / np.pi * (height - 1)).astype(np.int32)

    u = np.clip(u, 0, width - 1)
    v = np.clip(v, 0, height - 1)

    return u, v, r.astype(np.float32)


def _project_cube(coord: np.ndarray,
                  size: int) -> Tuple[np.ndarray,
                                      np.ndarray,
                                      np.ndarray,
                                      np.ndarray]:
    x = coord[:, 0]
    y = coord[:, 1]
    z = coord[:, 2]

    ax = np.abs(x)
    ay = np.abs(y)
    az = np.abs(z)

    dominant = np.argmax(np.stack([ax, ay, az], axis=1), axis=1)

    face_idx = np.zeros((coord.shape[0],), dtype=np.int32)
    uc = np.zeros((coord.shape[0],), dtype=np.float32)
    vc = np.zeros((coord.shape[0],), dtype=np.float32)

    # z-up convention to match panorama pitch:
    # - vertical direction is z for side faces
    # - top/bottom faces are +z/-z

    mask = (dominant == 0) & (x >= 0)
    face_idx[mask] = 0
    uc[mask] = -y[mask] / (ax[mask] + 1e-12)
    vc[mask] = -z[mask] / (ax[mask] + 1e-12)

    mask = (dominant == 0) & (x < 0)
    face_idx[mask] = 1
    uc[mask] = y[mask] / (ax[mask] + 1e-12)
    vc[mask] = -z[mask] / (ax[mask] + 1e-12)

    mask = (dominant == 1) & (y >= 0)
    face_idx[mask] = 2
    uc[mask] = x[mask] / (ay[mask] + 1e-12)
    vc[mask] = -z[mask] / (ay[mask] + 1e-12)

    mask = (dominant == 1) & (y < 0)
    face_idx[mask] = 3
    uc[mask] = -x[mask] / (ay[mask] + 1e-12)
    vc[mask] = -z[mask] / (ay[mask] + 1e-12)

    mask = (dominant == 2) & (z >= 0)
    face_idx[mask] = 4
    uc[mask] = x[mask] / (az[mask] + 1e-12)
    vc[mask] = y[mask] / (az[mask] + 1e-12)

    mask = (dominant == 2) & (z < 0)
    face_idx[mask] = 5
    uc[mask] = x[mask] / (az[mask] + 1e-12)
    vc[mask] = -y[mask] / (az[mask] + 1e-12)

    u = ((uc + 1.0) * 0.5 * (size - 1)).astype(np.int32)
    v = ((vc + 1.0) * 0.5 * (size - 1)).astype(np.int32)

    u = np.clip(u, 0, size - 1)
    v = np.clip(v, 0, size - 1)

    depth = np.linalg.norm(coord, axis=1).astype(np.float32)

    return face_idx, u, v, depth


def _make_feature_arrays(scene: SceneData) -> Dict[str, np.ndarray]:
    features: Dict[str, np.ndarray] = {}
    n = scene.coord.shape[0]

    features["depth"] = scene.coord

    if scene.color is not None and scene.color.shape[0] == n:
        features["color"] = _to_uint8_rgb(scene.color[:, :3])

    if scene.intensity is not None and scene.intensity.shape[0] == n:
        g = _normalize_to_uint8(scene.intensity.reshape(-1))
        features["intensity"] = np.stack([g, g, g], axis=1)

    if scene.normal is not None and scene.normal.shape[0] == n:
        normal_rgb = np.clip(
            (scene.normal[:, :3].astype(np.float32) + 1.0) * 127.5,
            0.0,
            255.0,
        ).astype(np.uint8)
        features["normal"] = normal_rgb

    if scene.class_id is not None and scene.class_id.shape[0] == n:
        features["class"] = _colorize_class(
            scene.class_id.reshape(-1), _build_class_lut())

    if scene.instance_id is not None and scene.instance_id.shape[0] == n:
        features["instance"] = _colorize_instance(
            scene.instance_id.reshape(-1))

    return features


def _render_panorama(
    scene: SceneData,
    out_dir: Path,
    width: int,
    height: int,
    selected_features: Iterable[str],
) -> None:
    u, v, depth = _project_equirectangular(
        scene.coord, width=width, height=height)
    linear = v * width + u

    best = _best_point_per_pixel(linear, depth, width * height)
    point_pixel = np.stack([u, v], axis=1).astype(np.int32)

    pano_dir = out_dir / scene.site_name / scene.scene_name / "panorama"
    pano_dir.mkdir(parents=True, exist_ok=True)

    np.save(pano_dir / "point_to_pixel.npy", point_pixel)
    np.save(pano_dir / "pixel_to_point.npy", best.reshape(height, width))

    features = _make_feature_arrays(scene)

    for feat in selected_features:
        if feat not in features:
            continue

        if feat == "depth":
            depth_img = np.zeros((height, width), dtype=np.float32)
            valid = best >= 0
            depth_img.reshape(-1)[valid] = depth[best[valid]]

            d8 = _normalize_to_uint8(
                depth_img.reshape(-1)).reshape(height, width)
            _save_png(pano_dir / "depth.png", d8)
            continue

        img = np.zeros((height, width, 3), dtype=np.uint8)
        valid = best >= 0
        img.reshape(-1, 3)[valid] = features[feat][best[valid]]

        _save_png(pano_dir / f"{feat}.png", img)


def _render_cube_map(
    scene: SceneData,
    out_dir: Path,
    size: int,
    selected_features: Iterable[str],
) -> None:
    face_idx, u, v, depth = _project_cube(scene.coord, size=size)
    point_face_pixel = np.stack([face_idx, u, v], axis=1).astype(np.int32)

    cube_dir = out_dir / scene.site_name / scene.scene_name / "cube_map"
    cube_dir.mkdir(parents=True, exist_ok=True)

    np.save(cube_dir / "point_to_face_pixel.npy", point_face_pixel)

    features = _make_feature_arrays(scene)

    for face_i, face_name in enumerate(_CUBE_FACES):
        mask = face_idx == face_i

        linear = v[mask] * size + u[mask]
        local_depth = depth[mask]
        local_point_ids = np.where(mask)[0]

        best_local = _best_point_per_pixel(linear, local_depth, size * size)

        best_global = np.full((size * size,), -1, dtype=np.int64)
        valid = best_local >= 0
        best_global[valid] = local_point_ids[best_local[valid]]

        np.save(
            cube_dir /
            f"pixel_to_point_{face_name}.npy",
            best_global.reshape(
                size,
                size))

        for feat in selected_features:
            if feat not in features:
                continue

            if feat == "depth":
                depth_img = np.zeros((size, size), dtype=np.float32)
                valid = best_global >= 0
                depth_img.reshape(-1)[valid] = depth[best_global[valid]]

                d8 = _normalize_to_uint8(
                    depth_img.reshape(-1)).reshape(size, size)
                _save_png(cube_dir / f"depth_{face_name}.png", d8)
                continue

            img = np.zeros((size, size, 3), dtype=np.uint8)
            valid = best_global >= 0
            img.reshape(-1, 3)[valid] = features[feat][best_global[valid]]

            _save_png(cube_dir / f"{feat}_{face_name}.png", img)


def _render_one_scene(
        scene_dir: Path, options: RenderOptions) -> tuple[str, str]:
    """
    Must be a top-level function for ProcessPoolExecutor.
    Do not define this inside render_from_config().
    """
    scene_data = _load_scene(scene_dir)

    if options.render_pano:
        _render_panorama(
            scene=scene_data,
            out_dir=options.output_root,
            width=options.pano_width,
            height=options.pano_height,
            selected_features=list(options.selected_features),
        )

    if options.render_cube:
        _render_cube_map(
            scene=scene_data,
            out_dir=options.output_root,
            size=options.cube_size,
            selected_features=list(options.selected_features),
        )

    return scene_data.site_name, scene_data.scene_name


def _get_parallel_settings(cfg) -> tuple[str, int]:
    parallel_cfg = getattr(cfg.render, "parallel", None)

    if parallel_cfg is None:
        return "serial", 1

    backend = str(getattr(parallel_cfg, "backend", "process")).lower()
    workers_raw = getattr(parallel_cfg, "workers", 1)

    if workers_raw in (None, 0, "auto"):
        workers = os.cpu_count() or 1
    else:
        workers = int(workers_raw)

    if backend not in {"serial", "process", "thread"}:
        raise ValueError(
            "render.parallel.backend must be one of: "
            "'serial', 'process', 'thread'."
        )

    if workers < 1:
        raise ValueError("render.parallel.workers must be >= 1, 0, or 'auto'.")

    if backend == "serial":
        workers = 1

    return backend, workers


def render_from_config(config_path: str | Path) -> None:
    log = logging.getLogger(__name__)

    cfg = load_config(config_path)

    data_root = Path(cfg.data.root).expanduser().resolve()
    output_root = Path(cfg.output.root).expanduser().resolve()

    site = getattr(cfg.selection, "site", None)
    site = 'all' if site is None else site

    scene = getattr(cfg.selection, "scene", None)
    scene = 'all' if scene is None else scene

    render_pano = bool(cfg.render.panorama)
    render_cube = bool(cfg.render.cube_map)

    if not render_pano and not render_cube:
        raise ValueError(
            "Both render.panorama and render.cube_map are disabled.")

    selected_features = tuple(cfg.render.features)

    scenes = _discover_scenes(data_root, site=site, scene=scene)
    if not scenes:
        raise FileNotFoundError("No scenes found for the provided selection.")

    backend, workers = _get_parallel_settings(cfg)
    workers = min(workers, len(scenes))

    options = RenderOptions(
        output_root=output_root,
        render_pano=render_pano,
        render_cube=render_cube,
        pano_width=int(cfg.panorama.width),
        pano_height=int(cfg.panorama.height),
        cube_size=int(cfg.cube_map.size),
        selected_features=selected_features,
    )

    log.info("--- CONFIGURATION ------------------------------")
    log.info("  Input Directory:    %s", str(data_root))
    log.info("  Output Directory:   %s", str(options.output_root))
    log.info("  Site Selection:     %s", str(site))
    log.info("  Scene Selection:    %s", str(scene))
    log.info("  Feature Selection:  %s", str(options.selected_features))
    log.info("  Render Panorama:    %s", str(options.render_pano))
    log.info("  Render Cube Map:    %s", str(options.render_cube))
    if options.render_pano:
        log.info("    Panorama Width:   %s", options.pano_width)
        log.info("    Panorama Height:  %s", options.pano_height)
    if options.render_cube:
        log.info("    Cube Map Size:    %s", options.cube_size)
    log.info("------------------------------------------------")

    log.info(
        "Rendering %d scenes using backend=%s with workers=%d.",
        len(scenes),
        backend,
        workers,
    )

    progress = _ProgressLogger(total=len(scenes), log=log)

    done = 0
    failed = 0

    if workers == 1 or backend == "serial":
        for scene_dir in scenes:
            try:
                _render_one_scene(scene_dir, options)
            except Exception:
                failed += 1
                log.exception("Rendering failed for scene: %s", scene_dir)
                raise

            done += 1
            progress.maybe_log(done=done, failed=failed)

        progress.finish(done=done, failed=failed)
        return

    executor_cls = {
        "process": ProcessPoolExecutor,
        "thread": ThreadPoolExecutor,
    }[backend]

    with executor_cls(max_workers=workers) as executor:
        futures = {
            executor.submit(_render_one_scene, scene_dir, options): scene_dir
            for scene_dir in scenes
        }

        for future in as_completed(futures):
            scene_dir = futures[future]

            try:
                future.result()
            except Exception:
                failed += 1
                log.exception("Rendering failed for scene: %s", scene_dir)

                for pending_future in futures:
                    pending_future.cancel()

                raise

            done += 1
            progress.maybe_log(done=done, failed=failed)

    progress.finish(done=done, failed=failed)
