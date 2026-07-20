import json
import os
import sys
import urllib.error
import urllib.request


GITHUB_API = "https://api.github.com/repos/comfyanonymous/ComfyUI"


def github_json(path):
    token = os.getenv("GITHUB_TOKEN")
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "comfy3d-check-comfyui-latest",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(f"{GITHUB_API}/{path}", headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API request failed for {path}: HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"GitHub API request failed for {path}: {exc}") from exc


def get_latest_tag():
    tags = github_json("tags")
    if not isinstance(tags, list):
        raise RuntimeError(f"GitHub tags response was not a list: {tags!r}")
    return tags[0].get("name") if tags else None


def get_latest_commit():
    commit = github_json("commits/master")
    if not isinstance(commit, dict):
        raise RuntimeError(f"GitHub commit response was not an object: {commit!r}")
    return commit.get("sha")


def read_version_info(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r") as file:
            return json.load(file)
    return {"base_version": "", "update_version": "", "previous_commit": ""}


def write_version_info(file_path, base_version, update_version, commit):
    with open(file_path, "w") as file:
        json.dump({
            "base_version": base_version,
            "update_version": update_version,
            "previous_commit": commit,
        }, file)


def main():
    file_path = "utils/comfyui_version_info.json"
    version_info = read_version_info(file_path)

    latest_tag = get_latest_tag()
    latest_commit = get_latest_commit()

    # Check if we have a new tag (update_version changes)
    new_tag = latest_tag != version_info.get("update_version")
    new_commit = latest_commit != version_info.get("previous_commit")

    if new_tag or new_commit:
        # Keep the existing base_version unless it's empty
        base_version = version_info.get("base_version") or latest_tag
        write_version_info(file_path, base_version, latest_tag, latest_commit)

    # Write outputs to $GITHUB_OUTPUT
    github_output = os.getenv("GITHUB_OUTPUT")
    if github_output:
        # Resolve versions from GitHub data (tag preferred, then commit)
        git_version = latest_tag or latest_commit or ""
        base_version = version_info.get("base_version") or git_version
        update_version = git_version

        with open(github_output, "a") as output_file:
            output_file.write(f"new_tag={str(new_tag).lower()}\n")
            output_file.write(f"new_commit={str(new_commit).lower()}\n")
            output_file.write(f"latest_tag={latest_tag or ''}\n")
            output_file.write(f"latest_commit={latest_commit or ''}\n")
            output_file.write(f"base_version={base_version}\n")
            output_file.write(f"update_version={update_version}\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"check_comfyui_latest.py failed: {exc}", file=sys.stderr)
        raise
