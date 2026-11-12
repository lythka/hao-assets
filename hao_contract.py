#!/usr/bin/env python3
"""hao-contract: the interfaces between the research, runtime and patcher repositories, checked (workflow plan step 3).

  hao_contract.py check REPO            run the checks REPO/contract.json names; one line per problem, exit 1
  hao_contract.py lock REPO GLOB... --os-build B [--cache-uuid U] [--format F]
                                        print a generated.lock for the files GLOB matches (review, then commit)
  hao_contract.py stamps REPO GLOB...   the OS build stamped in each generated file's header

REPO/contract.json: {"contract_version": 1, "role": "research" | "runtime" | "patcher", "checks": [...]}, where a
check is one of
  {"kind": "hygiene", "allow": {PATH: [PATTERN LABELS]}, "commits": N}
        no tracked file (and none of the last N commit messages) names a private location
  {"kind": "generated-lock", "lock": "generated.lock", "globs": ["src/*_gen.inc"]}
        every file the globs match is listed with its sha256, every listed file matches, and a file whose
        header stamps an OS build must stamp the entry's os_build (the 26B131-rows-under-a-26A428-stamp case)
  {"kind": "payload", "manifest": PATH, "os_build": B, "layout_version": N}
        a hao-runtime payload-manifest.json: clean, the declared OS build and install-layout version, and every
        listed file present with its sha256
Standard library only, so each repo can vendor a pinned copy.
"""
import fnmatch
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

CONTRACT_VERSION = 1
# Built from parts so this file does not match itself.
PRIVATE = [
    ('private research repository', re.compile(re.escape('hao-' 'research'))),
    ('private evidence folder', re.compile(re.escape('store/' 'evidence'))),
    ('archived private tooling', re.compile(re.escape('ssd-tools-' 'archive'))),
    ('home folder', re.compile('/' r'Users/(?!Shared\b)[A-Za-z]')),
]
STAMP = re.compile(r'\b(\d{2}[A-Z]\d{2,4}[a-z]?)\)')
LOCK_FIELDS = ('path', 'sha256', 'export_id', 'os_build', 'cache_uuid', 'format')
PAYLOAD_FIELDS = ('version', 'commit', 'clean', 'os_build', 'cache_uuid', 'units_version', 'units_sha256',
                  'layout_version', 'files')


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def tracked(repo):
    out = subprocess.run(['git', '-C', str(repo), 'ls-files', '-z'], capture_output=True, check=True).stdout
    return [n for n in out.decode().split('\0') if n]


def stamp_of(path):
    with open(path, 'rb') as f:
        head = f.read(512).decode('utf8', 'replace').splitlines()[:3]
    for line in head:
        m = STAMP.search(line)
        if m:
            return m.group(1)
    return None


def check_hygiene(repo, c):
    bad = []
    allow = c.get('allow', {})
    for name in tracked(repo):
        path = Path(repo) / name
        if path.is_symlink() or not path.is_file():
            continue
        data = path.read_bytes()
        if b'\0' in data[:8192]:
            continue
        text = data.decode('utf8', 'replace')
        for label, pattern in PRIVATE:
            if label in allow.get(name, []):
                continue
            for n, line in enumerate(text.splitlines(), 1):
                if pattern.search(line):
                    bad.append('hygiene: %s:%d names a %s' % (name, n, label))
                    break
    n = c.get('commits', 0)
    if n:
        log = subprocess.run(['git', '-C', str(repo), 'log', '-%d' % n, '--format=%h%x00%B%x1e'],
                             capture_output=True, text=True, check=True).stdout
        for entry in filter(str.strip, log.split('\x1e')):
            h, _, body = entry.strip().partition('\0')
            for label, pattern in PRIVATE:
                if pattern.search(body):
                    bad.append('hygiene: commit %s message names a %s' % (h, label))
    return bad


