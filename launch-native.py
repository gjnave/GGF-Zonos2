"""App-local Python launcher for the unchanged native Zonos engine.

The environment supplies runtime DLLs and the audio decoder, not a toolkit.
No PyTorch, GPU model loading, system installation or third-party messaging.
"""
from __future__ import annotations
import argparse
import ctypes
import os
from pathlib import Path
import subprocess
import sys
import sysconfig

def native_environment():
    if sys.version_info[:2] != (3, 11) or sys.maxsize <= 2**32:
        raise RuntimeError('Run the app-local 64-bit Python 3.11 created by uv.')
    import imageio_ffmpeg
    import requests  # Used by the app's forthcoming installer/update helper.
    del requests
    packages = Path(sysconfig.get_path('purelib'))
    runtime = packages / 'nvidia' / 'cuda_runtime' / 'bin'
    blas = packages / 'nvidia' / 'cublas' / 'bin'
    for directory, filename in [(runtime, 'cudart64_12.dll'), (blas, 'cublas64_12.dll'), (blas, 'cublasLt64_12.dll')]:
        if not (directory / filename).is_file():
            raise RuntimeError(f'Missing application dependency: {filename}. Rerun install.bat.')
    env = dict(os.environ)
    env['PATH'] = os.pathsep.join([str(runtime), str(blas), env.get('PATH', '')])
    env.setdefault('ZONOS2_FFMPEG', imageio_ffmpeg.get_ffmpeg_exe())
    if not Path(env['ZONOS2_FFMPEG']).is_file():
        raise RuntimeError('The configured reference-audio decoder does not exist.')
    return env

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check-environment', action='store_true')
    parser.add_argument('--engine')
    parser.add_argument('--workdir', type=Path)
    args, native_args = parser.parse_known_args()
    env = native_environment()
    if args.check_environment:
        print(f'Python {sys.version.split()[0]}: {sys.executable}')
        print('App-local CUDA runtime libraries and FFmpeg are ready; no CUDA toolkit was installed.')
        return 0
    if not args.engine:
        raise RuntimeError('Native engine path was not provided.')
    engine = Path(args.engine).resolve()
    if not engine.is_file():
        raise RuntimeError(f'Native Zonos application executable is missing: {engine}')
    if '--gpu' in native_args:
        try:
            ctypes.WinDLL('nvcuda.dll')
        except OSError as exc:
            raise RuntimeError('NVIDIA driver is not available. Install/update it through the normal PC setup.') from exc
    workdir = (args.workdir or engine.parent).resolve()
    return subprocess.call([str(engine), *native_args], cwd=workdir, env=env)

if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (RuntimeError, ImportError) as error:
        print(f'ERROR: {error}', file=sys.stderr)
        raise SystemExit(1)
