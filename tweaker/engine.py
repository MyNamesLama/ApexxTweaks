import json
import os
import time
import uuid
from pathlib import Path
from dataclasses import asdict
from .windows_controls import ProcessExpired
from .actions import ACTIONS, Action

def atomic_json(path, data):
    temp = path.with_suffix('.tmp')
    with open(temp, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp, path)

class Engine:
    def __init__(self, backend, root):
        self.backend = backend
        self.actions = dict(ACTIONS)
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / 'history.json'
        self.records = json.loads(self.path.read_text()) if self.path.exists() else []
        if not isinstance(self.records, list):
            raise RuntimeError('Invalid journal; preserve backups and repair before changing settings.')
        for record in self.records:
            if record.get('status') != 'restored' and record.get('definition') and record['action'] not in self.actions:
                action=Action(**record['definition'])
                if action.id!=record['action'] or action.target!=record['target'] or action.desired!=record['desired']:
                    raise RuntimeError('Journal action definition mismatch; preserve backups before recovery.')
                self.actions[action.id]=action

    def save(self): atomic_json(self.path, self.records)
    def log(self, message):
        with open(self.root / 'events.log', 'a', encoding='utf-8') as f:
            f.write(f'{time.strftime("%Y-%m-%dT%H:%M:%S%z")} {message}\n')

    def register(self, actions):
        for action in actions:
            if action.id in self.actions and self.actions[action.id] != action:
                raise ValueError('Action identity collision')
            self.actions[action.id] = action

    def apply(self, action_id, session_id=None):
        action = self.actions[action_id]
        conflicts = lambda target: target == action.target or {target,action.target} == {'power','ac-mode'}
        if any(conflicts(r['target']) and r['status'] != 'restored' for r in self.records):
            raise RuntimeError('Target already owned by another action; restore it before applying.')
        if any(r['action'] == action_id and r['status'] != 'restored' for r in self.records):
            raise RuntimeError('Restore the existing or interrupted action first.')
        if hasattr(self.backend,'prepare'): self.backend.prepare(action)
        original = self.backend.read(action.target)
        if original == action.desired:
            return 'Already configured; no backup or change needed.'
        folder = self.root / str(uuid.uuid4())
        folder.mkdir()
        self.backend.backup(action.target, folder)
        record = dict(action=action.id, target=action.target, original=original,
                      desired=action.desired, status='pending', timestamp=time.time(), backup=str(folder),
                      definition=asdict(action), session=session_id)
        atomic_json(folder / 'snapshot.json', record)
        self.records.append(record)
        self.save()  # Write-ahead journal: recovery includes interrupted writes.
        try:
            if hasattr(self.backend,'prepare'): self.backend.prepare(action)
            if self.backend.read(action.target) != original:
                raise RuntimeError('Configuration changed during backup; no write attempted.')
            self.backend.write(action.target, action.desired)
            if self.backend.read(action.target) != action.desired:
                raise RuntimeError('Verification failed')
            record['status'] = 'applied'
            self.save()
            self.log(f'Applied {action.id}')
            return 'Applied and verified.'
        except Exception as error:
            record['status'] = 'recovery_required'
            record['error'] = str(error)
            self.save()
            self.log(f'Apply failed {action.id}: {error}')
            raise

    def restore(self, record, force=False):
        try:
            current = self.backend.read(record['target'])
        except ProcessExpired:
            if not record['target'].startswith('eco:'): raise
            record['status'] = 'restored'
            record['restore_note'] = 'Original optional process exited; no write to a reused PID.'
            self.save()
            self.log('Expired process restored by lifetime: ' + record['action'])
            return
        if current not in (record['desired'], record['original']) and not force:
            raise RuntimeError('Setting changed outside FrameWise; restore refused to avoid overwriting it.')
        if current != record['original']:
            self.backend.write(record['target'], record['original'])
        if self.backend.read(record['target']) != record['original']:
            raise RuntimeError('Restore verification failed')
        record['status'] = 'restored'
        self.save()
        self.log('Restored ' + record['action'])

    def restore_all(self):
        errors = []
        for record in reversed(self.records):
            if record['status'] != 'restored':
                try: self.restore(record)
                except Exception as e: errors.append(f"{record['action']}: {e}")
        if errors: raise RuntimeError('\n'.join(errors))
