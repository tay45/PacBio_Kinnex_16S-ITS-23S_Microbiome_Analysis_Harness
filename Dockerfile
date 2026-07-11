FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

COPY requirements.txt pyproject.toml README.md ./
COPY src ./src
COPY tests ./tests
COPY config ./config
COPY docs ./docs

RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -r requirements.txt \
    && python -m pip install --no-cache-dir -e .

# This image installs the Python harness and test/runtime Python dependencies.
# Production PacBio/Kinnex runs still require external bioinformatics tools such
# as skera, lima, bam2fasta, bam2fastq, pbmm2, samtools, mothur, and Emu. Those
# tools may need a separate production bioinformatics container or site-specific
# module environment; this Dockerfile does not pretend proprietary tools are
# automatically available.
CMD ["python", "-m", "pytest", "-q"]
