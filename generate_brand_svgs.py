#!/usr/bin/env python3
"""
Generate brand SVG files for Field Notes: East Anglia.
  - profile_picture.svg/png  (400x400)   — barley icon on dark green
  - facebook_cover.svg/png   (820x312)   — newsletter header layout
PNGs are rendered at 2× resolution for retina sharpness.
"""
import re
import os
import math
import subprocess

MAP_PATH = '/Users/neilpeacock/farm/field-notes/newsletter/assets/fn_map_east_anglia_banner.svg'


def read_map_inner():
    """Extract the inner SVG content (everything between the root <svg> tags)."""
    with open(MAP_PATH, 'r', encoding='utf-8') as f:
        content = f.read()
    # Strip the root <svg ...> opening and </svg> closing tags
    inner = re.sub(r'^\s*<\?xml[^?]*\?>\s*', '', content.strip())
    inner = re.sub(r'^\s*<svg[^>]*>', '', inner.strip())
    inner = re.sub(r'</svg>\s*$', '', inner.strip())
    return inner.strip()


def _barley_stalk(base_x, base_y, tip_x, tip_y, n_pairs=7):
    """
    Return SVG element strings for a single barley stalk.
    Stem goes from (base_x,base_y) to (tip_x,tip_y).
    Grain head occupies the top 52% of the stalk height.
    Spikelets tilt outward + slightly upward (classic barley ear shape).
    """
    GOLD, PALE = "#D4A843", "#E8CC7A"
    els = []

    dx, dy = tip_x - base_x, tip_y - base_y
    length = math.sqrt(dx*dx + dy*dy)
    ux, uy = dx/length, dy/length        # unit along stem (upward)
    px, py = -uy, ux                     # unit perpendicular (rightward)

    # Stem
    els.append(
        f'<line x1="{base_x}" y1="{base_y}" x2="{tip_x:.1f}" y2="{tip_y:.1f}" '
        f'stroke="{GOLD}" stroke-width="2.5" stroke-linecap="round" opacity="0.60"/>'
    )

    TILT = 0.38          # radians: how much spikelets sweep upward from horizontal
    HEAD_START = 0.48    # grain head begins at this fraction from base

    for i in range(n_pairs):
        t_head = i / (n_pairs - 1)                              # 0=lowest grain, 1=topmost
        t_stalk = HEAD_START + t_head * (1.0 - HEAD_START)

        cx = base_x + t_stalk * dx
        cy = base_y + t_stalk * dy

        sp = 17 - t_head * 7        # spikelet half-length: 17→10 top to bottom (reversed: longer at base)
        sp = 10 + (1 - t_head) * 7  # 17 at base, 10 at top

        # Spikelet direction: perpendicular + upward tilt
        rdx = px * math.cos(TILT) + ux * math.sin(TILT)
        rdy = py * math.cos(TILT) + uy * math.sin(TILT)
        ldx = -px * math.cos(TILT) + ux * math.sin(TILT)
        ldy = -py * math.cos(TILT) + uy * math.sin(TILT)

        for sdx, sdy in [(rdx, rdy), (ldx, ldy)]:
            scx = cx + sp * sdx
            scy = cy + sp * sdy
            ang = math.degrees(math.atan2(sdy, sdx))
            op = 0.68 - t_head * 0.18
            fill = GOLD if i % 2 == 0 else PALE
            els.append(
                f'<ellipse cx="{scx:.1f}" cy="{scy:.1f}" rx="{sp:.1f}" ry="3.8" '
                f'fill="{fill}" opacity="{op:.2f}" '
                f'transform="rotate({ang:.0f} {scx:.1f} {scy:.1f})"/>'
            )
            # awn (long barley whisker)
            awn = 22 - t_head * 8
            acx = cx + (sp * 2 + awn * 0.5) * sdx
            acy = cy + (sp * 2 + awn * 0.5) * sdy
            els.append(
                f'<ellipse cx="{acx:.1f}" cy="{acy:.1f}" rx="{awn/2:.1f}" ry="1.2" '
                f'fill="{GOLD}" opacity="{op*0.45:.2f}" '
                f'transform="rotate({ang:.0f} {acx:.1f} {acy:.1f})"/>'
            )

    # Terminal awn at very tip
    ang_tip = math.degrees(math.atan2(uy, ux))
    els.append(
        f'<ellipse cx="{tip_x:.1f}" cy="{tip_y - 8:.1f}" rx="1.8" ry="10" '
        f'fill="{GOLD}" opacity="0.45" transform="rotate({ang_tip:.0f} {tip_x:.1f} {tip_y - 8:.1f})"/>'
    )
    return '\n  '.join(els)


def generate_profile(path):
    """
    400×400 square — barley icon on dark green background.
    Three stalks: left (lean left, shorter), centre (straight, tallest),
    right (lean right, medium).
    """
    stalks = [
        # (base_x, base_y, tip_x, tip_y)
        (158, 322, 148, 108),   # left, leans slightly left
        (200, 322, 200, 76),    # centre, straight, tallest
        (242, 322, 252, 96),    # right, leans slightly right
    ]

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="400" viewBox="0 0 400 400">',
        '  <rect width="400" height="400" fill="#1b3a2d"/>',
        # Soft background glow
        '  <ellipse cx="200" cy="200" rx="160" ry="140" fill="#D4A843" opacity="0.04"/>',
        # Earth line
        '  <ellipse cx="200" cy="329" rx="92" ry="9" fill="#B8956A" opacity="0.28"/>',
        '  <ellipse cx="200" cy="333" rx="74" ry="5" fill="#A08060" opacity="0.18"/>',
    ]

    for bx, by, tx, ty in stalks:
        lines.append(f'  <!-- stalk {bx} -->')
        lines.append('  ' + _barley_stalk(bx, by, tx, ty))

    lines.append('</svg>')

    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    print(f'Written: {path}')


