from argparse import ArgumentParser, Namespace
from pathlib import Path

import winloop

from config import CONSTANTS
from DatexParser.datex_filter import FilterConfig
from DatexParser.overlay_export import export_overlay_data, run_overlay_export_loop

DEFAULT_ROADS = ["A-1", "AP-7", "AP-8"]


def _build_filter_config() -> FilterConfig:
    return FilterConfig(
        transient_ttl_days=1,
        roadworks_ttl_days=180,
        infrastructure_ttl_days=1095,
        low_severity_ttl_days=1,
        highest_road_closed_bonus=365,
        suspicious_threshold=0.75,
    )


def _parse_roads(raw_roads: str) -> list[str]:
    return [road.strip() for road in raw_roads.split(",") if road.strip()]


def parse_args() -> Namespace:
    parser = ArgumentParser(
        description="Export DATEX traffic alerts to overlay_data.json for OBS Browser Source."
    )
    parser.add_argument(
        "--roads",
        default=",".join(DEFAULT_ROADS),
        help="Comma-separated road whitelist. Use an empty string to disable filtering.",
    )
    parser.add_argument(
        "--output-file",
        default=str(CONSTANTS.COMMON.DATA_DIR / "overlay_data.json"),
        help="Output path for overlay JSON.",
    )
    parser.add_argument(
        "--interval-seconds",
        type=int,
        default=300,
        help="Refresh interval in seconds when running in loop mode.",
    )
    parser.add_argument(
        "--max-items",
        type=int,
        default=50,
        help="Maximum number of alerts to keep in overlay_data.json.",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run once and exit. Default behavior runs continuously.",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    roads = _parse_roads(args.roads) or None
    config = _build_filter_config()
    output_file = Path(args.output_file)

    if args.once:
        target = await export_overlay_data(
            output_file=output_file,
            roads=roads,
            max_items=args.max_items,
            filter_config=config,
        )
        print(f"Overlay data written to: {target}")
        return

    await run_overlay_export_loop(
        interval_seconds=args.interval_seconds,
        output_file=output_file,
        roads=roads,
        max_items=args.max_items,
        filter_config=config,
    )


if __name__ == "__main__":
    winloop.run(main())
