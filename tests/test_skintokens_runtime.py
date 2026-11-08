import importlib.util
from pathlib import Path
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]


def runtime():
    spec = importlib.util.spec_from_file_location('skintokens_runtime', ROOT / 'utils/skintokens_runtime.py')
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_vendored_patch_matches_gpu_exercised_bytes():
    import hashlib
    patch = runtime().SOURCE_PATCH
    assert hashlib.sha256(patch.read_bytes()).hexdigest() == (
        '85de82bf3f405c015509543100e3ac2a72a605eaf7db731d1fb955a99233b9f7'
    )


@pytest.fixture
def source_fixture(tmp_path):
    m = runtime()
    origin = tmp_path / 'origin'
    origin.mkdir()
    subprocess.run(['git', 'init', str(origin)], check=True, capture_output=True)
    (origin / 'demo.py').write_text('# fixture\n')
    tokenrig = origin / 'src/model/tokenrig.py'
    tokenrig.parent.mkdir(parents=True)
    tokenrig.write_text('''        )[0], device=device).unsqueeze(0)
        assert start_tokens.shape[0] == 1
        start_embed = self.transformer.get_input_embeddings()(start_tokens)
        inputs_embeds = torch.cat([learned_mesh_cond, start_embed], dim=1)
\x20\x20\x20\x20\x20\x20\x20\x20
        results = self.transformer.generate(
            inputs_embeds=inputs_embeds,
''')
    tokenrig.chmod(0o755)
    subprocess.run(['git', '-C', str(origin), 'add', '.'], check=True)
    subprocess.run(['git', '-C', str(origin), '-c', 'user.name=Test', '-c', 'user.email=test@example.org', 'commit', '-m', 'fixture'], check=True, capture_output=True)
    revision = subprocess.check_output(['git', '-C', str(origin), 'rev-parse', 'HEAD'], text=True).strip()
    source = tmp_path / 'runtime/source'
    cache = tmp_path / 'cache'
    return m, origin, revision, source, cache


def test_prepare_checks_out_exact_revision_and_links_persistent_models(source_fixture):
    m, origin, revision, source, cache = source_fixture
    m.prepare_source(source, cache, str(origin), revision)
    patched = (source / 'src/model/tokenrig.py').read_bytes()
    assert b'.to(start_embed.dtype)' in patched
    m.prepare_source(source, cache, str(origin), revision)
    assert (source / 'src/model/tokenrig.py').read_bytes() == patched
    m.validate_source(source, revision)
    assert subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip() == revision
    assert (source / 'experiments').resolve() == cache / 'experiments'
    assert (source / 'models').resolve() == cache / 'models'
    (source / 'demo.py').write_text('# user edit\n')
    with pytest.raises(RuntimeError, match='modified'):
        m.prepare_source(source, cache, str(origin), revision)


@pytest.mark.parametrize('change', [
    'unrelated', 'same-file', 'staged', 'staged-add', 'deleted', 'mode',
    'assume-unchanged', 'skip-worktree', 'staged-hidden-by-worktree',
])
def test_prepare_and_validate_refuse_every_other_tracked_change(source_fixture, change):
    m, origin, revision, source, cache = source_fixture
    m.prepare_source(source, cache, str(origin), revision)
    path = source / ('src/model/tokenrig.py' if change == 'same-file' else 'demo.py')
    git = ['git', '-C', str(source)]
    original = path.read_bytes()
    if change in ('assume-unchanged', 'skip-worktree'):
        subprocess.run([*git, 'update-index', '--' + change, 'demo.py'], check=True)
    if change == 'deleted':
        path.unlink()
    elif change == 'mode':
        path.chmod(0o755)
    elif change == 'staged-add':
        (source / 'other.py').write_text('# extra tracked file\n')
        subprocess.run([*git, 'add', 'other.py'], check=True)
    else:
        path.write_bytes(original + b'# unexpected edit\n')
        if change in ('staged', 'staged-hidden-by-worktree'):
            subprocess.run([*git, 'add', 'demo.py'], check=True)
        if change == 'staged-hidden-by-worktree':
            path.write_bytes(original)
    before = path.read_bytes() if path.exists() else None
    with pytest.raises(RuntimeError, match='modified'):
        m.validate_source(source, revision)
    with pytest.raises(RuntimeError, match='modified'):
        m.prepare_source(source, cache, str(origin), revision)
    assert (path.read_bytes() if path.exists() else None) == before


