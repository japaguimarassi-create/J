import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path


def run_isolated_python(code, tests, timeout):
    docker = shutil.which("docker")
    if not docker:
        return {"status": "skipped", "reason": "Docker is required; candidate code is never executed on the host."}
    script = code.rstrip() + "\n\n" + tests.rstrip() + "\n"
    with tempfile.TemporaryDirectory(prefix="hypercode-candidate-") as directory:
        candidate = Path(directory) / "candidate.py"
        candidate.write_text(script, encoding="utf-8")
        command = [
            docker, "run", "--rm",
            "--network=none",
            "--read-only",
            "--tmpfs", "/tmp:rw,noexec,nosuid,size=16m",
            "--cap-drop=ALL",
            "--security-opt=no-new-privileges",
            "--pids-limit=32",
            "--memory=128m",
            "--cpus=0.5",
            "--user=65534:65534",
            "-v", f"{candidate}:/workspace/candidate.py:ro",
            "python:3.12-alpine",
            "python", "-I", "/workspace/candidate.py",
        ]
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return {"status": "timeout", "reason": f"Exceeded {timeout} seconds"}
        return {
            "status": "passed" if result.returncode == 0 else "failed",
            "returncode": result.returncode,
            "stdout": result.stdout[-2000:],
            "stderr": result.stderr[-2000:],
        }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--tasks", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("sandbox-results.jsonl"))
    parser.add_argument("--timeout", type=int, default=3)
    args = parser.parse_args()

    tasks = [json.loads(line) for line in args.tasks.read_text(encoding="utf-8").splitlines() if line.strip()]
    candidates = [json.loads(line) for line in args.candidates.read_text(encoding="utf-8").splitlines() if line.strip()]
    results = []
    for candidate_row in candidates:
        task = tasks[candidate_row["task_index"]]
        if task.get("language") != "python" or "tests" not in task:
            continue
        for candidate in candidate_row.get("candidates", []):
            if not candidate.get("syntax_ok"):
                result = {"status": "failed", "reason": "Static syntax check failed"}
            else:
                result = run_isolated_python(candidate["code"], task["tests"], args.timeout)
            results.append({
                "task_index": candidate_row["task_index"],
                "candidate": candidate["candidate"],
                **result,
            })
    args.output.write_text(
        "".join(json.dumps(result, ensure_ascii=False) + "\n" for result in results),
        encoding="utf-8",
    )
    print(json.dumps({
        "candidates_tested": len(results),
        "passed": sum(result["status"] == "passed" for result in results),
        "failed": sum(result["status"] == "failed" for result in results),
        "skipped": sum(result["status"] == "skipped" for result in results),
        "output": str(args.output),
    }, indent=2))


if __name__ == "__main__":
    main()
