"""Bound local diagnostic output; never remove site or accounting records."""
import gzip
from pathlib import Path

MAX_LOG_BYTES = 8 * 1024 * 1024
LOG_COPIES = 3
LOCAL_LOGS = ('bench.log', 'bench-start.log', 'worker.log', 'worker.error.log', 'platform-worker.log')


def rotate_log(path: Path, max_bytes=MAX_LOG_BYTES, copies=LOG_COPIES):
    """Copy/compress then truncate the same inode, compatible with open writers.

    Like logrotate copytruncate, a concurrent diagnostic write at truncation can
    be lost. This is exclusively for console/CLI logs, never audit/business data.
    The initial cleanup runs with the app stopped and archives all prior output.
    """
    if max_bytes <= 0 or copies < 1:
        raise ValueError('Positive log limits are required')
    if path.is_symlink() or not path.is_file() or path.stat().st_size <= max_bytes:
        return 0
    temp = path.with_name(path.name + '.rotate.tmp')
    if temp.exists() or temp.is_symlink():
        raise RuntimeError('A previous log rotation needs operator review')
    size = path.stat().st_size
    try:
        # Snapshot only the measured bytes; an actively growing log cannot make
        # compression run indefinitely. No truncation until gzip is closed.
        with path.open('rb') as source, temp.open('xb') as raw:
            with gzip.GzipFile(fileobj=raw, mode='wb', compresslevel=6, mtime=0) as target:
                remaining = size
                while remaining:
                    chunk = source.read(min(1024 * 1024, remaining))
                    if not chunk:
                        raise RuntimeError('Log changed during rotation')
                    target.write(chunk)
                    remaining -= len(chunk)
        oldest = path.with_name(f'{path.name}.{copies}.gz')
        if oldest.is_symlink():
            raise RuntimeError('Refusing a linked log archive')
        for index in range(copies - 1, 0, -1):
            source = path.with_name(f'{path.name}.{index}.gz')
            target = path.with_name(f'{path.name}.{index + 1}.gz')
            if source.is_symlink() or target.is_symlink():
                raise RuntimeError('Refusing a linked log archive')
            if source.exists():
                source.replace(target)
        temp.replace(path.with_name(path.name + '.1.gz'))
        with path.open('r+b') as stream:
            # Preserve output appended while the snapshot was compressed.
            stream.seek(size)
            tail = stream.read()
            stream.seek(0)
            stream.write(tail)
            stream.truncate()
        return size
    finally:
        if temp.exists() and not temp.is_symlink():
            temp.unlink()


def maintain_logs(bench: Path):
    directory = bench / 'logs'
    if directory.is_symlink():
        raise RuntimeError('Expected the local bench log directory')
    return sum(rotate_log(directory / name) for name in LOCAL_LOGS)


def stream_worker_output(bench: Path):
    """Use the already bounded Docker logger, not unlimited shell redirects."""
    path = bench / 'Procfile'
    original = path.read_text()
    old = 'worker:  bench worker 1>> logs/worker.log 2>> logs/worker.error.log'
    if old in original:
        path.write_text(original.replace(old, 'worker:  bench worker'))
