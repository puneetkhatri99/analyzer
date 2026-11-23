"""Command line for everything that isn't the API: python -m app.cli <command> --help"""

import argparse
import sys

from app.auth import commands as auth_commands
from app.core import migrations
from app.ingestion import bizdev, bizdev_enrich, bizdev_sync, classify_roles, daily_feed, push_data
from app.ingestion.collector import run as collector
from app.job_pages import check
from app.leads import crm_sync, daily_report
from app.report import data_check

COMMANDS = (
    migrations,
    auth_commands,
    bizdev,
    check,
    collector,
    push_data,
    daily_report,
    daily_feed,
    bizdev_sync,
    bizdev_enrich,
    classify_roles,
    data_check,
    crm_sync,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    commands = parser.add_subparsers(dest="command", required=True)
    for module in COMMANDS:
        module.register(commands)
    args = parser.parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    sys.exit(main())
