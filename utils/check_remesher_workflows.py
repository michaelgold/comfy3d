import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


IGNORED_CLASS_TYPES = {
    # ComfyUI workflow/comment helper nodes may appear in exported files but are
    # not execution nodes that must be registered in /object_info.
    "Note",
}


def load_required_class_types(workflow_dir: Path) -> dict[str, set[str]]:
    by_file: dict[str, set[str]] = {}
    for path in sorted(workflow_dir.glob("*.json")):
        data = json.loads(path.read_text())
        classes = set()
        for node in data.values():
            if not isinstance(node, dict):
                continue
            class_type = node.get("class_type")
            if isinstance(class_type, str):
                classes.add(class_type)
        classes -= IGNORED_CLASS_TYPES
        by_file[path.name] = classes
    if not by_file:
        raise RuntimeError(f"No workflow JSON files found in {workflow_dir}")
    return by_file


def fetch_object_info(server_url: str, attempts: int = 30, delay: float = 2.0) -> dict:
    url = server_url.rstrip("/") + "/object_info"
    last_error: Exception | None = None
    for _ in range(attempts):
        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                return json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = exc
            time.sleep(delay)
    raise RuntimeError(f"Could not fetch {url}: {last_error}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify remesher example workflows reference nodes registered by a running ComfyUI server."
    )
    parser.add_argument("workflow_dir", type=Path)
    parser.add_argument("--server", default="http://127.0.0.1:8234")
    args = parser.parse_args()

    by_file = load_required_class_types(args.workflow_dir)
    object_info = fetch_object_info(args.server)
    registered = set(object_info.keys())

    missing_by_file = {
        name: sorted(classes - registered)
        for name, classes in by_file.items()
        if classes - registered
    }

    print("Remesher workflow node registration check")
    print(f"Server: {args.server}")
    print(f"Workflows checked: {len(by_file)}")
    print(f"Registered ComfyUI node classes: {len(registered)}")
    for name, classes in by_file.items():
        print(f"- {name}: {len(classes)} node classes")

    if missing_by_file:
        print("Missing required node classes:", file=sys.stderr)
        for name, missing in missing_by_file.items():
            print(f"- {name}: {', '.join(missing)}", file=sys.stderr)
        return 1

    print("PASS remesher workflows: all referenced node classes are registered")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
