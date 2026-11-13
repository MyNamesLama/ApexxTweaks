"""JSON target descriptors and strict optional-app policy, shared with mock tests."""
import hashlib
import json
import ntpath
import re

# No shell hosts, launchers, updaters, browsers or system components.
PUBLISHERS = {'spotify.exe': 'Spotify AB', 'discord.exe': 'Discord Inc.'}
RUN_KEY = r'Software\Microsoft\Windows\CurrentVersion\Run'

def encode(kind, **fields):
    return kind + ':' + json.dumps(fields, sort_keys=True, separators=(',', ':'))

def decode(target, kind):
    if not target.startswith(kind + ':'): raise ValueError('Unexpected target kind')
    value = json.loads(target[len(kind)+1:])
    if not isinstance(value, dict): raise ValueError('Invalid target')
    return value

def identifier(kind, target):
    return kind + '.' + hashlib.sha256(target.encode()).hexdigest()[:20]

def executable(command):
    """Accept only an unambiguous absolute .exe, never shell expansion or scripts."""
    command = command.strip()
    pattern = r'^"([^"\r\n]+\.exe)"(?:\s+(.*))?$' if command.startswith('"') else r'^([^\s"\r\n]+\.exe)(?:\s+(.*))?$'
    match = re.fullmatch(pattern, command, flags=re.I)
    if not match: raise ValueError('Ambiguous startup command; use the application settings instead')
    path, args = match.group(1), match.group(2) or ''
    if not re.match(r'^[A-Za-z]:\\', path) or '%' in path or '..' in path.split('\\'):
        raise ValueError('Only absolute local executable paths are supported')
    if ntpath.basename(path).lower() not in PUBLISHERS:
        raise ValueError('Not an approved optional application')
    # Only ordinary startup switches; exclude updater/script/external program dispatch.
    if args and not re.fullmatch(r'(?:--(?:start-minimized|minimized|autostart)(?:\s+|$))*', args):
        raise ValueError('Unsupported startup arguments; no change permitted')
    return ntpath.normpath(path)

def approved_image(path, status, subject):
    name = ntpath.basename(path).lower()
    expected = PUBLISHERS.get(name)
    # Match a certificate subject organization/CN exactly, not a substring vendor name.
    fields = re.findall(r'(?:^|,\s*)(?:O|CN)=(?:"([^"]+)"|([^,]+))', subject or '')
    identities = {a or b.strip() for a,b in fields}
    return bool(expected and status == 'Valid' and expected in identities)

def classify_inventory(data):
    """Recommendations are review candidates, never automatic removal decisions."""
    result = {'startup': [], 'tasks': [], 'processes': [], 'note': 'Unknown entries remain read-only. No unused-app claim can be inferred from a name.'}
    for row in data.get('startup', []) or []:
        item = dict(row); item['recommendation'] = 'Review manually; unknown/system/launcher entries are not actionable.'
        try:
            executable(str(row.get('Command','')))
            item['recommendation'] = 'Optional app candidate; signature and current-user Run location must pass before an action is offered. Takes effect next sign-in.'
        except ValueError: pass
        result['startup'].append(item)
    for row in data.get('tasks', []) or []:
        item = dict(row)
        item['recommendation'] = 'Read-only: keep update, security and unknown tasks enabled.'
        result['tasks'].append(item)
    for row in data.get('processes', []) or []:
        item = dict(row)
        item['recommendation'] = ('Optional EcoQoS candidate; user confirmation and signed image validation required.'
                                  if str(row.get('Name','')).lower().split('#')[0].removesuffix('.exe') in ('spotify','discord')
                                  else 'Read-only; no process changes offered.')
        result['processes'].append(item)
    return result
