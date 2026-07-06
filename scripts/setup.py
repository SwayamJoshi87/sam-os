#!/usr/bin/env python3
"""CLI helper for first-time sam-os setup."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(REPO_ROOT))

from samos.setup import (
    run_setup,
    seed_template,
    setup_check,
    verify_calendar_credentials,
    write_hermes_config,
)


def main():
    parser = argparse.ArgumentParser(description="Set up sam-os")
    sub = parser.add_subparsers(dest="command")

    check_cmd = sub.add_parser("check", help="Verify prerequisites")
    check_cmd.add_argument("--json", action="store_true", help="Output JSON")
    check_cmd.add_argument("--docker", action="store_true", help="Check Docker deployment prerequisites")

    hermes_cmd = sub.add_parser("hermes", help="Write Hermes mcp.json")
    hermes_cmd.add_argument("--output", help="Override output path")
    hermes_cmd.add_argument("--db-path", help="Override SQLite path (venv only)")
    hermes_cmd.add_argument("--tz", default="America/Toronto", help="Timezone")
    hermes_cmd.add_argument("--calendar-offline", action="store_true", help="Skip calendar")
    hermes_cmd.add_argument("--docker", action="store_true", help="Generate Docker-based Hermes config")

    seed_cmd = sub.add_parser("seed", help="Seed a starter weekly template")

    cal_cmd = sub.add_parser("calendar", help="Verify iCloud calendar credentials")

    setup_cmd = sub.add_parser("run", help="Run full setup")
    setup_cmd.add_argument("--no-hermes", action="store_true", help="Skip Hermes config")
    setup_cmd.add_argument("--no-seed", action="store_true", help="Skip template seed")
    setup_cmd.add_argument("--calendar-offline", action="store_true", help="Skip calendar")
    setup_cmd.add_argument("--docker", action="store_true", help="Use Docker deployment")

    args = parser.parse_args()

    if args.command == "check":
        result = setup_check(use_docker=args.docker)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Repo root: {result['repo_root']}")
            print(f"Deployment: {result['deployment']}")
            print(f"Docker available: {result['docker_available']}")
            print(f"Docker compose present: {result['docker_compose_present']}")
            print(f"Venv present: {result['venv_present']}")
            print(f"Deps importable: {result['deps_importable']}")
            print(f"DB path: {result['db_path']}")
            print(f"DB dir writable: {result['db_dir_writable']}")
            print(f"Hermes config present: {result['hermes_config_present']}")
            print(f"iCloud app password present: {result['icloud_app_password_present']}")
            print(f"Calendar offline: {result['calendar_offline']}")
            print(f"Template populated: {result['template_populated']}")
            print(f"Ready to run: {result['ready_to_run']}")
            for issue in result.get("issues", []):
                print(f"  ISSUE: {issue}")
        sys.exit(0 if result["ready_to_run"] else 1)

    if args.command == "hermes":
        result = write_hermes_config(
            output_path=args.output,
            db_path=args.db_path,
            tz=args.tz,
            calendar_offline=args.calendar_offline,
            use_docker=args.docker,
        )
        print(f"Wrote {result['deployment']} Hermes config to {result['written_to']}")
        sys.exit(0)

    if args.command == "seed":
        result = seed_template()
        if result["seeded"]:
            print(f"Seeded {result['tasks_added']} starter tasks")
        else:
            print(f"Skipped: {result.get('reason', result.get('error', 'unknown'))}")
        sys.exit(0)

    if args.command == "calendar":
        result = verify_calendar_credentials()
        print(json.dumps(result, indent=2))
        sys.exit(0 if result.get("valid") or result.get("offline") else 1)

    if args.command == "run":
        result = run_setup(
            write_hermes=not args.no_hermes,
            seed_template_flag=not args.no_seed,
            calendar_offline=args.calendar_offline,
            use_docker=args.docker,
        )
        print(json.dumps(result, indent=2))
        sys.exit(0)

    parser.print_help()
    sys.exit(1)


if __name__ == "__main__":
    main()
