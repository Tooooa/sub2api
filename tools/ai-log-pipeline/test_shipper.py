import fcntl
import json
import os
from pathlib import Path
import tempfile
import threading
import time
import types
import unittest
from unittest import mock

import shipper


class Producer:
    def __init__(self, fail=False):
        self.fail = fail
        self.messages = []
        self.callbacks = []
        self.flushes = 0

    def produce(self, topic, **kwargs):
        self.messages.append((topic, kwargs['key'], kwargs['value']))
        self.callbacks.append(kwargs['on_delivery'])

    def poll(self, _timeout):
        pass

    def flush(self, _timeout):
        self.flushes += 1
        if self.fail:
            return len(self.callbacks)
        callbacks, self.callbacks = self.callbacks, []
        for callback in callbacks:
            callback(None, None)
        return 0


class ShipperTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'segment.ready'
        self.event = {'schema_version': 1, 'event_id': 'event-1', 'source_id': 'source', 'capture_id': 'capture-1'}
        self.path.write_text(json.dumps(self.event)+'\n')

    def test_ambiguous_delivery_retains_file_and_retry_keeps_identity(self):
        failed = Producer(fail=True)
        with self.assertRaises(RuntimeError):
            shipper.ship_segment(self.path, failed, 'raw', 'source')
        self.assertTrue(self.path.exists())
        success = Producer()
        self.assertEqual(shipper.ship_segment(self.path, success, 'raw', 'source'), 1)
        self.assertEqual(failed.messages, success.messages)
        self.assertFalse(self.path.exists())

    def test_active_writer_is_not_read_or_deleted(self):
        with self.path.open('rb') as writer:
            fcntl.flock(writer, fcntl.LOCK_EX | fcntl.LOCK_NB)
            producer = Producer()
            self.assertEqual(shipper.ship_segment(self.path, producer, 'raw', 'source'), 0)
            self.assertEqual(producer.messages, [])
        self.assertTrue(self.path.exists())

    def test_partial_tail_is_retained(self):
        self.path.write_bytes(self.path.read_bytes()+b'{"partial":')
        with self.assertRaises(ValueError):
            shipper.ship_segment(self.path, Producer(), 'raw', 'source')
        self.assertTrue(self.path.exists())

    def test_wrong_source_and_symlinks_rejected(self):
        with self.assertRaises(ValueError):
            shipper.ship_segment(self.path, Producer(), 'raw', 'other')
        link = self.path.parent/'link.ready'
        link.symlink_to(self.path)
        with self.assertRaises(OSError):
            shipper.ship_segment(link, Producer(), 'raw', 'source')

    def test_invalid_json_shapes_remain_recoverable(self):
        for value in ([], None, dict(self.event, capture_id=23)):
            with self.subTest(value=value):
                self.path.write_text(json.dumps(value)+'\n')
                with self.assertRaises(ValueError):
                    shipper.ship_segment(self.path, Producer(), 'raw', 'source')
                self.assertTrue(self.path.exists())

    def test_tls_and_idempotence_cannot_be_disabled_by_config(self):
        config = shipper.producer_config({'bootstrap_servers': 'example:443', 'username': 'user', 'password': 'private', 'source_id': 'source', 'security.protocol': 'PLAINTEXT'})
        self.assertEqual(config['security.protocol'], 'SASL_SSL')
        self.assertEqual(config['acks'], 'all')
        self.assertTrue(config['enable.idempotence'])
        self.assertTrue(config['enable.ssl.certificate.verification'])

    def add_segment(self, name, event_id):
        path = self.path.parent / name
        path.write_text(json.dumps(dict(self.event, event_id=event_id)) + '\n')
        return path

    def test_multiple_files_share_one_flush_and_keep_wire_identity(self):
        second = self.add_segment('second.ready', 'event-2')
        expected = [self.path.read_bytes(), second.read_bytes()]
        producer = Producer()
        count, invalid = shipper.ship_segments([self.path, second], producer, 'raw', 'source')
        self.assertEqual((count, invalid), (2, []))
        self.assertEqual(producer.flushes, 1)
        self.assertEqual([m[2] for m in producer.messages], expected)
        self.assertEqual([m[1] for m in producer.messages], [b'source:capture-1'] * 2)
        self.assertFalse(self.path.exists())
        self.assertFalse(second.exists())

    def test_batch_timeout_retains_every_file_and_retry_is_byte_identical(self):
        second = self.add_segment('second.ready', 'event-2')
        failed = Producer(fail=True)
        with self.assertRaises(RuntimeError):
            shipper.ship_segments([self.path, second], failed, 'raw', 'source')
        self.assertTrue(self.path.exists())
        self.assertTrue(second.exists())
        success = Producer()
        self.assertEqual(shipper.ship_segments([self.path, second], success, 'raw', 'source'), (2, []))
        self.assertEqual(failed.messages, success.messages)

    def test_partial_ack_or_delivery_error_never_unlinks_batch(self):
        second = self.add_segment('second.ready', 'event-2')
        for mode in ('missing-callback', 'delivery-error'):
            with self.subTest(mode=mode):
                producer = Producer()
                def flush(_timeout):
                    producer.callbacks[0](None, None)
                    if mode == 'delivery-error':
                        producer.callbacks[1](types.SimpleNamespace(code=lambda: -1), None)
                    return 0
                producer.flush = flush
                with self.assertRaises(RuntimeError):
                    shipper.ship_segments([self.path, second], producer, 'raw', 'source')
                self.assertTrue(self.path.exists())
                self.assertTrue(second.exists())

    def test_invalid_tail_is_never_enqueued_and_does_not_block_valid_file(self):
        self.path.write_bytes(self.path.read_bytes() + b'{"partial":')
        second = self.add_segment('second.ready', 'event-2')
        producer = Producer()
        count, invalid = shipper.ship_segments([self.path, second], producer, 'raw', 'source')
        self.assertEqual(count, 1)
        self.assertEqual(invalid[0][0], self.path)
        self.assertIsInstance(invalid[0][1], ValueError)
        self.assertEqual(len(producer.messages), 1)
        self.assertIn(b'event-2', producer.messages[0][2])
        self.assertTrue(self.path.exists())
        self.assertFalse(second.exists())

    def test_active_writer_does_not_block_other_files_in_batch(self):
        second = self.add_segment('second.ready', 'event-2')
        with self.path.open('rb') as writer:
            fcntl.flock(writer, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.assertEqual(shipper.ship_segments([self.path, second], Producer(), 'raw', 'source'), (1, []))
        self.assertTrue(self.path.exists())
        self.assertFalse(second.exists())

    def test_replaced_inode_is_not_deleted_after_ack(self):
        second = self.add_segment('second.ready', 'event-2')
        replacement = self.add_segment('replacement', 'replacement-event')
        producer = Producer()
        flush = producer.flush
        def replace_after_ack(timeout):
            result = flush(timeout)
            replacement.replace(self.path)
            return result
        producer.flush = replace_after_ack
        with self.assertRaises(RuntimeError):
            shipper.ship_segments([self.path, second], producer, 'raw', 'source')
        self.assertIn('replacement-event', self.path.read_text())
        self.assertTrue(second.exists())

    def test_enqueue_failure_keeps_previously_queued_files(self):
        second = self.add_segment('second.ready', 'event-2')
        producer = Producer()
        produce = producer.produce
        def failing_produce(topic, **kwargs):
            if producer.messages:
                raise RuntimeError('synthetic producer failure')
            produce(topic, **kwargs)
        producer.produce = failing_produce
        with self.assertRaises(RuntimeError):
            shipper.ship_segments([self.path, second], producer, 'raw', 'source')
        self.assertTrue(self.path.exists())
        self.assertTrue(second.exists())

    def test_batch_limits_and_oversized_file_preserve_order(self):
        paths = [self.path] + [self.add_segment(str(i) + '.ready', str(i)) for i in range(5)]
        batches = list(shipper.segment_batches(paths, max_files=2, max_bytes=10**6))
        self.assertEqual([len(b) for b in batches], [2, 2, 2])
        self.assertEqual([p for b in batches for p in b], paths)
        batches = list(shipper.segment_batches(paths, max_files=32, max_bytes=1))
        self.assertEqual([len(b) for b in batches], [1] * len(paths))

    def test_fifo_is_rejected_without_blocking(self):
        path = self.path.parent / 'fifo.ready'
        os.mkfifo(path)
        with self.assertRaises(ValueError):
            shipper.ship_segment(path, Producer(), 'raw', 'source')
        self.assertTrue(path.exists())

    def test_queue_metrics_exclude_deleted_files_and_nonregular_entries(self):
        os.utime(self.path, (100, 100))
        second = self.add_segment('second.open', 'event-2')
        os.utime(second, (200, 200))
        (self.path.parent / 'ignored.ready').symlink_to(second)
        (self.path.parent / 'directory.ready').mkdir()
        before = shipper.spool_stats(self.path.parent, now=300)
        self.assertEqual(before['pending_files'], 2)
        self.assertEqual(before['oldest_age_seconds'], 200)
        shipper.ship_segment(self.path, Producer(), 'raw', 'source')
        after = shipper.spool_stats(self.path.parent, now=300)
        self.assertEqual(after['pending_bytes'], second.stat().st_size)
        self.assertEqual(after['pending_files'], 1)
        self.assertEqual(after['oldest_age_seconds'], 100)

    def test_status_keeps_refreshing_while_kafka_flush_is_blocked(self):
        entered, release = threading.Event(), threading.Event()
        producer = Producer()
        flush = producer.flush
        def slow_flush(timeout):
            entered.set()
            self.assertTrue(release.wait(5))
            return flush(timeout)
        producer.flush = slow_flush
        worker = threading.Thread(target=lambda: shipper.ship_segment(self.path, producer, 'raw', 'source'))
        reporter = shipper.StatusReporter(self.path.parent, interval=.01)
        worker.start()
        reporter.thread.start()
        try:
            self.assertTrue(entered.wait(2))
            new = self.add_segment('new.ready', 'event-2')
            deadline = time.monotonic() + 2
            while time.monotonic() < deadline:
                try:
                    stats = json.loads((self.path.parent / 'shipper-status.json').read_text())
                    if stats['pending_files'] == 2:
                        break
                except FileNotFoundError:
                    pass
                time.sleep(.01)
            else:
                self.fail('status did not refresh while Kafka was blocked')
            self.assertEqual(stats['pending_bytes'], self.path.stat().st_size + new.stat().st_size)
        finally:
            release.set()
            worker.join(3)
            reporter.close()
        self.assertFalse(worker.is_alive())

    def test_stop_after_ack_preserves_not_yet_queued_batches(self):
        second = self.add_segment('second.ready', 'event-2')
        config = self.path.parent / 'config.json'
        config.write_text(json.dumps({'spool_dir': str(self.path.parent), 'topic': 'raw', 'source_id': 'source',
                                     'bootstrap_servers': 'example', 'username': 'user', 'password': 'private'}))
        config.chmod(0o600)
        producer = Producer()
        flush = producer.flush
        def stop_after_ack(timeout):
            result = flush(timeout)
            shipper.STOP = True
            return result
        producer.flush = stop_after_ack
        with mock.patch.dict('sys.modules', {'confluent_kafka': types.SimpleNamespace(Producer=lambda _: producer)}), \
                mock.patch('sys.argv', ['shipper', '--config', str(config)]), \
                mock.patch('shipper.signal.signal'), mock.patch('shipper.time.sleep'), \
                mock.patch.object(shipper, 'STOP', False), \
                mock.patch('shipper.segment_batches', side_effect=lambda paths: ([p] for p in paths)):
            shipper.main()
        # Sorted order sends second.ready first; the unqueued segment survives.
        self.assertFalse(second.exists())
        self.assertTrue(self.path.exists())


if __name__ == '__main__':
    unittest.main()
