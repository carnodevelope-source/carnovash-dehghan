ARG PYTHON_IMAGE=docker.arvancloud.ir/python:3.12-slim
FROM ${PYTHON_IMAGE}

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=120 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

RUN apt-get -o Acquire::Retries=5 -o Acquire::ForceIPv4=true update \
    && apt-get -o Acquire::Retries=5 -o Acquire::ForceIPv4=true install -y --no-install-recommends \
        libglib2.0-0 \
        libgomp1 \
        libxcb1 \
    && rm -rf /var/lib/apt/lists/*

COPY ai/final/requirements.txt /tmp/requirements.txt
COPY backend/packages /opt/packages
RUN if [ -d /opt/packages ] && [ "$(ls -A /opt/packages 2>/dev/null)" ]; then \
      pip install --no-index --find-links=/opt/packages -r /tmp/requirements.txt \
      && pip uninstall -y opencv-python \
      && pip install --no-index --find-links=/opt/packages --force-reinstall --no-deps opencv-python-headless; \
    else \
      pip install -r /tmp/requirements.txt; \
    fi

COPY ai/final/ /app/

EXPOSE 8765

CMD ["python", "plate_http_service.py", "--host", "0.0.0.0", "--port", "8765"]
