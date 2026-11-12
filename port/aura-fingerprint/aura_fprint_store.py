"""Private transactional storage for the future fprintd bridge.

Only trusted root callers may use this API. fprintd must authorize the caller
and resolve its account before calling it; this module grants no authorization.
It never reads template contents, PINs, handles or authentication tokens.
The secure-storage listener will write opaque databases under generated names.
Not connected to the existing engineering enrollment or installed system-wide.
"""
import contextlib
import fcntl
import json
import os
import re
import stat
import uuid

MAX_DB = 1024 * 1024
MAX_MANIFEST = 65536
NAME = re.compile(r"u([0-9]{1,10})-f([1-9]|10)-([0-9a-f]{32})\.db\Z")


class StoreError(Exception):
    pass


def _write_all(fd, data):
    while data:
        n = os.write(fd, data)
        if n <= 0:
            raise StoreError('Incomplete state write')
        data = data[n:]


def _private(fd, directory=False):
    s = os.fstat(fd)
    kind = stat.S_ISDIR if directory else stat.S_ISREG
    if not kind(s.st_mode) or s.st_uid != 0 or s.st_mode & 0o077:
        raise StoreError('Unsafe private storage permissions')
    if not directory and s.st_nlink != 1:
        raise StoreError('Hard-linked private state is not accepted')
    return s


def _unique_pairs(pairs):
    result = {}
    for k, v in pairs:
        if k in result:
            raise StoreError('Duplicate manifest field')
        result[k] = v
    return result


