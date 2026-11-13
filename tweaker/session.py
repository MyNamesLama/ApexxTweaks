"""Session-owned, transactional changes. No game-process manipulation."""
import uuid

class GamingSession:
    def __init__(self, engine):
        self.engine=engine
        self.active=None
        self.seen=False
        self.absent_polls=0

    def start(self, ids):
        if self.active: raise RuntimeError('Gaming Mode already active')
        if not ids: raise ValueError('Select at least one session-safe action first')
        if len(ids)!=len(set(ids)): raise ValueError('Duplicate session actions')
        if any(not self.engine.actions[k].session_safe for k in ids):
            raise ValueError('Selection includes a persistent-only action; apply it separately')
        self.active=str(uuid.uuid4()); self.seen=False; self.absent_polls=0
        results=[]
        try:
            for key in ids: results.append(self.engine.apply(key,session_id=self.active))
        except Exception as error:
            try: self.end()
            except Exception as rollback:
                raise RuntimeError(f'Session start failed: {error}. Rollback needs recovery: {rollback}') from error
            raise
        return results

    def end(self):
        if not self.active: return
        failures=[]
        for record in reversed(self.engine.records):
            if record.get('session')==self.active and record['status']!='restored':
                try: self.engine.restore(record)
                except Exception as error: failures.append(str(error))
        if failures: raise RuntimeError('Session recovery required: '+'; '.join(failures))
        self.active=None

    def observe(self, running):
        """Two absent polls after a detected run tolerate brief game restarts."""
        if not self.active: return False
        if running:
            self.seen=True; self.absent_polls=0
        elif self.seen:
            self.absent_polls+=1
            if self.absent_polls>=2:
                self.end(); return True
        return False
