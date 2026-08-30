from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
ARM64_WORKFLOW = WORKFLOWS / "deploy-arm64.yml"
PR_VALIDATION_WORKFLOW = WORKFLOWS / "validate-pull-request.yml"


def _runner_labels(runs_on):
    return [runs_on] if isinstance(runs_on, str) else list(runs_on)


def _on_section(workflow):
    if "on" in workflow:
        return workflow["on"]
    return workflow.get(True, {})


def test_on_section_supports_yaml_1_1_and_yaml_1_2_keys():
    triggers = {"push": {"branches": ["main"]}}
    assert _on_section({True: triggers}) is triggers
    assert _on_section({"on": triggers}) is triggers


def test_existing_self_hosted_workflows_are_explicitly_x64():
    for path in [*WORKFLOWS.glob("*.yml"), *WORKFLOWS.glob("*.yaml")]:
        if path == ARM64_WORKFLOW:
            continue
        workflow = yaml.safe_load(path.read_text())
        for job_name, job in workflow.get("jobs", {}).items():
            labels = _runner_labels(job["runs-on"])
            if "self-hosted" in labels:
                assert {"Linux", "X64"}.issubset(labels), (path, job_name, labels)


def test_pull_requests_never_run_on_self_hosted_runners():
    for path in [*WORKFLOWS.glob("*.yml"), *WORKFLOWS.glob("*.yaml")]:
        workflow = yaml.safe_load(path.read_text())
        if "pull_request" not in _on_section(workflow):
            continue
        for job_name, job in workflow.get("jobs", {}).items():
            labels = _runner_labels(job["runs-on"])
            assert "self-hosted" not in labels, (path, job_name, labels)

    validation = yaml.safe_load(PR_VALIDATION_WORKFLOW.read_text())
    validation_triggers = _on_section(validation)
    assert "pull_request" in validation_triggers
    validation_paths = validation_triggers["pull_request"]["paths"]
    assert ".github/workflows/*.yml" in validation_paths
    assert ".github/workflows/*.yaml" in validation_paths
    assert validation["jobs"]["validate"]["runs-on"] == "ubuntu-24.04"

    workflow = yaml.safe_load(ARM64_WORKFLOW.read_text())
    assert "pull_request" not in _on_section(workflow)

    validate = workflow["jobs"]["validate"]
    assert validate["runs-on"] == "ubuntu-24.04"

    native = workflow["jobs"]["build-test-publish"]
    assert native["runs-on"] == ["self-hosted", "Linux", "ARM64", "spark", "gpu"]
    assert native["needs"] == "validate"
    assert "github.ref == 'refs/heads/main'" in native["if"]


def test_arm64_workflow_gates_native_publication():
    source = ARM64_WORKFLOW.read_text()
    workflow = yaml.safe_load(source)

    assert workflow["name"] == "Build and Publish Native ARM64 Image"
    assert "pull_request" not in _on_section(workflow)
    triggers = _on_section(workflow)
    assert "push" in triggers
    assert triggers["push"]["branches"] == ["main"]

    assert "Docker/Dockerfile.arm64" in source
    assert "docker build" in source
    assert "uname -m" in source
    assert "nvidia-smi" in source
    assert "import torch, open3d, cumm.core_cc, spconv" in source
    assert "LD_PRELOAD=" in source
    assert "import bpy" in source
    assert "/object_info" in source
    assert "check_remesher_workflows.py" in source
    assert "c18e55b05e6f5de2376655342687c2cca7b1a9c1" in source
    assert "IMPORT FAILED|Cannot import|Traceback" in source
    assert '"update_version"' in source
    assert '--build-arg UPDATE_VERSION="${UPDATE_VERSION}"' in source
    assert "docker login" in source
    assert "docker push" in source
    assert "docker buildx imagetools inspect" in source
    assert "11d5960a326750d5838078e36cf38b85af677262" in source
    assert "actions/checkout@v4" not in source
    assert "PUSHED_DIGEST" in source
    assert 'image["architecture"] == "arm64"' in source
    assert 'image["os"] == "linux"' in source
    assert "docker logout" in source

    native_steps = workflow["jobs"]["build-test-publish"]["steps"]
    cleanup = next(step for step in native_steps if step["name"] == "Clean runner images")
    record_index = next(
        index
        for index, step in enumerate(native_steps)
        if step["name"] == "Record current ARM64 cache image"
    )
    pull_index = next(
        index for index, step in enumerate(native_steps) if step["name"] == "Pull ARM64 layer cache"
    )
    assert record_index < pull_index
    assert "always()" in cleanup["if"]
    assert "docker image rm" in cleanup["run"]
    assert "PREVIOUS_ARM64_IMAGE_ID" in source
    assert 'docker image inspect --format "{{.Id}}" "${IMAGE_REPOSITORY}:arm64"' in source
    assert 'docker image rm -f "${PREVIOUS_ARM64_IMAGE_ID}"' in cleanup["run"]
    assert '"${PREVIOUS_ARM64_IMAGE_ID}" != "${CURRENT_ARM64_IMAGE_ID}"' in cleanup["run"]
    assert 'docker image inspect --format "{{json .RepoTags}}" "${PREVIOUS_ARM64_IMAGE_ID}"' in cleanup["run"]
    assert 'docker image rm -f "${IMAGE_REPOSITORY}:arm64"' not in cleanup["run"]
    assert "docker image prune" not in cleanup["run"]

    test_index = source.index("Test native ARM64 container")
    publish_index = source.index("Publish ARM64 image")
    assert test_index < publish_index