class Store:
    """Hold the storage lock throughout one secure-sensor transaction.

    The already-created directory must be root-owned and mode 0700, reached
    through root-owned parents with no group/other write permission. No path
    from a username, D-Bus caller or firmware message is accepted by this API.
    """
    def __init__(self, path):
        self.fd = self.lock = -1
        self.state = None
        if os.geteuid() != 0:
            raise PermissionError('Fingerprint storage requires root')
        if not isinstance(path, str) or not path.startswith('/'):
            raise StoreError('Absolute private directory required')
        parts = path.split('/')[1:]
        if not parts or any(p in ('', '.', '..') for p in parts):
            raise StoreError('Noncanonical private directory')
        parent = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
        try:
            for part in parts:
                child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=parent)
                os.close(parent)
                parent = child
                s = os.fstat(parent)
                if s.st_uid != 0 or s.st_mode & 0o022:
                    raise StoreError('Unsafe private directory ancestor')
            _private(parent, True)
            self.fd, parent = parent, -1
            self.lock = os.open('lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600, dir_fd=self.fd)
            _private(self.lock)
            fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.state = self._load()
            self._recover()
        except BaseException:
            self.close()
            raise
        finally:
            if parent >= 0:
                os.close(parent)

    def close(self):
        for name in ('lock', 'fd'):
            fd = getattr(self, name, -1)
            if fd >= 0:
                os.close(fd)
                setattr(self, name, -1)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    @staticmethod
    def _identity(uid, username):
        if type(uid) is not int or not 1000 <= uid <= 0xfffffffe:
            raise StoreError('Invalid desktop account ID')
        if not isinstance(username, str) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.-]{0,63}', username):
            raise StoreError('Invalid desktop account name')

    @staticmethod
    def _finger(finger):
        if type(finger) is not int or not 1 <= finger <= 10:
            raise StoreError('Invalid finger identifier')

    @staticmethod
    def _record(record):
        if not isinstance(record, dict) or set(record) != {'uid', 'username', 'finger', 'database'}:
            raise StoreError('Invalid fingerprint record')
        Store._identity(record['uid'], record['username'])
        Store._finger(record['finger'])
        name = record['database']
        match = NAME.fullmatch(name) if isinstance(name, str) else None
        if not match or int(match[1]) != record['uid'] or int(match[2]) != record['finger']:
            raise StoreError('Database does not belong to this account/finger')

    def _load(self):
        try:
            fd = os.open('manifest.json', os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK, dir_fd=self.fd)
        except FileNotFoundError:
            return {'version': 1, 'records': [], 'pending': None, 'retired': []}
        try:
            s = _private(fd)
            if not 0 < s.st_size <= MAX_MANIFEST:
                raise StoreError('Invalid fingerprint manifest size')
            raw = bytearray()
            while len(raw) <= MAX_MANIFEST:
                chunk = os.read(fd, min(4096, MAX_MANIFEST + 1 - len(raw)))
                if not chunk:
                    break
                raw.extend(chunk)
            if len(raw) != s.st_size:
                raise StoreError('Changed fingerprint manifest')
            value = json.loads(raw, object_pairs_hook=_unique_pairs)
        finally:
            os.close(fd)
        if not isinstance(value, dict) or set(value) != {'version', 'records', 'pending', 'retired'} or type(value['version']) is not int or value['version'] != 1:
            raise StoreError('Unsupported fingerprint manifest')
        if not isinstance(value['records'], list) or not isinstance(value['retired'], list) or len(value['records']) > 100:
            raise StoreError('Invalid fingerprint manifest entries')
        seen, names, accounts = set(), set(), {}
        for record in value['records'] + ([value['pending']] if value['pending'] is not None else []):
            self._record(record)
            key = (record['uid'], record['finger'])
            if key in seen or record['database'] in names:
                raise StoreError('Duplicate fingerprint record')
            if record['uid'] in accounts and accounts[record['uid']] != record['username']:
                raise StoreError('Account identity changed')
            seen.add(key)
            names.add(record['database'])
            accounts[record['uid']] = record['username']
        retired = value['retired']
        if len(retired) > 100 or any(not isinstance(n, str) or not NAME.fullmatch(n) or n in names for n in retired) or len(set(retired)) != len(retired):
            raise StoreError('Invalid retired database list')
        return value

    def _save(self):
        data = (json.dumps(self.state, sort_keys=True) + '\n').encode()
        if len(data) > MAX_MANIFEST:
            raise StoreError('Fingerprint manifest full')
        temporary = '.manifest-' + uuid.uuid4().hex
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600, dir_fd=self.fd)
        try:
            _write_all(fd, data)
            os.fsync(fd)
            os.close(fd)
            fd = -1
            os.replace(temporary, 'manifest.json', src_dir_fd=self.fd, dst_dir_fd=self.fd)
            os.fsync(self.fd)
        except BaseException:
            # In-memory state may differ after an I/O failure. Require reopen.
            self.state = None
            raise
        finally:
            if fd >= 0:
                os.close(fd)
            with contextlib.suppress(FileNotFoundError):
                os.unlink(temporary, dir_fd=self.fd)

    def _remove(self, name):
        # Name already validated; unlink the entry, never follow a symlink.
        try:
            s = os.stat(name, dir_fd=self.fd, follow_symlinks=False)
        except FileNotFoundError:
            return
        if not stat.S_ISREG(s.st_mode) or s.st_uid or s.st_mode & 0o077 or s.st_nlink != 1:
            raise StoreError('Unsafe database entry; left untouched')
        os.unlink(name, dir_fd=self.fd)
        os.fsync(self.fd)

    def _recover(self):
        pending = self.state['pending']
        if pending:
            self._remove(pending['database'])
        for name in self.state['retired']:
            self._remove(name)
        if pending or self.state['retired']:
            self.state['pending'] = None
            self.state['retired'] = []
            self._save()

    def list(self, uid, username):
        self._identity(uid, username)
        records = [r for r in self.state['records'] if r['uid'] == uid]
        if any(r['username'] != username for r in records):
            raise StoreError('Account ID was reassigned; explicit cleanup required')
        return [dict(r) for r in records]

    def begin(self, uid, username, finger):
        self._finger(finger)
        existing = self.list(uid, username)
        if self.state['pending'] or any(r['finger'] == finger for r in existing):
            raise StoreError('Enrollment already exists or is in progress')
        if len(self.state['records']) >= 100:
            raise StoreError('Fingerprint manifest full')
        record = dict(uid=uid, username=username, finger=finger,
                      database=f'u{uid}-f{finger}-{uuid.uuid4().hex}.db')
        self.state['pending'] = record
        self._save()
        return dict(record)

    def commit(self, database):
        pending = self.state['pending']
        if pending is None or pending['database'] != database:
            raise StoreError('No matching enrollment transaction')
        fd = os.open(database, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK, dir_fd=self.fd)
        try:
            s = _private(fd)
            if not 0 < s.st_size <= MAX_DB:
                raise StoreError('Invalid opaque database size')
            os.fsync(fd)
        finally:
            os.close(fd)
        self.state['records'].append(pending)
        self.state['pending'] = None
        self._save()

    def cancel(self):
        self._recover()

    def delete(self, uid, username, finger):
        self._finger(finger)
        if self.state['pending']:
            raise StoreError('Enrollment is in progress')
        selected = [r for r in self.list(uid, username) if r['finger'] == finger]
        if not selected:
            return False
        record = selected[0]
        self.state['records'].remove(record)
        self.state['retired'].append(record['database'])
        self._save()  # revoke lookup before deletion; resume cleanup on reopen
        self._recover()
        return True
