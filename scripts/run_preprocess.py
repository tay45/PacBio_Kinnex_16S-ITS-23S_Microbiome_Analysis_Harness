#!/usr/bin/env python3
"""Run the preprocessing command from a source checkout."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kinnex16s.pacbio_preprocess import main


if __name__ == "__main__":
    main()