def test_validate_requires_patch_and_correct_pin_without_repair(source_fixture):
    m, origin, revision, source, cache = source_fixture
    with pytest.raises(RuntimeError, match='missing required prefill'):
        m.validate_source(origin, revision)
    assert b'.to(start_embed.dtype)' not in (origin / 'src/model/tokenrig.py').read_bytes()
    with pytest.raises(RuntimeError, match='pin mismatch'):
        m.validate_source(origin, '0' * 40)
    (origin / 'demo.py').write_text('# preexisting edit\n')
    with pytest.raises(RuntimeError, match='modified'):
        m.prepare_source(origin, cache, str(origin), revision)
    assert b'.to(start_embed.dtype)' not in (origin / 'src/model/tokenrig.py').read_bytes()
    assert not cache.exists()


def test_expected_patch_can_be_staged_and_untracked_assets_are_allowed(source_fixture):
    m, origin, revision, source, cache = source_fixture
    m.prepare_source(source, cache, str(origin), revision)
    subprocess.run(['git', '-C', str(source), 'add', 'src/model/tokenrig.py'], check=True)
    (source / 'result.glb').write_bytes(b'untracked output')
    m.validate_source(source, revision)
    m.prepare_source(source, cache, str(origin), revision)


def test_runtime_validation_uses_exact_source_check(source_fixture, monkeypatch):
    m, origin, revision, source, cache = source_fixture
    m.prepare_source(source, cache, str(origin), revision)
    monkeypatch.setattr(m, 'require_isolated', lambda prefix: None)
    real_validate = m.validate_source
    monkeypatch.setattr(m, 'validate_source', lambda path: real_validate(path, revision))
    # Patched source gets through to the next real validation boundary.
    with pytest.raises(RuntimeError, match='Missing model assets'):
        m.validate_runtime(source.parent)
    (source / 'demo.py').write_text('# unexpected edit\n')
    with pytest.raises(RuntimeError, match='modified'):
        m.validate_runtime(source.parent)


def test_download_pins_both_repositories_and_only_required_files(tmp_path):
    m = runtime()
    calls = []
    def download(**kwargs):
        calls.append(kwargs)
    m.download_models(tmp_path, download)
    assert len(calls) == 3
    assert {c['revision'] for c in calls} == {m.MODEL_REVISION, m.QWEN_REVISION}
    assert all(len(c['revision']) == 40 for c in calls)
    assert {c['filename'] for c in calls} == set(m.CHECKPOINTS) | {'config.json'}
    assert calls[-1]['local_dir'] == str(tmp_path / 'models/Qwen3-0.6B')


def test_dependencies_refuse_nonisolated_python_before_install(tmp_path):
    m = runtime()
    with pytest.raises(RuntimeError, match='isolated venv'):
        m.install_dependencies(tmp_path)


def test_missing_models_are_reported_not_silently_downloaded(tmp_path):
    m = runtime()
    with pytest.raises(RuntimeError, match='Missing model assets'):
        m.validate_assets(tmp_path)


def test_env_quotes_paths_and_exposes_node_contract(tmp_path):
    m = runtime()
    import shlex
    prefix = tmp_path / 'runtime space'
    cache = tmp_path / 'cache space'
    text = m.environment(prefix, cache)
    assert shlex.quote(str(prefix / 'source')) in text
    assert 'SKINTOKENS_ROOT=' in text
    assert 'SKINTOKENS_PYTHON=' in text
    assert 'HF_HOME=' in text
    assert 'LD_PRELOAD' not in text


def test_prepare_rejects_non_sha_before_mutating(tmp_path):
    m = runtime()
    with pytest.raises(ValueError, match='full commit SHA'):
        m.prepare_source(tmp_path / 'source', tmp_path / 'cache', revision='main')
    assert not (tmp_path / 'source').exists()


def test_installer_freezes_existing_platform_packages(tmp_path, monkeypatch):
    m = runtime()
    import importlib.metadata
    import sys
    from types import SimpleNamespace
    monkeypatch.setattr(m, 'require_isolated', lambda prefix: None)
    monkeypatch.setattr(importlib.metadata, 'version', lambda name: '1.0')
    monkeypatch.setattr(importlib.metadata, 'distributions', lambda: [
        SimpleNamespace(metadata={'Name': name}, version=ver)
        for name, ver in [('torch', '2.7.0+cu128'), ('bpy', '4.2.0'), ('numpy', '1.26.4')]
    ])
    monkeypatch.setitem(sys.modules, 'flash_attn', SimpleNamespace())
    calls = []
    def run(args, **kwargs):
        calls.append([str(a) for a in args])
        return SimpleNamespace(stdout='fixture freeze\n')
    monkeypatch.setattr(m, 'run', run)
    m.install_dependencies(tmp_path)
    constraints = tmp_path / 'platform-constraints.txt'
    assert constraints.read_text().splitlines() == ['bpy==4.2.0', 'numpy==1.26.4', 'torch==2.7.0+cu128']
    assert calls[0][calls[0].index('-c') + 1] == str(constraints)
    assert calls[1][-2:] == ['pip', 'check']
    assert (tmp_path / 'installed-requirements.txt').read_text() == 'fixture freeze\n'


