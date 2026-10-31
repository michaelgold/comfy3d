#!/usr/bin/env python3
"""Opt-in SkinTokens runtime. Never installs into ComfyUI's interpreter."""
import argparse
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys

SOURCE_REPO = 'https://github.com/VAST-AI-Research/SkinTokens.git'
SOURCE_REVISION = '273b691d35989d71cd17ff2895fdc735097b92d1'


def run(args, **kwargs):
    return subprocess.run([str(a) for a in args], check=True, text=True, **kwargs)


def prepare_source(source, cache, repo=SOURCE_REPO, revision=SOURCE_REVISION):
    if not re.fullmatch(r'[0-9a-f]{40}', revision):
        raise ValueError('Source revision must be a full commit SHA')
    source.parent.mkdir(parents=True, exist_ok=True)
    if not source.exists():
        run(['git', 'clone', '--no-checkout', repo, source])
        run(['git', '-C', source, 'checkout', '--detach', revision])
    head = run(['git', '-C', source, 'rev-parse', 'HEAD'], capture_output=True).stdout.strip()
    if head != revision:
        raise RuntimeError(f'Refusing existing checkout at {head}; expected {revision}')
    dirty = run(['git', '-C', source, 'status', '--porcelain', '--untracked-files=no'], capture_output=True).stdout
    if dirty:
        raise RuntimeError('Refusing modified SkinTokens tracked source')
    for name in ('experiments', 'models'):
        target = cache / name
        target.mkdir(parents=True, exist_ok=True)
        link = source / name
        if link.is_symlink() and link.resolve() == target.resolve():
            continue
        if link.exists() or link.is_symlink():
            raise RuntimeError(f'Refusing to replace {link}; move existing assets manually')
        link.symlink_to(target.resolve(), target_is_directory=True)


MODEL_REVISION = '79736cad0fd84de384d5eede659b4ebd24effe33'
QWEN_REVISION = 'c1899de289a04d12100db370d81485cdf75e47ca'
CHECKPOINTS = (
    'experiments/articulation_xl_quantization_256_token_4/grpo_1400.ckpt',
    'experiments/skin_vae_2_10_32768/last.ckpt',
)


def download_models(cache, downloader=None):
    if downloader is None:
        from huggingface_hub import hf_hub_download
        downloader = hf_hub_download
    for filename in CHECKPOINTS:
        downloader(repo_id='VAST-AI/SkinTokens', revision=MODEL_REVISION,
                   filename=filename, local_dir=str(cache))
    downloader(repo_id='Qwen/Qwen3-0.6B', revision=QWEN_REVISION,
               filename='config.json', local_dir=str(cache / 'models/Qwen3-0.6B'))


def validate_assets(source):
    missing = [p for p in (*CHECKPOINTS, 'models/Qwen3-0.6B/config.json')
               if not (source / p).is_file() or (source / p).stat().st_size == 0]
    if missing:
        raise RuntimeError('Missing model assets; run download: ' + ', '.join(missing))
    config = json.loads((source / 'models/Qwen3-0.6B/config.json').read_text())
    if config.get('model_type') != 'qwen3':
        raise RuntimeError('Expected Qwen3 configuration')


def require_isolated(prefix):
    cfg = prefix / 'venv/pyvenv.cfg'
    if (Path(sys.prefix).resolve() != (prefix / 'venv').resolve()
            or sys.prefix == sys.base_prefix or not cfg.is_file()
            or 'include-system-site-packages = false' not in cfg.read_text().lower()):
        raise RuntimeError('Run with the dedicated isolated venv; refusing shared Python')


def install_dependencies(prefix):
    require_isolated(prefix)
    from importlib.metadata import distributions, version, PackageNotFoundError
    # Never let a resolver choose torch/Blender/CUDA for the operator.
    for package in ('torch', 'bpy', 'numpy'):
        try:
            version(package)
        except PackageNotFoundError as exc:
            raise RuntimeError(f'Provision platform-compatible {package} in the isolated venv first') from exc
    try:
        import flash_attn  # noqa: F401
    except ImportError as exc:
        raise RuntimeError('Provision ABI-compatible flash-attn in the isolated venv first') from exc
    constraints = prefix / 'platform-constraints.txt'
    constraints.write_text(''.join(sorted(
        f"{d.metadata['Name']}=={d.version}\n" for d in distributions() if d.metadata['Name']
    )))
    run([sys.executable, '-m', 'pip', 'install', '-c', constraints, '-r',
         Path(__file__).with_name('skintokens-requirements.txt')])
    run([sys.executable, '-m', 'pip', 'check'])
    result = run([sys.executable, '-m', 'pip', 'freeze', '--all'], capture_output=True)
    (prefix / 'installed-requirements.txt').write_text(result.stdout)


