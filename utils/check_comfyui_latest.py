import requests
import json
import os

def get_latest_tag():
    response = requests.get('https://api.github.com/repos/comfyanonymous/ComfyUI/tags')
    tags = response.json()
    return tags[0]['name'] if tags else None

def get_latest_commit():
    response = requests.get('https://api.github.com/repos/comfyanonymous/ComfyUI/commits/master')
    commit = response.json()
    return commit['sha'] if commit else None

def read_version_info(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            return json.load(file)
    return {"base_version": "", "update_version": "", "previous_commit": ""}

def write_version_info(file_path, base_version, update_version, commit):
    with open(file_path, 'w') as file:
        json.dump({
            "base_version": base_version, 
            "update_version": update_version, 
            "previous_commit": commit
        }, file)

def main():
    file_path = 'utils/comfyui_version_info.json'
    version_info = read_version_info(file_path)

    latest_tag = get_latest_tag()
    latest_commit = get_latest_commit()

    # Check if we have a new tag (update_version changes)
    new_tag = latest_tag != version_info.get('update_version')
    new_commit = latest_commit != version_info.get('previous_commit')

    if new_tag or new_commit:
        # Keep the existing base_version unless it's empty
        base_version = version_info.get('base_version') or latest_tag
        write_version_info(file_path, base_version, latest_tag, latest_commit)

    # Write outputs to $GITHUB_OUTPUT
    github_output = os.getenv('GITHUB_OUTPUT')
    if github_output:
        # Ensure we always have valid versions
        base_version = version_info.get('base_version') or latest_tag or 'v0.3.50'
        # update_version should always be the latest detected, not stored
        update_version = latest_tag or 'v0.3.50'
        
        with open(github_output, 'a') as output_file:
            output_file.write(f"new_tag={str(new_tag).lower()}\n")
            output_file.write(f"new_commit={str(new_commit).lower()}\n")
            output_file.write(f"latest_tag={latest_tag or ''}\n")
            output_file.write(f"base_version={base_version}\n")
            output_file.write(f"update_version={update_version}\n")

if __name__ == "__main__":
    main()
