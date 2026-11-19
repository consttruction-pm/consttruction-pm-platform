"""P0-M benchmark driver: runs each (size, workers) config in its own process.

Samples the summed RSS of the config process and all of its descendants from
the outside every 50 ms (the config itself must stay single-threaded, because
the pipeline deliberately refuses to fork from a process with live threads).
"""
from __future__ import annotations

import json
import subprocess
import sys
import time

import psutil

CONFIG = "/tmp/p0m_matrix.py"


def _sample_tree(pid: int) -> tuple[int, int]:
    try:
        root = psutil.Process(pid)
        total = root.memory_info().rss
        count = 0
        for child in root.children(recursive=True):
            try:
                total += child.memory_info().rss
                count += 1
            except psutil.Error:
                pass
        return total // 1024, count
    except psutil.Error:
        return 0, 0


def run_config(
    size: int, workers: int, repeats: int, mode: str, want_bytes: bool
) -> dict:
    command = [
        sys.executable,
        CONFIG,
        "--run",
        str(size),
        str(workers),
        str(repeats),
        mode,
    ]
    if want_bytes:
        command.append("--bytes")
    process = subprocess.Popen(command, stdout=subprocess.PIPE, text=True)
    peak_total = 0
    peak_children = 0
    peak_children_count = 0
    while process.poll() is None:
        total, count = _sample_tree(process.pid)
        peak_total = max(peak_total, total)
        if count:
            peak_children = max(peak_children, total - _sample_root(process.pid))
            peak_children_count = max(peak_children_count, count)
        time.sleep(0.05)
    stdout, _ = process.communicate()
    if process.returncode != 0:
        raise RuntimeError(f"config failed: {size}x{workers}/{mode}")
    payload = json.loads(stdout.strip().splitlines()[-1])
    payload["external_peak_tree_rss_kb"] = peak_total
    payload["external_peak_children_rss_kb"] = max(peak_children, 0)
    payload["external_peak_children_count"] = peak_children_count
    return payload


def _sample_root(pid: int) -> int:
    try:
        return psutil.Process(pid).memory_info().rss // 1024
    except psutil.Error:
        return 0


def main() -> None:
    sizes = [int(value) for value in sys.argv[1].split(",")]
    repeats = [int(value) for value in sys.argv[2].split(",")]
    out_path = sys.argv[3]
    modes = sys.argv[4].split(",") if len(sys.argv) > 4 else ["pipeline"]
    rows = []
    for size, repeat in zip(sizes, repeats):
        for mode in modes:
            for workers in (1, 2, 4):
                row = run_config(size, workers, repeat, mode, want_bytes=workers > 1)
                rows.append(row)
                print(
                    f"{size} x{workers} {mode}: median {row['wall_median_ms']} ms  "
                    f"p95 {row['wall_p95_ms']}  cpu {row['total_cpu_median_ms']}  "
                    f"util {row['utilization']}  "
                    f"ipc_submit {row['ipc_submit_median_ms']} ms  "
                    f"drain {row['drain_wait_median_ms']} ms  "
                    f"child_rss {row['external_peak_children_rss_kb']} kB  "
                    f"{row['sha256'][:12]}",
                    flush=True,
                )
                with open(out_path, "w") as handle:
                    json.dump(rows, handle, indent=1)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
