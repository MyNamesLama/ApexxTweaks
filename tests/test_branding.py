"""Brand rename must not orphan any prior configuration or rollback journal."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from tweaker.branding import APP_NAME, LEGACY_APP_NAME, JOURNAL_MUTEX, OPTIONAL_TASK_PATHS, data_directory, branded_text
from tweaker.engine import Engine
from tweaker.platform import MockBackend
from tweaker.actions import optional_action
from tweaker.targets import encode, identifier
from tweaker.windows_controls import task_read


class BrandingCompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name)

    def test_fresh_install_uses_exact_name(self):
        self.assertEqual(APP_NAME,'ApexxTweaks')
        self.assertEqual(data_directory(self.base),self.base/'ApexxTweaks')
        self.assertFalse(data_directory(self.base).exists())

    def test_legacy_data_reused_without_modification(self):
        legacy=self.base/LEGACY_APP_NAME; legacy.mkdir()
        files={'benchmarks.json':json.dumps({'Before':[{'average_fps':100}],'After':[]}),
               'preferences.json':'{"test":"keep"}','events.log':'previous log'}
        for name,content in files.items(): (legacy/name).write_text(content)
        self.assertEqual(data_directory(self.base),legacy)
        for name,content in files.items(): self.assertEqual((legacy/name).read_text(),content)
        self.assertFalse((self.base/APP_NAME).exists())

    def test_legacy_journal_and_snapshot_paths_survive_restore(self):
        backend=MockBackend(); old=Engine(backend,self.base/LEGACY_APP_NAME)
        original=backend.read('power'); old.apply('power.high')
        stored_path=old.records[0]['backup']
        snapshot=Path(stored_path)/'snapshot.json'; original_snapshot=snapshot.read_bytes()
        before=old.path.read_bytes()
        recovered=Engine(backend,data_directory(self.base))
        self.assertEqual(recovered.path.read_bytes(),before)
        self.assertEqual(recovered.records[0]['backup'],stored_path)
        recovered.restore_all()
        self.assertEqual(backend.read('power'),original)
        self.assertEqual(snapshot.read_bytes(),original_snapshot)
        self.assertEqual(recovered.records[0]['status'],'restored')

    def test_legacy_task_action_identity_preserved(self):
        backend=MockBackend(); old=Engine(backend,self.base/LEGACY_APP_NAME)
        target=encode('task',path=OPTIONAL_TASK_PATHS[1],name='Optional Music',fingerprint='unchanged')
        original={'enabled':True,'fingerprint':'unchanged'}
        action=optional_action('task',target,'Optional Music',{'enabled':False,'fingerprint':'unchanged'})
        backend.values[target]=original; old.register([action]); old.apply(action.id)
        old.records[0]['definition']['description']=LEGACY_APP_NAME+' optional task'
        old.save()
        recovered=Engine(backend,data_directory(self.base))
        self.assertEqual(recovered.records[0]['target'],target)
        self.assertEqual(action.id,identifier('task',target))
        self.assertIn(APP_NAME,branded_text(recovered.actions[action.id].description))
        recovered.restore_all(); self.assertEqual(backend.read(target),original)

    def test_discovery_can_refresh_renamed_metadata_without_rewriting_journal(self):
        from dataclasses import replace
        target=encode('startup',name='Music',command='fixture')
        old_action=optional_action('startup',target,LEGACY_APP_NAME+' action',{'exists':False})
        backend=MockBackend(); backend.values[target]={'exists':True,'type':1,'value':'fixture'}
        engine=Engine(backend,self.base/LEGACY_APP_NAME)
        engine.register([old_action]); engine.apply(old_action.id)
        original_journal=engine.path.read_bytes()
        renamed=replace(old_action,title=APP_NAME+' action')
        engine.register([renamed])
        self.assertEqual(engine.actions[renamed.id].title,APP_NAME+' action')
        self.assertEqual(engine.path.read_bytes(),original_journal)
        with self.assertRaises(ValueError): engine.register([replace(renamed,target='different')])
        engine.restore_all()

    def test_both_task_namespaces_pass_same_validation(self):
        xml='''<Task xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task"><Principals><Principal><UserId>S-1-test</UserId><LogonType>InteractiveToken</LogonType><RunLevel>LeastPrivilege</RunLevel></Principal></Principals><Settings><Enabled>true</Enabled></Settings><Actions><Exec><Command>C:\\Apps\\Spotify.exe</Command></Exec></Actions></Task>'''
        from tweaker.windows_controls import task_definition
        fingerprint=task_definition(xml,'S-1-test')[2]
        with patch('tweaker.platform.psjson',return_value={'xml':xml,'sid':'S-1-test'}) as query:
            for namespace in OPTIONAL_TASK_PATHS:
                target=encode('task',path=namespace,name='Music',fingerprint=fingerprint)
                self.assertEqual(task_read(target),{'enabled':True,'fingerprint':fingerprint})
                self.assertIn(namespace,query.call_args.args[0])
        with self.assertRaises(ValueError):
            task_read(encode('task',path='\\ApexxTweaksOptional\\Other\\',name='Music',fingerprint=fingerprint))

    def test_two_populated_stores_refused_without_changes(self):
        for name in (APP_NAME,LEGACY_APP_NAME):
            folder=self.base/name; folder.mkdir(); (folder/'history.json').write_text('[]')
        before={p:p.read_bytes() for p in self.base.glob('*/history.json')}
        with self.assertRaisesRegex(RuntimeError,'Two populated'):
            data_directory(self.base)
        self.assertEqual(before,{p:p.read_bytes() for p in before})

    def test_empty_current_store_does_not_hide_legacy_data(self):
        (self.base/APP_NAME).mkdir()
        legacy=self.base/LEGACY_APP_NAME; legacy.mkdir(); (legacy/'events.log').write_text('keep')
        self.assertEqual(data_directory(self.base),legacy)

    def test_empty_legacy_store_does_not_hide_current_data(self):
        (self.base/LEGACY_APP_NAME).mkdir()
        current=self.base/APP_NAME; current.mkdir(); (current/'history.json').write_text('[]')
        self.assertEqual(data_directory(self.base),current)

    def test_environment_location_and_shared_legacy_mutex(self):
        with patch.dict(os.environ,{'LOCALAPPDATA':str(self.base)}):
            self.assertEqual(data_directory(),self.base/APP_NAME)
        self.assertEqual(JOURNAL_MUTEX,'Local\\'+LEGACY_APP_NAME+'Journal')
