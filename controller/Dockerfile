FROM python:3.8-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential ca-certificates libffi-dev && \
    rm -rf /var/lib/apt/lists/*

COPY ryu_app.py /app/ryu_app.py

RUN python -m pip install --upgrade "pip<25" "setuptools<58" wheel && \
    python -m pip install "eventlet==0.30.2" ryu

EXPOSE 6653 8080

CMD ["ryu-manager", "/app/ryu_app.py", "ryu.app.ofctl_rest"]
