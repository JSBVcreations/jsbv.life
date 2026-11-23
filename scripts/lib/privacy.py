"""The one privacy check for everything the public repo would publish. Stdlib only.

    from lib.privacy import check_public
    problems = check_public()      # [] when clean

It looks at every file git would commit (tracked, plus new files that .gitignore doesn't hide) and flags:
  - text that looks like a phone number, an email address or an IP address (in JSON strings, and in page/doc text)
  - JSON keys that only raw exports carry (Spotify's ip_addr, Strava's polyline/description, "with", "number"...)
  - a private dataset (meta-log/data/privacy.json) showing up in plain form in daily.json, its shards or summary.json
  - any phone number or call-log name from jsbv data/ATT/phone-people.json, when that file is on this machine
  - a workbook, CSV, PDF, zip or database file that git would commit
Rules and the known false positives (with why) live in scripts/config/public-check.json.
A problem names the file, where in it, and what kind of thing it is. It never prints the matched value itself.
"""
import fnmatch
import hashlib
import json
import os
import re
import subprocess

from .paths import ROOT, DATA, repo

PHONE = re.compile(r'(?<![\d.])(?:\+?1[\s.\-]?)?\(?\d{3}\)?[\s.\-]\d{3}[\s.\-]\d{4}(?![\d.])')
EMAIL = re.compile(r'[\w.+-]+@[A-Za-z0-9-]+\.[A-Za-z]{2,}')
IPV4 = re.compile(r'(?<![\d.])(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)(?![\d.])')
RAW_EXT = ('.sqlite', '.db', '.xlsx', '.xlsm', '.numbers', '.csv', '.pdf', '.zip')   # never committed, whatever .gitignore says
TEXT_EXT = ('.json', '.html', '.js', '.css', '.md', '.txt', '.py', '.command', '.svg', '.xml', '.webmanifest')


def digest(s):
    """How an allow rule names a value without spelling it out (first 12 hex of sha256)."""
    return hashlib.sha256(s.encode('utf-8')).hexdigest()[:12]


def committable():
    r = subprocess.run(['git', 'ls-files', '-co', '--exclude-standard'], cwd=ROOT, stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, universal_newlines=True)
    if r.returncode != 0:      # no git = no way to know what would be committed: never report "clean" for that
        raise SystemExit(f'privacy check: git could not list the files ({r.stderr.strip()[:120]}); run it inside the repo')
    return [f for f in r.stdout.split('\n') if f and os.path.isfile(repo(f))]


def public_files():
    return sorted(f for f in committable() if f.endswith(TEXT_EXT))


def local_terms():
    """Numbers and names from the private phone key, if this machine has it. Kept in memory only."""
    p = os.path.join(DATA, 'ATT', 'phone-people.json')
    if not os.path.isfile(p):
        return []
    try:
        key = json.load(open(p, encoding='utf-8'))
    except (OSError, ValueError):
        return []
    terms = set()
    for num, rec in key.items():
        n = num[6:].split('@')[0] if num.startswith('email:') else num
        if len(n) >= 7: terms.add(('call-log number', n))
        for nm in [rec.get('name')] + list((rec.get('name_votes') or {}).keys()):
            if nm and len(nm.strip()) >= 4: terms.add(('call-log name', nm.strip()))
    return sorted(terms)


class Checker:
    def __init__(self, rules, terms):
        self.keys = {k.lower() for k in rules['keys']}
        self.allow = rules['allow']
        self.private = set(rules.get('private_ids', []))
        self.terms = [(kind, t, re.compile(r'(?<![\w])' + re.escape(t) + r'(?![\w])')) for kind, t in terms]
        self.out = []

    def allowed(self, f, kind, where, value):
        for a in self.allow:
            if not fnmatch.fnmatch(f, a['file']): continue
            if a.get('kind') and a['kind'] != kind: continue
            if 'key' in a and not where.endswith('.' + a['key']): continue
            if 'text' in a and a['text'] != value: continue
            if 'sha' in a and a['sha'] != digest(value): continue
            return True
        return False

    def flag(self, f, kind, where, value):
        if not self.allowed(f, kind, where, value):
            self.out.append({'file': f, 'where': where, 'kind': kind, 'sha': digest(value)})

    def text(self, f, where, s):
        for kind, rx in (('phone number', PHONE), ('email address', EMAIL), ('IP address', IPV4)):
            for m in rx.finditer(s):
                self.flag(f, kind, where, m.group(0))
        for kind, t, rx in self.terms:
            if t in s and rx.search(s):
                self.flag(f, kind, where, t)

    def walk(self, f, o, where):
        if isinstance(o, dict):
            for k, v in o.items():
                w = where + '.' + k
                if k.lower() in self.keys: self.flag(f, 'raw-export key', w, k)
                self.text(f, w + ' (key)', k)
                self.walk(f, v, w)
        elif isinstance(o, list):
            for v in o:
                self.walk(f, v, where + '[]')
        elif isinstance(o, str):
            self.text(f, where, o)

    def file(self, f):
        try:
            raw = open(repo(f), encoding='utf-8').read()
        except (OSError, UnicodeDecodeError):
            return
        if f.endswith('.json'):
            try:
                o = json.loads(raw)
            except ValueError:
                self.out.append({'file': f, 'where': '', 'kind': 'not valid JSON', 'sha': ''}); return
            self.walk(f, o, '')
            self.plain_private(f, o)
        else:
            for i, line in enumerate(raw.split('\n'), 1):
                self.text(f, f'line {i}', line)

    def plain_private(self, f, o):
        """Sealed datasets may only leave as private.enc.json."""
        if not isinstance(o, dict): return
        ids = []
        if isinstance(o.get('datasets'), list):
            ids = [d.get('id') for d in o['datasets'] if isinstance(d, dict)]
        elif f.startswith('meta-log/data/days/') and isinstance(o.get('id'), str):
            ids = [o['id']]
        for i in ids:
            if i in self.private: self.out.append({'file': f, 'where': '.datasets', 'kind': 'private dataset in plain form', 'sha': digest(i)})


def check_public(files=None):
    rules = json.load(open(repo('scripts', 'config', 'public-check.json'), encoding='utf-8'))
    try:
        rules['private_ids'] = json.load(open(repo('meta-log', 'data', 'privacy.json'), encoding='utf-8'))['private']
    except (OSError, ValueError, KeyError):
        rules['private_ids'] = []
    skip = rules.get('skip', [])
    c = Checker(rules, local_terms())
    if not files:
        for f in committable():
            if f.lower().endswith(RAW_EXT):
                c.out.append({'file': f, 'where': '', 'kind': 'raw export or database file', 'sha': ''})
    for f in files or public_files():
        if not any(fnmatch.fnmatch(f, s) for s in skip):
            c.file(f)
    return c.out


def report(problems, limit=40):
    lines = [f"  {p['kind']:30} {p['file']}  {p['where'][:80]}" + (f"  (sha {p['sha']})" if p['sha'] else '') for p in problems[:limit]]
    if len(problems) > limit: lines.append(f'  ... and {len(problems) - limit} more')
    return '\n'.join(lines)
