# Agent-environment image (placeholder).
#
# PIN the base image by digest — a bare tag ("latest", "3.12-slim") is not
# reproducible and fails the build check. Resolve the real digest with:
#   docker pull python:3.12-slim
#   docker inspect --format '{{index .RepoDigests 0}}' python:3.12-slim
FROM python:3.12-slim@sha256:0000000000000000000000000000000000000000000000000000000000000000

WORKDIR /workspace

# The build context is this environment/ directory. Place the task's input
# files beside this Dockerfile (e.g. environment/data/) and stage ONLY them.
# Never COPY tests/ or solution/ into this image — the model must not be able
# to see either.
COPY data/ /workspace/data/

# Preinstall only what the task's START state requires. Discovering and
# installing analysis dependencies is legitimate work for the model.
RUN pip install --no-cache-dir pandas