def test_compose_is_opt_in_and_preserves_default_dependencies():
    import yaml
    overlay = yaml.safe_load((ROOT / 'docker-compose.skintokens.yml').read_text())
    service = overlay['services']['comfy3d']
    assert service['environment'] == {
        'SKINTOKENS_ROOT': '/opt/skintokens/source',
        'SKINTOKENS_PYTHON': '/opt/skintokens/venv/bin/python',
    }
    assert 'command' not in service and 'entrypoint' not in service
    assert 'SKINTOKENS' not in (ROOT / 'docker-compose.yml').read_text()
    requirements = (ROOT / 'utils/skintokens-requirements.txt').read_text().splitlines()
    assert not any(line.startswith(('torch', 'bpy', 'flash-attn')) for line in requirements)


def test_prepare_validates_reused_venv_before_publishing_environment(tmp_path, monkeypatch):
    m = runtime()
    import sys
    from types import SimpleNamespace
    prefix = tmp_path / 'runtime'
    (prefix / 'venv').mkdir(parents=True)
    (prefix / 'venv/pyvenv.cfg').write_text('include-system-site-packages = false\n')
    monkeypatch.setattr(m, 'prepare_source', lambda *args: None)
    monkeypatch.setattr(sys, 'argv', ['runtime', 'prepare', '--prefix', str(prefix),
                                    '--cache', str(tmp_path / 'cache')])
    calls = []
    def run(args, **kwargs):
        calls.append([str(a) for a in args])
        if str(args[0]) == str(prefix / 'venv/bin/python'):
            raise subprocess.CalledProcessError(1, args)
        return SimpleNamespace(stdout='')
    monkeypatch.setattr(m, 'run', run)
    with pytest.raises(subprocess.CalledProcessError):
        m.main()
    assert not (prefix / 'env.sh').exists()
    assert calls[-1][0] == str(prefix / 'venv/bin/python')
    assert calls[-1][1:3] == ['-I', '-c']


def test_documentation_does_not_recommend_unsafe_upstream_server():
    import re
    text = (ROOT / 'docs/skintokens.md').read_text()
    shell_blocks = re.findall(r'```sh\n(.*?)```', text, re.S)
    assert not any('demo.py' in block for block in shell_blocks)
    assert 'loopback' in text
    assert 'Integration pending' not in text
    assert 'd53a0010f31106abf7dfe0822404cfe5d9a1b274' in text
    assert 'single-sample end-to-end smoke passed on ARM64 Spark' in text
    assert 'does **not** qualify clean separate-runtime installation' in text
    smoke = next(block for block in shell_blocks if 'skintokens_worker.py' in block)
    assert '/app/comfy/custom_nodes/ComfyUI-UniRig/nodes/skintokens_worker.py' in smoke
    assert 'cd "$SKINTOKENS_ROOT"' in smoke
    assert '"$SKINTOKENS_PYTHON"' in smoke
    assert '--use_transfer' in smoke
    assert 'env LD_PRELOAD= OMP_NUM_THREADS=4' in smoke
    assert '--use_postprocess' not in smoke  # not part of the recorded Spark run
    assert 'export LD_PRELOAD' not in text and 'unset LD_PRELOAD' not in text
    assert '2.13.0+cu130' in text and '4.57.6' in text
    assert 'transformers==4.57.6' in (ROOT / 'utils/skintokens-requirements.txt').read_text()
    assert 'timeout --signal=TERM --kill-after=10s' in smoke
    commands = '\n'.join(line for line in smoke.splitlines() if not line.lstrip().startswith('#'))
    assert '--foreground' not in commands


def test_prepare_checks_real_venv_and_is_idempotent(tmp_path, monkeypatch):
    m = runtime()
    import sys
    prefix = tmp_path / 'runtime'
    monkeypatch.setattr(m, 'prepare_source', lambda *args: None)
    monkeypatch.setattr(sys, 'argv', ['runtime', 'prepare', '--prefix', str(prefix),
                                    '--cache', str(tmp_path / 'cache'),
                                    '--python', sys.executable])
    m.main()
    first_env = (prefix / 'env.sh').read_text()
    m.main()
    assert (prefix / 'env.sh').read_text() == first_env
    assert 'include-system-site-packages = false' in (prefix / 'venv/pyvenv.cfg').read_text()
