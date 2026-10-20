"""Ship bounded gateway WAL segments to Kafka with at-least-once delivery.

The server binds the Kafka principal/topic to a tenant. No tenant supplied by
an HTTP caller is trusted. Payloads and credentials are never written to stdout.
"""
import argparse
from contextlib import ExitStack
import fcntl
import json
import logging
import os
from pathlib import Path
import signal
import stat
import time
import threading

MAX_LINE = 128 * 1024
MAX_BATCH_FILES = 32
MAX_BATCH_BYTES = 8 * 1024 * 1024
STOP = False
LOG = logging.getLogger('ai-log-shipper')


def producer_config(config):
    result = {
        'bootstrap.servers': config['bootstrap_servers'],
        'security.protocol': 'SASL_SSL',
        'sasl.mechanism': 'SCRAM-SHA-512',
        'sasl.username': config['username'],
        'sasl.password': config['password'],
        'ssl.endpoint.identification.algorithm': 'https',
        'enable.ssl.certificate.verification': True,
        'enable.idempotence': True,
        'acks': 'all',
        'compression.type': 'zstd',
        'linger.ms': 20,
        'batch.size': 131072,
        'message.max.bytes': 1048576,
        'delivery.timeout.ms': 120000,
        'queue.buffering.max.kbytes': 32768,
        'client.id': config['source_id'],
    }
    if config.get('ca_file'):
        result['ssl.ca.location'] = config['ca_file']
    return result


def records(stream, source_id):
    """Read bounded records; never expose payloads in errors."""
    while True:
        line = stream.readline(MAX_LINE + 1)
        if not line:
            return
        if len(line) > MAX_LINE or not line.endswith(b'\n'):
            raise ValueError('incomplete or oversized WAL line')
        event = json.loads(line)
        if not isinstance(event, dict) or event.get('schema_version') != 1 or event.get('source_id') != source_id:
            raise ValueError('WAL schema/source mismatch')
        if any(not isinstance(event.get(key), str) or not event[key] for key in ('event_id', 'capture_id')):
            raise ValueError('missing event identity')
        yield (source_id + ':' + event['capture_id']).encode(), line


def segment_batches(paths, max_files=MAX_BATCH_FILES, max_bytes=MAX_BATCH_BYTES):
    """Bound open descriptors and queued input. An oversized file runs alone."""
    batch, size = [], 0
    for path in paths:
        try:
            length = path.lstat().st_size
        except FileNotFoundError:
            continue
        if batch and (len(batch) >= max_files or size + length > max_bytes):
            yield batch
            batch, size = [], 0
        batch.append(path)
        size += length
    if batch:
        yield batch


def ship_segments(paths, producer, topic, source_id):
    """One acknowledgement barrier; retain every queued file on ambiguity.

    Validate each locked file before enqueueing any of its records. Invalid
    files remain recoverable without starving other valid files in the batch.
    Multiple partitions can progress concurrently, but enqueue order and the
    source/capture Kafka key are unchanged. Memory is bounded by the producer
    queue and one MAX_LINE record, not by the size of all files in the batch.
    """
    invalid, queued, errors = [], [], []
    acknowledged = 0

    def delivered(error, _message):
        nonlocal acknowledged
        if error is not None:
            errors.append(error.code())
        else:
            acknowledged += 1

    with ExitStack() as stack:
        for path in paths:
            try:
                fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
                stream = stack.enter_context(os.fdopen(fd, 'rb'))
                info = os.fstat(stream.fileno())
                if not stat.S_ISREG(info.st_mode):
                    raise ValueError('spool entry is not a regular file')
                try:
                    fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    continue
                count = sum(1 for _ in records(stream, source_id))
                stream.seek(0)
            except FileNotFoundError:
                continue
            except (ValueError, OSError) as error:
                invalid.append((path, error))
                continue
            # Any enqueue failure escapes before unlink; even previously
            # acknowledged files remain on disk for a stable-ID retry.
            for key, line in records(stream, source_id):
                while True:
                    try:
                        producer.produce(topic, key=key, value=line, on_delivery=delivered)
                        break
                    except BufferError:
                        producer.poll(1)
                producer.poll(0)
            queued.append((path, info, count))
        if not queued:
            return 0, invalid
        count = sum(item[2] for item in queued)
        remaining = producer.flush(125)
        if remaining or errors or acknowledged != count:
            raise RuntimeError('Kafka did not acknowledge the entire batch')
        # Check every identity before unlinking any path. Never remove a
        # replacement inode after acknowledging the original file.
        for path, info, _ in queued:
            current = path.lstat()
            if (current.st_dev, current.st_ino, current.st_size, current.st_mtime_ns) != (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns):
                raise RuntimeError('WAL file changed while delivering')
        directories = set()
        for path, _, _ in queued:
            path.unlink()
            directories.add(path.parent)
        for directory in directories:
            fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
        return count, invalid


