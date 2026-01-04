FROM ubuntu:24.04

ENV \
    DEBIAN_FRONTEND="noninteractive" \
    PIP_DISABLE_PIP_VERSION_CHECK="1" \
    PYTHONDONTWRITEBYTECODE="1" \
    PYTHONUNBUFFERED="1"

WORKDIR /app

RUN apt-get -qq update \
    && apt-get -qq install --no-install-recommends -y \
        intel-gpu-tools \
        python3 \
        python3-pip \
        tini \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN python3 -m pip install --no-cache-dir -r /app/requirements.txt --break-system-packages

COPY exporter.py /app/exporter.py

EXPOSE 9100

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python3", "/app/exporter.py"]

LABEL \
    org.opencontainers.image.title="intel-gpu-exporter" \
    org.opencontainers.image.authors="Andrew Golikov <andrewgolikov55@gmail.com>" \
    org.opencontainers.image.source="https://github.com/AndrewGolikov55/intel_gpu_exporter"