def check_lock(repo, c):
    repo = Path(repo)
    lock_path = repo / c.get('lock', 'generated.lock')
    if not lock_path.is_file():
        return ['generated-lock: %s is missing' % lock_path.name]
    try:
        lock = json.loads(lock_path.read_text())
    except ValueError as x:
        return ['generated-lock: %s is not JSON (%s)' % (lock_path.name, x)]
    bad, listed = [], {}
    for e in lock.get('files', []):
        missing = [f for f in LOCK_FIELDS if f not in e]
        if missing:
            bad.append('generated-lock: %s lacks %s' % (e.get('path', '?'), ', '.join(missing)))
            continue
        listed[e['path']] = e
        p = repo / e['path']
        if not p.is_file():
            bad.append('generated-lock: %s is listed but missing' % e['path'])
            continue
        if sha256(p) != e['sha256']:
            bad.append('generated-lock: %s differs from its locked sha256 (edited by hand, or not re-exported)'
                       % e['path'])
        stamp = stamp_of(p)
        if stamp and stamp != e['os_build']:
            bad.append('generated-lock: %s is stamped %s but locked as %s' % (e['path'], stamp, e['os_build']))
    for name in tracked(repo):
        if any(fnmatch.fnmatch(name, g) for g in c.get('globs', [])) and name not in listed:
            bad.append('generated-lock: %s is generated but not in %s' % (name, lock_path.name))
    return bad


def check_payload(repo, c):
    path = Path(repo) / c['manifest'] if not os.path.isabs(c['manifest']) else Path(c['manifest'])
    if not path.is_file():
        return ['payload: %s is missing' % path]
    m = json.loads(path.read_text())
    bad = ['payload: manifest lacks %s' % f for f in PAYLOAD_FIELDS if f not in m]
    if bad:
        return bad
    if m['clean'] is not True:
        bad.append('payload: built from a dirty tree')
    if m['os_build'] != c['os_build']:
        bad.append('payload: OS build %s, the patcher declares %s' % (m['os_build'], c['os_build']))
    if m['layout_version'] != c['layout_version']:
        bad.append('payload: install-layout version %s, the patcher declares %s' % (m['layout_version'],
                                                                                   c['layout_version']))
    root = path.parent
    for rel, digest in sorted(m['files'].items()):
        f = root / rel
        if not f.is_file():
            bad.append('payload: %s is listed but missing' % rel)
        elif sha256(f) != digest:
            bad.append('payload: %s does not match its sha256' % rel)
    return bad


CHECKS = {'hygiene': check_hygiene, 'generated-lock': check_lock, 'payload': check_payload}


def check(repo):
    contract = Path(repo) / 'contract.json'
    if not contract.is_file():
        return ['%s has no contract.json' % repo]
    c = json.loads(contract.read_text())
    if c.get('contract_version') != CONTRACT_VERSION:
        return ['contract.json: contract_version %s, this checker is %d' % (c.get('contract_version'), CONTRACT_VERSION)]
    bad = []
    for item in c.get('checks', []):
        fn = CHECKS.get(item.get('kind'))
        bad += fn(repo, item) if fn else ['contract.json: unknown check %r' % item.get('kind')]
    return bad


def main(argv):
    if len(argv) >= 2 and argv[0] == 'check':
        bad = check(argv[1])
        print('\n'.join(bad) or 'hao-contract: %s keeps its contract' % argv[1])
        return 1 if bad else 0
    if len(argv) >= 3 and argv[0] == 'stamps':
        repo = Path(argv[1])
        for name in sorted(n for n in tracked(repo) if any(fnmatch.fnmatch(n, g) for g in argv[2:])):
            print('%-12s %s' % (stamp_of(repo / name) or '-', name))
        return 0
    if len(argv) >= 3 and argv[0] == 'lock' and '--os-build' in argv:
        opts = {argv[i]: argv[i + 1] for i in range(len(argv) - 1) if argv[i].startswith('--')}
        repo = Path(argv[1])
        globs = [a for a in argv[2:] if not a.startswith('--') and a not in opts.values()]
        files = []
        for name in sorted(n for n in tracked(repo) if any(fnmatch.fnmatch(n, g) for g in globs)):
            files.append({'path': name, 'sha256': sha256(repo / name), 'export_id': None,
                          'os_build': opts['--os-build'], 'cache_uuid': opts.get('--cache-uuid'),
                          'format': opts.get('--format')})
        print(json.dumps({'lock_version': 1, 'files': files}, indent=1))
        return 0
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
