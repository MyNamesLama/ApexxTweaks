"""Native Windows CI test touches only a disposable current-user test key."""
import os
import unittest
import uuid
from tweaker.windows_controls import reg_read, reg_write, ABSENT

@unittest.skipUnless(os.name=='nt','Requires Windows registry; never tests machine/game settings')
class NativeRegistryRoundtrip(unittest.TestCase):
    def test_unicode_value_and_absence(self):
        import winreg
        key='Software\\FrameWiseTests\\'+uuid.uuid4().hex
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER,key): pass
        try:
            self.assertEqual(reg_read(key,'fixture'),ABSENT)
            original={'exists':True,'type':1,'value':'Unicode ä ✓ "C:\\my app.exe"'}
            reg_write(key,'fixture',original); self.assertEqual(reg_read(key,'fixture'),original)
            reg_write(key,'fixture',ABSENT); self.assertEqual(reg_read(key,'fixture'),ABSENT)
            original={'exists':True,'type':4,'value':0}
            reg_write(key,'fixture',original); self.assertEqual(reg_read(key,'fixture'),original)
            reg_write(key,'fixture',ABSENT)
        finally: winreg.DeleteKey(winreg.HKEY_CURRENT_USER,key)


@unittest.skipUnless(os.name=='nt','Requires Windows APIs; tests only the current test-runner process')
class NativeProcessRoundtrip(unittest.TestCase):
    def test_qos_flags_restored_for_test_runner_only(self):
        import sys
        from unittest.mock import patch
        from tweaker.discovery import creation_time
        from tweaker.targets import encode, PUBLISHERS
        from tweaker.windows_controls import eco
        # Test-only allowlist extension never ships in product policy. No game or
        # other user app is touched; signature validation is tested separately.
        import ntpath
        target=encode('eco',pid=os.getpid(),created=str(creation_time(os.getpid())),path=sys.executable)
        with patch.dict(PUBLISHERS,{ntpath.basename(sys.executable).lower():'Test runner'}),patch('tweaker.windows_controls.signature'):
            original=eco(target)
            try:
                desired={'control':original['control']|1,'state':original['state']|1}
                eco(target,desired)
                self.assertEqual(eco(target),desired)
            finally: eco(target,original)
            self.assertEqual(eco(target),original)
    def test_creation_time_mismatch_never_writes(self):
        import sys
        import ntpath
        from unittest.mock import patch
        from tweaker.discovery import creation_time
        from tweaker.targets import encode, PUBLISHERS
        from tweaker.windows_controls import eco, ProcessExpired
        target=encode('eco',pid=os.getpid(),created=str(creation_time(os.getpid())+1),path=sys.executable)
        with patch.dict(PUBLISHERS,{ntpath.basename(sys.executable).lower():'Test runner'}),patch('tweaker.windows_controls.signature'):
            with self.assertRaises(ProcessExpired): eco(target,{'control':1,'state':1})
