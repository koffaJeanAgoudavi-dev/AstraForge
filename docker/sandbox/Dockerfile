FROM python:3.12-slim

RUN pip install --no-cache-dir pytest ruff

RUN useradd --create-home --uid 10001 astrasandbox
USER astrasandbox
WORKDIR /workspace

ENTRYPOINT ["/usr/local/bin/python"]
