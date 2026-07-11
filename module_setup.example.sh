#!/usr/bin/env bash
set -euo pipefail

# Generic example only. Replace module names/versions with those available
# on your workstation, HPC cluster, or container image.
module purge
module load smrtlink
module load samtools
module load mothur

module list