def ship_segment(path, producer, topic, source_id):
    """Compatibility entry point for one-file callers and replay tools."""
    count, invalid = ship_segments([path], producer, topic, source_id)
    if invalid:
        raise invalid[0][1]
    return count


def spool_stats(spool, now=None):
    """Count only files currently on disk, including unacknowledged batches."""
    now = time.time() if now is None else now
    pending, files, oldest = 0, 0, now
    for path in spool.iterdir():
        if path.suffix not in ('.ready', '.open'):
            continue
        try:
            info = path.lstat()
        except FileNotFoundError:
            continue
        if not stat.S_ISREG(info.st_mode):
            continue
        pending += info.st_size
        files += 1
        oldest = min(oldest, info.st_mtime)
    return {'pending_bytes': pending, 'pending_files': files,
            'oldest_age_seconds': max(0, int(now - oldest)), 'updated_at': int(now)}


class StatusReporter:
    """Refresh local queue metrics even during a slow Kafka flush."""
    def __init__(self, spool, interval=30):
        self.spool, self.interval = spool, interval
        self.lock, self.stopped = threading.Lock(), threading.Event()
        self.values = {'delivered_events': 0, 'failures': 0}
        self.thread = threading.Thread(target=self.run, name='shipper-status', daemon=True)

    def update(self, **values):
        with self.lock:
            self.values.update(values)

    def publish(self):
        from shipper_control import atomic_file
        stats = spool_stats(self.spool)
        with self.lock:
            stats.update(self.values)
        atomic_file(self.spool / 'shipper-status.json', json.dumps(stats).encode())
        LOG.info('status %s', json.dumps(stats))
        return stats

    def run(self):
        while not self.stopped.is_set():
            try:
                self.publish()
            except Exception as error:
                LOG.error('status_failed class=%s', type(error).__name__)
            self.stopped.wait(self.interval)

    def close(self):
        self.stopped.set()
        self.thread.join(timeout=5)


def main():
    from confluent_kafka import Producer
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True)
    args = parser.parse_args()
    config_path = Path(args.config)
    if stat.S_IMODE(config_path.stat().st_mode) & 0o077:
        raise ValueError('shipper config must be mode 0600')
    config = json.loads(config_path.read_text())
    spool = Path(config['spool_dir']).resolve(strict=True)
    # Hold this descriptor for the process lifetime. Two shippers could
    # otherwise reorder segments of the same capture across Kafka partitions.
    lock_fd = os.open(spool / '.shipper.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    from shipper_control import Heartbeat, prepare_probe
    instance = prepare_probe(config, spool)
    heartbeat = Heartbeat(config, spool, instance) if instance else None
    producer = Producer(producer_config(config))
    if heartbeat:
        heartbeat.thread.start()
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    def stop(_signal, _frame):
        global STOP
        STOP = True
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    delivered, last_delivery_at = 0, 0
    invalid_segments = {}
    reporter = StatusReporter(spool)
    reporter.thread.start()
    try:
        while not STOP:
            failed, delivery_failures = 0, 0
            entries = sorted((p for p in spool.iterdir() if p.suffix in ('.ready', '.open')), key=lambda p: p.name)
            candidates = []
            for path in entries:
                try:
                    info = path.lstat()
                except FileNotFoundError:
                    continue
                fingerprint = (info.st_ino, info.st_mtime_ns, info.st_size)
                if invalid_segments.get(path.name) == fingerprint:
                    failed += 1
                    continue
                candidates.append(path)
            for batch in segment_batches(candidates):
                if STOP:
                    break
                try:
                    count, invalid = ship_segments(batch, producer, config['topic'], config['source_id'])
                    delivered += count
                    if count:
                        last_delivery_at = int(time.time())
                    for path, error in invalid:
                        failed += 1
                        LOG.error('segment_delivery_failed file=%s class=%s', path.name, type(error).__name__)
                        if isinstance(error, ValueError):
                            try:
                                info = path.lstat()
                                invalid_segments[path.name] = (info.st_ino, info.st_mtime_ns, info.st_size)
                            except FileNotFoundError:
                                pass
                except Exception as error:
                    failed += 1
                    delivery_failures += 1
                    LOG.error('batch_delivery_failed files=%d class=%s', len(batch), type(error).__name__)
                    time.sleep(1)
                reporter.update(delivered_events=delivered, failures=failed)
                if heartbeat:
                    heartbeat.update(delivered_events=delivered, failures=failed,
                                     last_delivery_at=last_delivery_at)
                if delivery_failures >= 3:
                    break
            present = {path.name for path in entries}
            invalid_segments = {name: value for name, value in invalid_segments.items() if name in present}
            reporter.update(delivered_events=delivered, failures=failed)
            if heartbeat:
                heartbeat.update(failures=failed)
            time.sleep(1)
    finally:
        # A forced shutdown can duplicate acknowledged records, but cannot
        # delete unacknowledged WAL; stable event IDs support recovery.
        producer.flush(15)
        reporter.close()
        if heartbeat:
            heartbeat.close()
        os.close(lock_fd)


if __name__ == '__main__':
    main()
