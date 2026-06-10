# This file builds the sandbox image used to run student bots.
# Edit this file when bot languages or sandbox runtime packages change.
# Copy this file only when adding a separate sandbox image.
FROM python:3.14-slim-trixie

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && \
    apt-get install -y --no-install-recommends g++ coreutils && \
    rm -rf /var/lib/apt/lists/* && \
    groupadd --gid 10002 runner && \
    useradd --uid 10002 --gid 10002 --create-home --shell /usr/sbin/nologin runner

USER runner
WORKDIR /app

COPY runner/server.py /app/runner/server.py

EXPOSE 8090

CMD ["python", "/app/runner/server.py"]
