"""Unified command-line entry point."""

from __future__ import annotations

import argparse
import sys

from . import comparison_report, downstream_router, emu_runner, html_report, mothur_runner, pacbio_preprocess, validation_report
from .config import load_config


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="kinnex16s",
        description="PacBio Kinnex 16S-ITS-23S Microbiome Analysis Harness",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    preprocess = subparsers.add_parser("preprocess", parents=[pacbio_preprocess.build_arg_parser()], add_help=False)
    preprocess.set_defaults(func=pacbio_preprocess.run_pipeline)

    mothur = subparsers.add_parser("mothur", parents=[mothur_runner.build_arg_parser()], add_help=False)
    mothur.set_defaults(func=mothur_runner.run_pipeline)

    downstream = subparsers.add_parser(
        "downstream",
        parents=[downstream_router.build_arg_parser()],
        add_help=False,
    )
    downstream.set_defaults(func=lambda args: downstream_router.route_downstream(load_config(args.config)))

    emu = subparsers.add_parser("emu", parents=[emu_runner.build_arg_parser()], add_help=False)
    emu.set_defaults(func=lambda args: emu_runner.run_emu_from_config(load_config(args.config)))

    compare = subparsers.add_parser(
        "compare",
        parents=[comparison_report.build_arg_parser()],
        add_help=False,
    )
    compare.set_defaults(func=lambda args: comparison_report.run_comparison_from_config(load_config(args.config), force=True))

    validate = subparsers.add_parser(
        "validate",
        parents=[validation_report.build_arg_parser()],
        add_help=False,
    )
    validate.set_defaults(func=lambda args: validation_report.run_validation_from_config(load_config(args.config), force=True))

    report = subparsers.add_parser(
        "report",
        parents=[html_report.build_arg_parser()],
        add_help=False,
    )
    report.set_defaults(func=lambda args: html_report.generate_html_report(load_config(args.config), force=True))

    args = parser.parse_args()
    try:
        args.func(args)
    except Exception as exc:
        parser.exit(status=1, message=f"ERROR: {exc}\n")


if __name__ == "__main__":
    sys.exit(main())