def generate_cover(map_inner, path):
    """
    820x312 — newsletter hero layout.

    Safe zones for Facebook Page:
      - Mobile crops ~90px each side → text x ≥ 100
      - Profile picture (circular, ~170px) sits CENTRED at the bottom of the cover,
        overlapping approx x=325-495, y=228-312 → no important text in that zone.

    Layout: full 312px hero (#1b3a2d).
      Left text panel: WEEKLY label / Field Notes / East Anglia / pill / tagline
      All text finishes above y=228 (safe above profile pic)
      Bottom strip y=288-312: decorative #263f32 with gold top border only (no text)
      Map: right portion, opacity 0.75
    """
    SAFE_BOTTOM = 224   # keep text baselines at or above this y
    STRIP_Y     = 284   # decorative strip start (no text here — profile pic centre zone)

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<svg xmlns="http://www.w3.org/2000/svg" width="820" height="312" viewBox="0 0 820 312">',

        # ── defs ──────────────────────────────────────────────────────────────
        '  <defs>',
        '    <linearGradient id="heroFade" x1="0" y1="0" x2="1" y2="0">',
        '      <stop offset="0%"   stop-color="#1b3a2d" stop-opacity="1"/>',
        '      <stop offset="40%"  stop-color="#1b3a2d" stop-opacity="1"/>',
        '      <stop offset="62%"  stop-color="#1b3a2d" stop-opacity="0"/>',
        '      <stop offset="100%" stop-color="#1b3a2d" stop-opacity="0"/>',
        '    </linearGradient>',
        '  </defs>',

        # ── full-height hero background ────────────────────────────────────────
        '  <rect width="820" height="312" fill="#1b3a2d"/>',

        # ── map (full height, aligned right) ──────────────────────────────────
        '  <g opacity="0.75">',
        '    <svg x="310" y="0" width="510" height="312"',
        '         viewBox="70 10 310 250" preserveAspectRatio="xMaxYMid meet">',
        map_inner,
        '    </svg>',
        '  </g>',

        # ── gradient overlay ───────────────────────────────────────────────────
        '  <rect width="820" height="312" fill="url(#heroFade)"/>',

        # ── left text panel ───────────────────────────────────────────────────
        # All text x ≥ 100 (mobile safe zone), all baselines ≤ y=224 (above profile pic)

        # "WEEKLY FARMING INTELLIGENCE"
        '  <text x="100" y="58"',
        '        font-family="Georgia, serif" font-size="10" font-weight="700"',
        '        fill="#d4a853" letter-spacing="3">WEEKLY FARMING INTELLIGENCE</text>',

        # "Field Notes"
        '  <text x="100" y="112"',
        '        font-family="Georgia, serif" font-size="54" font-weight="900"',
        '        fill="#ffffff">Field Notes</text>',

        # "East Anglia"
        '  <text x="100" y="149"',
        '        font-family="Georgia, serif" font-size="28" font-weight="700"',
        '        fill="#d4a853">East Anglia</text>',

        # frosted pill
        '  <rect x="100" y="164" width="268" height="30" rx="6"',
        '        fill="white" fill-opacity="0.12"/>',
        '  <text x="114" y="183"',
        '        font-family="Arial, sans-serif" font-size="12"',
        '        fill="#c8d6c0">Free \u00b7 Every Monday lunchtime</text>',

        # tagline — short enough to clear profile pic (circle starts ~x=325)
        # at ~7px/char, 30 chars ≈ 210px → fits within x=100–310
        '  <text x="100" y="218"',
        '        font-family="Georgia, serif" font-size="12" font-style="italic"',
        '        fill="#c8d6c0" opacity="0.80">Norfolk \u00b7 Suffolk \u00b7 Cambridgeshire</text>',

        # ── decorative bottom strip (no text — profile pic centre zone below here) ──
        f'  <rect x="0" y="{STRIP_Y}" width="820" height="{312 - STRIP_Y}" fill="#263f32"/>',
        f'  <line x1="0" y1="{STRIP_Y}" x2="820" y2="{STRIP_Y}" stroke="#d4a853" stroke-width="2"/>',

        '</svg>',
    ]
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    print(f'Written: {path}')


def svg_to_png(svg_path, png_path, w, h):
    """Render SVG to PNG at 2× resolution using rsvg-convert."""
    subprocess.run(
        ['rsvg-convert', '-w', str(w * 2), '-h', str(h * 2), svg_path, '-o', png_path],
        check=True,
    )
    print(f'Written: {png_path}')


def main():
    out_dir = os.path.dirname(os.path.abspath(__file__))
    map_inner = read_map_inner()
    print(f'Map SVG inner content: {len(map_inner)} chars')

    profile_svg = os.path.join(out_dir, 'profile_picture.svg')
    cover_svg   = os.path.join(out_dir, 'facebook_cover.svg')
    profile_png = os.path.join(out_dir, 'profile_picture.png')
    cover_png   = os.path.join(out_dir, 'facebook_cover.png')

    generate_profile(profile_svg)
    generate_cover(map_inner, cover_svg)

    svg_to_png(profile_svg, profile_png, 400, 400)    # outputs 800×800
    svg_to_png(cover_svg,   cover_png,   820, 312)    # outputs 1640×624

    print('Done.')


if __name__ == '__main__':
    main()


if __name__ == '__main__':
    main()
