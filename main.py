"""CLI entrypoint for generating and publishing daily multilingual devotional Pinterest pins."""

from __future__ import annotations

import argparse
from datetime import date, timedelta
import json
import os
from pathlib import Path
import sys

from dotenv import load_dotenv

from src.artwork import generate_artwork
from src.panchang import format_date, get_lunar_tithi
from src.pinterest_client import list_boards, publish_pin
from src.poster import render_poster

ROOT_DIR = Path(__file__).resolve().parent
CONFIG_DIR = ROOT_DIR / "config"
OUTPUT_DIR = ROOT_DIR / "output"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_board_id(religion: str, lang: str, boards_map: dict) -> str:
    for key in (f"{religion}:{lang}", religion, lang, "default"):
        val = boards_map.get(key, "").strip()
        if val and not val.startswith("your_"):
            return val
    return os.getenv("PINTEREST_BOARD_ID", "").strip()


def run_for_date(
    target_date: date,
    religions: list[str],
    languages: list[str],
    traditions: dict,
    lang_configs: dict,
    boards_map: dict,
    publish: bool,
    brand_tag: str,
) -> list[Path]:
    weekday_idx = target_date.weekday()  # 0=Monday .. 6=Sunday
    generated_files: list[Path] = []
    date_folder = OUTPUT_DIR / target_date.isoformat()

    for religion in religions:
        tradition = traditions[religion]
        day_spec = tradition["weekdays"][weekday_idx]
        art_path = date_folder / f"_art_{religion}.png"

        art_path, used_ai = generate_artwork(
            prompt_subject=day_spec["prompt_subject"],
            target_date=target_date,
            religion=religion,
            accent_hex=day_spec["accent_color"],
            output_path=art_path,
        )
        source_label = "Gemini AI" if used_ai else "Fallback (no GEMINI_API_KEY)"
        print(f"[{target_date}] Artwork ({religion} - {day_spec['deity']}): {art_path.name} [{source_label}]")

        for lang in languages:
            lc = lang_configs[lang]
            weekday_label = lc["weekdays"][weekday_idx]
            date_label = format_date(target_date, lc.get("digits", "0123456789"))
            tithi_label = get_lunar_tithi(target_date, lang) if religion == "hindu" else None

            raw_greeting = lc["greetings"].get(religion, "")
            greeting_main = raw_greeting[weekday_idx] if isinstance(raw_greeting, list) else raw_greeting

            poster_path = date_folder / f"{target_date.isoformat()}_{religion}_{lang}.png"
            render_poster(
                background_image=art_path,
                output_path=poster_path,
                weekday_label=weekday_label,
                date_label=date_label,
                tithi_label=tithi_label,
                greeting_main=greeting_main,
                good_morning=lc["good_morning"],
                font_family=lc["font_family"],
                text_dir=lc.get("dir", "ltr"),
                accent_color=day_spec["accent_color"],
                brand_tag=brand_tag,
            )
            generated_files.append(poster_path)
            print(f"  -> Poster ({lang}): {poster_path.name}")

            if publish:
                board_id = resolve_board_id(religion, lang, boards_map)
                title = f"{weekday_label} | {day_spec['deity']} | {date_label}"
                hashtags = " ".join(day_spec.get("hashtags", []))
                description = f"{greeting_main}\n{lc['good_morning']}\n{date_label}\n\n{hashtags}".strip()
                res = publish_pin(
                    image_path=poster_path,
                    board_id=board_id,
                    title=title,
                    description=description,
                    alt_text=f"{day_spec['deity']} devotional blessing for {weekday_label} {date_label}",
                )
                print(f"  -> Published Pin ID: {res.get('id')} to board {board_id}")

    return generated_files


def main() -> int:
    load_dotenv(ROOT_DIR / ".env")
    traditions = load_json(CONFIG_DIR / "traditions.json")
    lang_configs = load_json(CONFIG_DIR / "languages.json")
    boards_file = CONFIG_DIR / "boards.json"
    boards_map = load_json(boards_file) if boards_file.exists() else {}

    parser = argparse.ArgumentParser(description="Daily Multilingual Devotional Pinterest Generator & Publisher")
    parser.add_argument("--date", help="Target date YYYY-MM-DD (default: today)")
    parser.add_argument("--week", action="store_true", help="Generate all 7 days starting from --date")
    parser.add_argument(
        "--religions",
        default=os.getenv("DEFAULT_RELIGIONS", "hindu"),
        help=f"Comma-separated religions or 'all' ({', '.join(traditions.keys())})",
    )
    parser.add_argument(
        "--languages",
        default=os.getenv("DEFAULT_LANGUAGES", "gu,hi,en"),
        help=f"Comma-separated language codes or 'all' ({', '.join(lang_configs.keys())})",
    )
    parser.add_argument("--publish", action="store_true", help="Publish generated posters to Pinterest API v5")
    parser.add_argument("--list-boards", action="store_true", help="List Pinterest boards and exit")
    parser.add_argument("--brand", default="", help="Optional small watermark/handle at bottom")
    args = parser.parse_args()

    if args.list_boards:
        boards = list_boards()
        for b in boards:
            print(f"{b.get('id')}  |  {b.get('name')}")
        return 0

    religions = list(traditions.keys()) if args.religions.strip().lower() == "all" else [
        r.strip().lower() for r in args.religions.split(",") if r.strip()
    ]
    languages = list(lang_configs.keys()) if args.languages.strip().lower() == "all" else [
        l.strip().lower() for l in args.languages.split(",") if l.strip()
    ]

    for r in religions:
        if r not in traditions:
            print(f"Unknown religion '{r}'. Valid: {', '.join(traditions.keys())}", file=sys.stderr)
            return 1
    for l in languages:
        if l not in lang_configs:
            print(f"Unknown language '{l}'. Valid: {', '.join(lang_configs.keys())}", file=sys.stderr)
            return 1

    start_date = date.fromisoformat(args.date) if args.date else date.today()
    dates = [start_date + timedelta(days=i) for i in range(7)] if args.week else [start_date]

    for d in dates:
        run_for_date(
            target_date=d,
            religions=religions,
            languages=languages,
            traditions=traditions,
            lang_configs=lang_configs,
            boards_map=boards_map,
            publish=args.publish,
            brand_tag=args.brand,
        )

    print(f"\nDone! Output saved in: {OUTPUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
