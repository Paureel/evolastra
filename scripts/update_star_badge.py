from __future__ import annotations

import argparse
from pathlib import Path


def compact_count(count: int) -> str:
    if count < 1_000:
        return str(count)
    if count < 1_000_000:
        return f"{count / 1_000:.1f}k".replace(".0k", "k")
    return f"{count / 1_000_000:.1f}m".replace(".0m", "m")


def render_badge(count: int) -> str:
    value = compact_count(count)
    value_width = max(34, 16 + len(value) * 7)
    width = 68 + value_width
    split = 68
    label_center = split / 2
    value_center = split + value_width / 2
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="20" role="img" aria-label="stars: {value}">
  <title>GitHub stars: {count}</title>
  <linearGradient id="s" x2="0" y2="100%">
    <stop offset="0" stop-color="#fff" stop-opacity=".08"/>
    <stop offset="1" stop-opacity=".08"/>
  </linearGradient>
  <clipPath id="r"><rect width="{width}" height="20" rx="3"/></clipPath>
  <g clip-path="url(#r)">
    <rect width="{split}" height="20" fill="#071b26"/>
    <rect x="{split}" width="{value_width}" height="20" fill="#c99a32"/>
    <rect width="{width}" height="20" fill="url(#s)"/>
  </g>
  <g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="11">
    <text x="{label_center}" y="15" fill="#010101" fill-opacity=".3">★ stars</text>
    <text x="{label_center}" y="14">★ stars</text>
    <text x="{value_center}" y="15" fill="#010101" fill-opacity=".3">{value}</text>
    <text x="{value_center}" y="14">{value}</text>
  </g>
</svg>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Update the repository-local GitHub star badge.")
    parser.add_argument("count", type=int, help="Current GitHub stargazer count")
    parser.add_argument("--output", type=Path, default=Path("docs/badges/stars.svg"))
    args = parser.parse_args()
    if args.count < 0:
        parser.error("count must be non-negative")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_badge(args.count), encoding="utf-8")


if __name__ == "__main__":
    main()
