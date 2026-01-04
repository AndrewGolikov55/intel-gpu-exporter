import logging
import json
import os
import signal
import subprocess
import sys

from prometheus_client import Gauge, start_http_server

METRIC_SPECS = (
    ("igpu_engines_blitter_0_busy", ("engines", "Blitter/0", "busy"), "Blitter 0 busy utilisation %"),
    ("igpu_engines_blitter_0_sema", ("engines", "Blitter/0", "sema"), "Blitter 0 sema utilisation %"),
    ("igpu_engines_blitter_0_wait", ("engines", "Blitter/0", "wait"), "Blitter 0 wait utilisation %"),
    ("igpu_engines_render_3d_0_busy", ("engines", "Render/3D/0", "busy"), "Render 3D 0 busy utilisation %"),
    ("igpu_engines_render_3d_0_sema", ("engines", "Render/3D/0", "sema"), "Render 3D 0 sema utilisation %"),
    ("igpu_engines_render_3d_0_wait", ("engines", "Render/3D/0", "wait"), "Render 3D 0 wait utilisation %"),
    ("igpu_engines_video_0_busy", ("engines", "Video/0", "busy"), "Video 0 busy utilisation %"),
    ("igpu_engines_video_0_sema", ("engines", "Video/0", "sema"), "Video 0 sema utilisation %"),
    ("igpu_engines_video_0_wait", ("engines", "Video/0", "wait"), "Video 0 wait utilisation %"),
    ("igpu_engines_video_enhance_0_busy", ("engines", "VideoEnhance/0", "busy"), "Video Enhance 0 busy utilisation %"),
    ("igpu_engines_video_enhance_0_sema", ("engines", "VideoEnhance/0", "sema"), "Video Enhance 0 sema utilisation %"),
    ("igpu_engines_video_enhance_0_wait", ("engines", "VideoEnhance/0", "wait"), "Video Enhance 0 wait utilisation %"),
    ("igpu_frequency_actual", ("frequency", "actual"), "Frequency actual MHz"),
    ("igpu_frequency_requested", ("frequency", "requested"), "Frequency requested MHz"),
    ("igpu_imc_bandwidth_reads", ("imc-bandwidth", "reads"), "IMC reads MiB/s"),
    ("igpu_imc_bandwidth_writes", ("imc-bandwidth", "writes"), "IMC writes MiB/s"),
    ("igpu_interrupts", ("interrupts", "count"), "Interrupts/s"),
    ("igpu_period", ("period", "duration"), "Period ms"),
    ("igpu_power_gpu", ("power", "GPU"), "GPU power W"),
    ("igpu_power_package", ("power", "Package"), "Package power W"),
    ("igpu_rc6", ("rc6", "value"), "RC6 %"),
)

GAUGES = {name: Gauge(name, help_text) for name, _, help_text in METRIC_SPECS}
_MISSING = object()


def get_nested(data, path, default=0.0):
    current = data
    for key in path:
        if not isinstance(current, dict):
            return default
        current = current.get(key, _MISSING)
        if current is _MISSING:
            return default
    return current


def update_metrics(data):
    for name, path, _ in METRIC_SPECS:
        GAUGES[name].set(get_nested(data, path, 0.0))


def read_int_env(name, default, min_value=None):
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        value = int(raw_value)
    except ValueError:
        logging.warning("Invalid %s=%r, using %s", name, raw_value, default)
        return default
    if min_value is not None and value < min_value:
        logging.warning("Invalid %s=%r, using %s", name, raw_value, default)
        return default
    return value


def configure_logging():
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=level)


def run_exporter():
    port = read_int_env("EXPORTER_PORT", 9100, min_value=1)
    period_ms = read_int_env("REFRESH_PERIOD_MS", 5000, min_value=250)

    def handle_signal(signum, frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    start_http_server(port)
    logging.info("Exporter listening on port %s", port)

    cmd = ["/usr/bin/intel_gpu_top", "-J", "-s", str(period_ms)]
    logging.info("Starting %s", " ".join(cmd))
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
    except FileNotFoundError:
        logging.error("intel_gpu_top not found at /usr/bin/intel_gpu_top")
        return 1

    output = ""
    try:
        if process.stdout is None:
            raise RuntimeError("stdout not captured")
        for line in process.stdout:
            output += line
            if line == "},\n":
                payload = output[:-2]
                output = ""
                try:
                    update_metrics(json.loads(payload))
                except json.JSONDecodeError as exc:
                    logging.warning("Failed to parse intel_gpu_top output: %s", exc)
    except KeyboardInterrupt:
        logging.info("Interrupted; shutting down")
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()

        stderr_output = ""
        if process.stderr is not None:
            stderr_output = process.stderr.read().strip()
        if process.returncode not in (0, None):
            if stderr_output:
                logging.error("intel_gpu_top exited with %s: %s", process.returncode, stderr_output)
            else:
                logging.error("intel_gpu_top exited with %s", process.returncode)

    logging.info("Finished")
    return 0


def main():
    configure_logging()
    return run_exporter()


if __name__ == "__main__":
    sys.exit(main())
