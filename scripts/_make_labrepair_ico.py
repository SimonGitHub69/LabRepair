from pathlib import Path

from PIL import Image, ImageDraw

out_dir = Path(r"D:\Progetti\LabRepair\scripts")
img_dir = Path(r"D:\Progetti\LabRepair\static\securtek\img")
out_ico = out_dir / "LabRepair.ico"
out_png = img_dir / "labrepair-app.png"


def make_icon(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    pad = max(1, size // 16)
    radius = max(2, size // 4)
    blue = (32, 107, 196, 255)
    draw.rounded_rectangle(
        [pad, pad, size - pad - 1, size - pad - 1],
        radius=radius,
        fill=blue,
    )

    s = size
    thick = max(2, s // 10)
    cx, cy = int(s * 0.62), int(s * 0.38)
    r = int(s * 0.16)
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(255, 255, 255, 255), width=thick)
    ri = max(1, r - thick)
    draw.ellipse([cx - ri, cy - ri, cx + ri, cy + ri], fill=blue)
    x0, y0 = int(s * 0.28), int(s * 0.72)
    x1, y1 = int(s * 0.58), int(s * 0.42)
    draw.line([(x0, y0), (x1, y1)], fill=(255, 255, 255, 255), width=thick)
    tip = max(2, s // 9)
    draw.rectangle(
        [x0 - tip // 2, y0 - tip // 2, x0 + tip // 2, y0 + tip // 2],
        fill=(255, 255, 255, 255),
    )
    return img


def main() -> None:
    sizes = [16, 24, 32, 48, 64, 128, 256]
    images = [make_icon(s) for s in sizes]
    # Pillow ICO: pass all sizes via save
    images[-1].save(
        out_ico,
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=images[:-1],
    )
    make_icon(256).save(out_png, format="PNG")
    print(f"Wrote {out_ico} ({out_ico.stat().st_size} bytes)")
    print(f"Wrote {out_png} ({out_png.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
