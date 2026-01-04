# Intel GPU Exporter

Python based metrics exporter for Prometheus.

The intel-gpu-tools package is used to extract GPU metrics.

# Usage:

Run container:

```
docker run -d \
  --device /dev/dri:/dev/dri \
  --privileged \
  --publish 9100:9100 \
  --restart always \
  --name intel-gpu-exporter \
  andrewgolikov55/intel-gpu-exporter
```

Or docker-compose:

```
version: '3.3'
services:
    intel-gpu-exporter:
        devices:
            - '/dev/dri:/dev/dri'
        privileged: true
        ports:
            - '9100:9100'
        restart: always
        container_name: intel-gpu-exporter
        image: andrewgolikov55/intel-gpu-exporter
```
/dev/dri is essential for GPU usage, and the container must operate with elevated privileges and as the root user to ensure adequate GPU access.

You can collect metrics after start container at the following address:

```
http://localhost:9100/metrics
```

Environment variables:

- `EXPORTER_PORT` (default: `9100`)
- `REFRESH_PERIOD_MS` (default: `5000`)
- `LOG_LEVEL` (default: `INFO`)

Or you can run script manually, just run:

```
python3 exporter.py
```

# Prometheus setup

You can use this configuration to collect metrics:

```
  - job_name: gpu_metrics
    honor_timestamps: true
    scrape_interval: 15s
    scrape_timeout: 10s
    scheme: http
    follow_redirects: true
    static_configs:
    - targets:
      - localhost:9100
```

# Building a container from sources

Building:

```
git clone https://github.com/AndrewGolikov55/intel-gpu-exporter.git
cd intel-gpu-exporter
docker build -t intel-gpu-exporter .
```
