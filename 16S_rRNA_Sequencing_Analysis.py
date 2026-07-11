#!/usr/bin/env python3
"""Compatibility wrapper for the PacBio Kinnex preprocessing harness."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from kinnex16s.pacbio_preprocess import main


if __name__ == "__main__":
    main()
