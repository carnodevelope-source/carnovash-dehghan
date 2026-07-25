from pathlib import Path
from PIL import Image

def flood_clear_corners(img: Image.Image, tol=28):
    img = img.convert('RGBA')
    w, h = img.size
    px = img.load()
    corners = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]
    targets = []
    for x, y in corners:
        r, g, b, a = px[x, y]
        if r > 230 and g > 230 and b > 230:
            targets.append((r, g, b))
    if not targets:
        targets = [px[0, 0][:3]]

    def near(c1, c2):
        return abs(c1[0] - c2[0]) <= tol and abs(c1[1] - c2[1]) <= tol and abs(c1[2] - c2[2]) <= tol

    visited = set()
    stack = list(corners)
    while stack:
        x, y = stack.pop()
        if (x, y) in visited or x < 0 or y < 0 or x >= w or y >= h:
            continue
        visited.add((x, y))
        r, g, b, a = px[x, y]
        if a == 0:
            continue
        if not any(near((r, g, b), t) for t in targets):
            continue
        px[x, y] = (r, g, b, 0)
        stack.extend([(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)])
    return img


def save_webp(img, path, q=82, max_side=None):
    out = img
    if max_side:
        out = out.copy()
        out.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    out.save(path, 'WEBP', quality=q, method=6)


root = Path(r'D:\Desktop\PRG\Cursor\carno\carvash\frontend')
landing = root / 'src' / 'assets' / 'landing'
public = root / 'public'

jobs = [
    (public / 'logo' / 'blue.png', public / 'logo' / 'blue.webp', 82, 512),
    (public / 'logo' / 'green.png', public / 'logo' / 'green.webp', 82, 512),
    (landing / 'logo.png', landing / 'logo.webp', 82, 512),
    (landing / 'hero-3d.png', landing / 'hero-3d.webp', 78, 1400),
    (landing / 'mobile-app-platform.png', landing / 'mobile-app-platform.webp', 78, 1000),
    (landing / 'automatic-carwash-station.png', landing / 'automatic-carwash-station.webp', 78, 1000),
]

for src, dst, q, side in jobs:
    img = Image.open(src)
    cleaned = flood_clear_corners(img)
    save_webp(cleaned, dst, q=q, max_side=side)
    print(f'{src.name}: {src.stat().st_size} -> {dst.stat().st_size}')

blue = Image.open(public / 'logo' / 'blue.webp').convert('RGBA')
for name, size in [('favicon.png', 192), ('apple-touch-icon.png', 180)]:
    icon = blue.copy()
    icon.thumbnail((size, size), Image.Resampling.LANCZOS)
    canvas = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    ox = (size - icon.width) // 2
    oy = (size - icon.height) // 2
    canvas.paste(icon, (ox, oy), icon)
    canvas.save(public / name, 'PNG', optimize=True)
    print(name, (public / name).stat().st_size)

fav = blue.copy()
fav.thumbnail((64, 64), Image.Resampling.LANCZOS)
fav.save(public / 'favicon.webp', 'WEBP', quality=85, method=6)
print('done')
