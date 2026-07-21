#!/usr/bin/env python3
import html
import re
import sys
import urllib.request
from datetime import datetime

BG = "#08080c"
LINE = "#22D3EE"
AREA_TOP = "#22D3EE"
POINT = "#FFFFFF"
ACCENT = "#A78BFA"
TEXT = "#C7C9D1"
GRID = "#1c1c26"

MONTHS = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def fetch_days(username):
    url = f"https://github.com/users/{username}/contributions"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        page = r.read().decode("utf-8", "replace")

    id_date = {}
    for cell in re.findall(r"<td[^>]*ContributionCalendar-day[^>]*>", page):
        cid = re.search(r'id="(contribution-day-component-[^"]+)"', cell)
        date = re.search(r'data-date="(\d{4}-\d{2}-\d{2})"', cell)
        if cid and date:
            id_date[cid.group(1)] = date.group(1)

    id_count = {}
    for tip in re.findall(r"<tool-tip[^>]*>.*?</tool-tip>", page, re.S):
        forid = re.search(r'for="(contribution-day-component-[^"]+)"', tip)
        if not forid:
            continue
        body = html.unescape(re.sub(r"<[^>]+>", "", tip)).strip()
        if body.lower().startswith("no contribution"):
            id_count[forid.group(1)] = 0
        else:
            m = re.match(r"([\d,]+)\s+contribution", body)
            id_count[forid.group(1)] = int(m.group(1).replace(",", "")) if m else 0

    days = [(d, id_count.get(cid, 0)) for cid, d in id_date.items()]
    days.sort(key=lambda x: x[0])
    return days


def esc(s):
    return html.escape(str(s), quote=True)


def build_svg(username, days_window):
    dates = [datetime.strptime(d, "%Y-%m-%d") for d, _ in days_window]
    counts = [c for _, c in days_window]

    W, H = 850, 300
    ml, mr, mt, mb = 46, 22, 54, 42
    pw, ph = W - ml - mr, H - mt - mb
    n = len(days_window)
    ymax = max(max(counts), 1)

    def px(i):
        return ml + (pw * i / (n - 1) if n > 1 else pw / 2)

    def py(v):
        return mt + ph - (ph * v / ymax)

    pts = [(px(i), py(counts[i])) for i in range(n)]

    yticks = sorted({0, (ymax + 1) // 2, ymax})
    grid, ylabels = [], []
    for t in yticks:
        y = py(t)
        grid.append(f'<line x1="{ml}" y1="{y:.1f}" x2="{ml+pw}" y2="{y:.1f}" '
                    f'stroke="{GRID}" stroke-width="1"/>')
        ylabels.append(f'<text x="{ml-10}" y="{y+4:.1f}" fill="{TEXT}" '
                       f'font-size="11" text-anchor="end">{t}</text>')

    step = max(1, n // 6)
    xlabels = []
    seen = set()
    for i in list(range(0, n, step)) + [n - 1]:
        if i in seen:
            continue
        seen.add(i)
        d = dates[i]
        label = f"{MONTHS[d.month]} {d.day}"
        xlabels.append(f'<text x="{px(i):.1f}" y="{mt+ph+22:.1f}" fill="{TEXT}" '
                       f'font-size="11" text-anchor="middle">{label}</text>')

    line_path = "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in pts)
    area_path = (f"M {pts[0][0]:.1f} {mt+ph:.1f} L "
                 + " L ".join(f"{x:.1f} {y:.1f}" for x, y in pts)
                 + f" L {pts[-1][0]:.1f} {mt+ph:.1f} Z")
    dots = "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.4" fill="{POINT}"/>'
                   for x, y in pts)

    total = sum(counts)
    rng = f"{MONTHS[dates[0].month]} {dates[0].day} – {MONTHS[dates[-1].month]} {dates[-1].day}"
    subtitle = f"{total} contributions · {rng}"

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Daily contribution graph for {esc(username)}">
  <defs>
    <linearGradient id="areaFill" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="{AREA_TOP}" stop-opacity="0.35"/>
      <stop offset="100%" stop-color="{AREA_TOP}" stop-opacity="0"/>
    </linearGradient>
  </defs>
  <rect width="{W}" height="{H}" rx="10" fill="{BG}"/>
  <text x="{ml}" y="28" fill="{ACCENT}" font-size="16" font-weight="700" font-family="Segoe UI, Helvetica, Arial, sans-serif">Contribution activity — @{esc(username)}</text>
  <text x="{ml}" y="44" fill="{TEXT}" font-size="11" font-family="Segoe UI, Helvetica, Arial, sans-serif">{esc(subtitle)}</text>
  <g font-family="Segoe UI, Helvetica, Arial, sans-serif">
    {"".join(grid)}
    <path d="{area_path}" fill="url(#areaFill)"/>
    <path d="{line_path}" fill="none" stroke="{LINE}" stroke-width="2.2" stroke-linejoin="round" stroke-linecap="round"/>
    {dots}
    {"".join(ylabels)}
    {"".join(xlabels)}
  </g>
</svg>
'''


def main():
    username = sys.argv[1] if len(sys.argv) > 1 else "modieoldie"
    days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    out = sys.argv[3] if len(sys.argv) > 3 else "assets/contribution-graph.svg"

    all_days = fetch_days(username)
    if not all_days:
        raise SystemExit(f"No contribution data found for '{username}'.")
    window = all_days[-days:]

    with open(out, "w", encoding="utf-8") as f:
        f.write(build_svg(username, window))
    print(f"Wrote {out}  ({len(window)} days, {sum(c for _, c in window)} contributions)")


if __name__ == "__main__":
    main()
