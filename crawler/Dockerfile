# Playwright's own base image bundles the browser binaries + OS deps that
# `playwright install --with-deps` would otherwise need at build time.
FROM mcr.microsoft.com/playwright/python:v1.47.0-jammy

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# No CMD here on purpose: this image runs either the scheduler
# (core/scheduler.py, continuous) or a one-off connector/audit script
# (tools/merchant_audit.py), and which one depends on the deployment -
# set the command explicitly in docker-compose.yml or your platform's job
# definition rather than hardcoding one here.
