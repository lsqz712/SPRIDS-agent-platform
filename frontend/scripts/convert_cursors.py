"""Extract Windows .ani cursor frames and export PNG + hotspot metadata for web CSS."""

from __future__ import annotations

import io
import json
import struct
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
IMPORT_DIR = ROOT / "_cursor_import"
OUT_DIR = ROOT / "public" / "cursors" / "phrolova"

# Source ANI filename -> web asset basename
CURSOR_MAP = {
    "Normal.ani": "default",
    "Link.ani": "pointer",
    "Text.ani": "text",
    "Link.ani#grab": "grab",
    "Vertical.ani": "ns-resize",
    "Horizontal.ani": "ew-resize",
    "Diagonal1.ani": "nwse-resize",
    "Diagonal2.ani": "nesw-resize",
    "Unavailable.ani": "not-allowed",
    "Help.ani": "help",
    "Precision.ani": "crosshair",
    "Handwriting.ani": "pen",
    "Busy.ani": "wait",
    "Working.ani": "progress",
    "Alternate.ani": "alias",
    "Person.ani": "copy",
    "Pin.ani": "cell",
}


def extract_icons_from_ani(path: Path) -> list[bytes]:
    data = path.read_bytes()
    icons: list[bytes] = []

    if len(data) < 12 or data[:4] != b"RIFF" or data[8:12] != b"ACON":
        raise ValueError(f"Not a valid ANI file: {path}")

    pos = 12
    while pos + 8 <= len(data):
        chunk_id = data[pos : pos + 4]
        size = struct.unpack("<I", data[pos + 4 : pos + 8])[0]
        chunk = data[pos + 8 : pos + 8 + size]
        pos += 8 + size + (size & 1)

        if chunk_id == b"LIST":
            inner_pos = 4
            while inner_pos + 8 <= len(chunk):
                inner_id = chunk[inner_pos : inner_pos + 4]
                inner_size = struct.unpack("<I", chunk[inner_pos + 4 : inner_pos + 8])[0]
                inner_body = chunk[inner_pos + 8 : inner_pos + 8 + inner_size]
                inner_pos += 8 + inner_size + (inner_size & 1)
                if inner_id == b"icon":
                    icons.append(inner_body)
        elif chunk_id == b"icon":
            icons.append(chunk)

    return icons


def parse_cur(cur_data: bytes) -> tuple[Image.Image, int, int]:
    if len(cur_data) < 6:
        raise ValueError("CUR data too short")

    reserved, cursor_type, count = struct.unpack("<HHH", cur_data[:6])
    if cursor_type != 2 or count < 1:
        raise ValueError("Unsupported CUR format")

    entry_offset = 6
    width, height, _, _, x_hot, y_hot, size, image_offset = struct.unpack(
        "<BBBBHHII", cur_data[entry_offset : entry_offset + 16]
    )

    if width == 0:
        width = 256
    if height == 0:
        height = 256

    image_data = cur_data[image_offset : image_offset + size]
    dib = image_data

    # BITMAPINFOHEADER is 40 bytes; color table follows for <=8bpp
    header_size = struct.unpack("<I", dib[:4])[0]
    if header_size < 40:
        raise ValueError("Invalid DIB header")

    _, dib_height, planes, bit_count = struct.unpack("<iiHH", dib[4:16])
    abs_height = abs(dib_height)
    xor_height = abs_height // 2
    xor_mask_offset = header_size

    if bit_count <= 8:
        color_table_size = (1 << bit_count) * 4
        xor_mask_offset += color_table_size

    xor_size = ((width * bit_count + 31) // 32) * 4 * xor_height
    and_row_bytes = ((width + 31) // 32) * 4
    and_size = and_row_bytes * xor_height

    xor_bytes = dib[xor_mask_offset : xor_mask_offset + xor_size]
    and_bytes = dib[xor_mask_offset + xor_size : xor_mask_offset + xor_size + and_size]

    if bit_count == 32:
        img = Image.frombytes("RGBA", (width, xor_height), xor_bytes)
    elif bit_count == 24:
        rgb = Image.frombytes("RGB", (width, xor_height), xor_bytes)
        img = rgb.convert("RGBA")
    elif bit_count == 8:
        palette_data = dib[header_size : header_size + (1 << bit_count) * 4]
        palette = []
        for i in range(0, len(palette_data), 4):
            b, g, r, _ = palette_data[i : i + 4]
            palette.extend((r, g, b))
        indexed = Image.frombytes("P", (width, xor_height), xor_bytes)
        indexed.putpalette(palette)
        img = indexed.convert("RGBA")
    else:
        raise ValueError(f"Unsupported bit depth: {bit_count}")

    # Apply AND mask for transparency
    and_img = Image.frombytes("1", (width, xor_height), and_bytes)
    alpha = img.split()[3]
    mask = and_img.point(lambda p: 0 if p else 255)
    img.putalpha(Image.composite(mask, alpha, and_img))

    # Windows DIB stores rows bottom-up; flip so PNG matches on-screen orientation.
    img = img.transpose(Image.FLIP_TOP_BOTTOM)

    return img, x_hot, y_hot


def pick_best_frame(icons: list[bytes]) -> tuple[Image.Image, int, int]:
    best: tuple[Image.Image, int, int] | None = None
    best_area = -1

    for icon in icons:
        try:
            img, x_hot, y_hot = parse_cur(icon)
        except Exception:
            continue

        area = img.width * img.height
        if area > best_area:
            best = (img, x_hot, y_hot)
            best_area = area

    if best is None:
        raise ValueError("No valid CUR frames found")

    return best


def find_ani_files() -> dict[str, Path]:
    files: dict[str, Path] = {}
    for path in IMPORT_DIR.rglob("*.ani"):
        files[path.name] = path
    return files


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ani_files = find_ani_files()
    meta: dict[str, dict[str, int | str]] = {}

    for ani_name, basename in CURSOR_MAP.items():
        source_name = ani_name.split("#", 1)[0]
        path = ani_files.get(source_name)
        if path is None:
            raise FileNotFoundError(f"Missing {source_name} in {IMPORT_DIR}")

        icons = extract_icons_from_ani(path)
        if not icons:
            raise ValueError(f"No frames in {path}")

        img, x_hot, y_hot = pick_best_frame(icons)

        # Browsers work best with <=128px cursors
        max_size = 128
        if max(img.size) > max_size:
            scale = max_size / max(img.size)
            new_size = (max(1, int(img.width * scale)), max(1, int(img.height * scale)))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
            x_hot = max(0, min(new_size[0] - 1, int(x_hot * scale)))
            y_hot = max(0, min(new_size[1] - 1, int(y_hot * scale)))

        out_path = OUT_DIR / f"{basename}.png"
        img.save(out_path, format="PNG")
        meta[basename] = {"file": f"{basename}.png", "x": x_hot, "y": y_hot}
        print(f"Wrote {out_path.name} ({img.width}x{img.height}) hotspot {x_hot},{y_hot} frames={len(icons)}")

    (OUT_DIR / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"Done: {len(meta)} cursors -> {OUT_DIR}")


if __name__ == "__main__":
    main()
