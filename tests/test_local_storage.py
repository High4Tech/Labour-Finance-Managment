"""Verify diagnostic retention without involving tenant databases."""
import gzip
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('local_storage', Path(__file__).resolve().parents[1] / 'scripts/local_storage.py')
storage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(storage)


class LocalStorageTests(unittest.TestCase):
    def test_rotation_preserves_open_inode_and_compressed_content(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'worker.log'
            value = b'completed local job\n' * 1000
            path.write_bytes(value)
            inode = path.stat().st_ino
            with path.open('ab') as writer:
                self.assertEqual(storage.rotate_log(path, max_bytes=100), len(value))
                self.assertEqual(gzip.decompress(path.with_name('worker.log.1.gz').read_bytes()), value)
                self.assertEqual(path.stat().st_ino, inode)
                writer.write(b'new output\n')
            self.assertEqual(path.read_bytes(), b'new output\n')

    def test_retention_is_bounded_and_small_logs_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'bench.log'
            for number in range(5):
                path.write_bytes(bytes([number]) * 200)
                storage.rotate_log(path, max_bytes=100, copies=3)
            self.assertEqual(len(list(Path(directory).glob('*.gz'))), 3)
            self.assertEqual(gzip.decompress(path.with_name('bench.log.3.gz').read_bytes()), bytes([2]) * 200)
            path.write_text('small')
            self.assertEqual(storage.rotate_log(path, max_bytes=100), 0)
            self.assertEqual(path.read_text(), 'small')

    def test_failed_archive_does_not_truncate_original(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'bench.log'
            path.write_bytes(b'x' * 200)
            path.with_name('bench.log.rotate.tmp').touch()
            with self.assertRaises(RuntimeError):
                storage.rotate_log(path, max_bytes=100)
            self.assertEqual(path.stat().st_size, 200)

    def test_only_known_local_worker_redirect_is_changed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / 'Procfile'
            original = 'web: bench serve\nworker:  bench worker 1>> logs/worker.log 2>> logs/worker.error.log\ncustom: echo hello\n'
            path.write_text(original)
            storage.stream_worker_output(root)
            self.assertEqual(path.read_text(), original.replace('worker:  bench worker 1>> logs/worker.log 2>> logs/worker.error.log', 'worker:  bench worker'))


if __name__ == '__main__':
    unittest.main()
