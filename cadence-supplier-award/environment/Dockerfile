# Agent environment for the FY2026 valve-seat sourcing award task.
#
# Base image pinned by digest (python:3.12-slim, manifest index resolved
# 2026-09-01). A floating tag fails the platform build check.
FROM python:3.12-slim@sha256:e5c9fa26ffb76e11e0f054f30dc2523a2f9693f0c36c0cf1e39b27e152d899fc

WORKDIR /workspace

# Starting state only. The input dataset is one of the shipped formats an
# analyst could not open without these two, so they are preinstalled; anything
# further the analysis wants is the attempt's own work to discover and install.
RUN pip install --no-cache-dir pandas==2.2.3 openpyxl==3.1.5

# Build context is this environment/ directory. Only the input data is staged;
# tests/ and solution/ are never part of this image.
COPY data/ /workspace/data/

RUN mkdir -p /workspace/output

CMD ["/bin/bash"]