def environment(prefix, cache):
    values = {'SKINTOKENS_ROOT': prefix / 'source',
              'SKINTOKENS_PYTHON': prefix / 'venv/bin/python',
              'HF_HOME': cache / 'huggingface'}
    return ''.join(f'export {key}={shlex.quote(str(value))}\n' for key, value in values.items())


def validate_runtime(prefix):
    require_isolated(prefix)
    source = prefix / 'source'
    head = run(['git', '-C', source, 'rev-parse', 'HEAD'], capture_output=True).stdout.strip()
    if head != SOURCE_REVISION:
        raise RuntimeError('SkinTokens source pin mismatch')
    if run(['git', '-C', source, 'status', '--porcelain', '--untracked-files=no'], capture_output=True).stdout:
        raise RuntimeError('SkinTokens source has modified tracked files')
    validate_assets(source)
    run([sys.executable, '-m', 'pip', 'check'])
    # Import the actual CLI/server graphs, not just package metadata. No model load,
    # server start, checkpoint deserialization, or download occurs here.
    code = '''import sys
sys.path.insert(0, '.')
import torch, bpy, flash_attn
import demo
import src.server.bpy_server
assert torch.cuda.is_available(), 'CUDA GPU is required'
assert bpy.app.version >= (4, 2, 0), 'bpy >= 4.2 is required'
print('SkinTokens imports/CUDA OK:', torch.__version__, bpy.app.version_string)
'''
    run([sys.executable, '-I', '-c', code], cwd=source)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'install', 'download', 'validate', 'env'))
    parser.add_argument('--prefix', type=Path, default=Path('/opt/skintokens'))
    parser.add_argument('--cache', type=Path, default=Path('/app/comfy/models/skintokens'))
    parser.add_argument('--python', default=sys.executable, help='Python used to create a clean venv (prepare only)')
    args = parser.parse_args()
    prefix, cache = args.prefix.resolve(), args.cache.resolve()
    if args.action == 'env':
        print(environment(prefix, cache), end='')
        return
    if args.action == 'prepare':
        run([args.python, '-I', '-c',
             "import sys; assert sys.version_info >= (3, 11), 'SkinTokens requires Python >= 3.11'"])
        prepare_source(prefix / 'source', cache)
        cfg = prefix / 'venv/pyvenv.cfg'
        if not cfg.exists():
            if (prefix / 'venv').exists():
                raise RuntimeError('Refusing existing non-venv directory')
            run([args.python, '-m', 'venv', prefix / 'venv'])
        if 'include-system-site-packages = false' not in cfg.read_text().lower():
            raise RuntimeError('Refusing venv with system site packages')
        # --python only chooses the creator; an existing venv may be older,
        # moved, or broken. Check the interpreter actually used by the node.
        run([prefix / 'venv/bin/python', '-I', '-c',
             "import sys; from pathlib import Path; "
             "assert sys.version_info >= (3, 11), 'SkinTokens requires Python >= 3.11'; "
             "assert sys.prefix != sys.base_prefix, 'Expected isolated venv'; "
             "assert Path(sys.prefix).resolve() == Path(sys.argv[1]).resolve(), 'Venv prefix mismatch'",
             prefix / 'venv'])
        (prefix / 'env.sh').write_text(environment(prefix, cache))
        print(f'Prepared source/venv only. Provision platform wheels next. Environment: {prefix / "env.sh"}')
        return
    python = prefix / 'venv/bin/python'
    if Path(sys.prefix).resolve() != (prefix / 'venv').resolve():
        if not python.exists():
            raise RuntimeError('Run prepare first')
        # -I prevents ComfyUI PYTHONPATH/user site packages leaking into the child.
        run([python, '-I', Path(__file__).resolve(), args.action, '--prefix', prefix, '--cache', cache])
        return
    require_isolated(prefix)
    os.environ['HF_HOME'] = str(cache / 'huggingface')
    if args.action == 'install':
        install_dependencies(prefix)
    elif args.action == 'download':
        prepare_source(prefix / 'source', cache)
        download_models(cache)
        validate_assets(prefix / 'source')
        print('Pinned model assets downloaded')
    else:
        validate_runtime(prefix)


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, ValueError, subprocess.CalledProcessError) as exc:
        print(f'SkinTokens: {exc}', file=sys.stderr)
        sys.exit(1)
