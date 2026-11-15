#!/usr/bin/env python3
"""Encrypt private datasets so they can live in this PUBLIC repo without being readable.

The repo on GitHub is public, so anything committed is public. Private datasets (ids listed in
meta-log/data/privacy.json) are written only as meta-log/data/private.enc.json: AES-256-GCM, key from the
passphrase by PBKDF2-SHA256 (600,000 rounds). The home page asks for the passphrase and decrypts in the browser
(WebCrypto); nothing is sent anywhere.

Key file (OUTSIDE the repo): $JSBV_KEY_FILE, default ~/Documents/00-Database/jsbv data/jsbv-private-key.txt
    line 1: the passphrase      line 2: the salt (base64; made once, keep it so "remember this device" keeps working)
Run this script on its own to create the key file with a random passphrase (it never overwrites one):
    python3 scripts/private_box.py --init
Needs:  pip3 install cryptography
"""
import base64
import json
import os
import secrets
import sys

ITER = 600_000
HOME = os.path.expanduser('~')
KEY_FILE = os.environ.get('JSBV_KEY_FILE') or os.path.join(
    os.environ.get('JSBV_DATA') or os.path.join(HOME, 'Documents', '00-Database', 'jsbv data'), 'jsbv-private-key.txt')
b64 = lambda b: base64.b64encode(b).decode('ascii')


def read_key():
    """(passphrase, salt bytes) or None when there is no key file."""
    if not os.path.exists(KEY_FILE): return None
    lines = [ln.strip() for ln in open(KEY_FILE, encoding='utf-8').read().splitlines() if ln.strip() and not ln.startswith('#')]
    if len(lines) < 2: sys.exit(f'{KEY_FILE}: needs the passphrase on one line and the salt on the next')
    return lines[0], base64.b64decode(lines[1])


def seal(obj):
    """obj -> the JSON-able envelope, or None when there is no key file."""
    k = read_key()
    if not k: return None
    try:
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    except ImportError:
        print('private  needs:  pip3 install cryptography   (private datasets left out until then)'); return None
    pw, salt = k
    key = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=ITER).derive(pw.encode('utf-8'))
    iv = secrets.token_bytes(12)
    ct = AESGCM(key).encrypt(iv, json.dumps(obj, separators=(',', ':'), ensure_ascii=False).encode('utf-8'), None)
    return {'v': 1, 'alg': 'AES-GCM', 'kdf': 'PBKDF2-SHA256', 'iter': ITER, 'salt': b64(salt), 'iv': b64(iv), 'ct': b64(ct)}


def init():
    if os.path.exists(KEY_FILE):
        print(f'key file already exists: {KEY_FILE} (not changed)'); return
    words = '-'.join(secrets.token_urlsafe(6) for _ in range(4))
    os.makedirs(os.path.dirname(KEY_FILE), exist_ok=True)
    with open(KEY_FILE, 'w', encoding='utf-8') as f:
        f.write('# jsbv.life private-data key. Keep this file OUT of the repo. Line 1 = passphrase (change it if you like,\n'
                '# then run Update and unlock again). Line 2 = salt (leave it).\n' + words + '\n' + b64(secrets.token_bytes(16)) + '\n')
    os.chmod(KEY_FILE, 0o600)
    print(f'created {KEY_FILE}')


if __name__ == '__main__':
    if sys.argv[1:] == ['--init']: init()
    else: sys.exit(__doc__)
