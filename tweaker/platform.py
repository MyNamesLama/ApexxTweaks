import json
import os
import platform
import subprocess
import re
import base64

WINDOWS = os.name == 'nt'

def run(args, timeout=30, encoding=None):
    result = subprocess.run(args, capture_output=True, text=True, timeout=timeout, encoding=encoding,
                            creationflags=0x08000000 if WINDOWS else 0)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or f'Command failed: {args[0]}')
    return result.stdout.strip()

def powershell(script):
    if not WINDOWS:
        raise RuntimeError('Windows required; no system changes were made.')
    prefix = "$ErrorActionPreference='Stop'; [Console]::OutputEncoding=[System.Text.UTF8Encoding]::new($false); $OutputEncoding=[Console]::OutputEncoding; "
    encoded = base64.b64encode((prefix + script).encode('utf-16le')).decode('ascii')
    return run(['powershell.exe', '-NoProfile', '-NonInteractive', '-EncodedCommand', encoded], 60, encoding='utf-8')

def psjson(script):
    value = powershell(script + ' | ConvertTo-Json -Depth 6 -Compress')
    return json.loads(value) if value else None

class WindowsBackend:
    def supported(self):
        return WINDOWS and platform.version().split('.')[-1].isdigit() and int(platform.version().split('.')[-1]) >= 19041

    def read(self, target):
        if not self.supported():
            raise RuntimeError('Requires Windows 10 build 19041 or later.')
        from . import windows_controls as controls
        if target == 'ac-mode':
            if int(platform.version().split('.')[-1]) < 22000: raise RuntimeError('AC power-mode API action requires Windows 11')
            return controls.mode()
        if target == 'recording-policy': return controls.recording_policy()
        if target.startswith('startup:'): return controls.startup_read(target)
        if target.startswith('task:'): return controls.task_read(target)
        if target.startswith('eco:'):
            if int(platform.version().split('.')[-1]) < 22000: raise RuntimeError('EcoQoS action requires Windows 11')
            return controls.eco(target)
        if target == 'power':
            match = re.search(r'[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}', run(['powercfg', '/getactivescheme']))
            if not match:
                raise RuntimeError('Cannot identify active power scheme.')
            return match.group().lower()
        if target == 'fax':
            data = psjson("Get-CimInstance Win32_Service -Filter \"Name='Fax'\" | Select-Object Name,StartMode,State")
            if not data:
                raise RuntimeError('Fax service is not installed.')
            # This action changes startup only; it never stops a running service.
            if data['State'] != 'Stopped':
                raise RuntimeError('Fax is running; close fax activity first. No change made.')
            deps = psjson("Get-Service -Name Fax | Select-Object -ExpandProperty DependentServices | Select-Object Name")
            if deps:
                raise RuntimeError('Fax has dependent services; action refused.')
            # Refuse delayed-auto configurations rather than lose their delay flag.
            import winreg
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'SYSTEM\CurrentControlSet\Services\Fax') as key:
                    if winreg.QueryValueEx(key, 'DelayedAutoStart')[0]:
                        raise RuntimeError('Delayed-auto Fax configuration is not supported; no change made.')
            except FileNotFoundError:
                pass
            return data['StartMode']
        raise ValueError('Unknown target')

    def write(self, target, value):
        self.read(target)  # Repeat safety checks immediately before mutation.
        from . import windows_controls as controls
        if target == 'ac-mode': controls.mode(value); return
        if target == 'recording-policy': controls.recording_policy(value); return
        if target.startswith('startup:'): controls.startup_write(target,value); return
        if target.startswith('task:'): controls.task_write(target,value); return
        if target.startswith('eco:'): controls.eco(target,value); return
        if target == 'power':
            if not re.fullmatch(r'[0-9a-f-]{36}', value):
                raise ValueError('Invalid power scheme')
            run(['powercfg', '/setactive', value])
        elif target == 'fax':
            modes = {'Auto': 'Automatic', 'Manual': 'Manual', 'Disabled': 'Disabled'}
            if value not in modes:
                raise ValueError('Unsupported service mode')
            powershell("Set-Service -Name Fax -StartupType " + modes[value])
        else:
            raise ValueError('Unknown target')

    def prepare(self, action):
        if not self.supported(): raise RuntimeError('Windows required')
        if action.target in ('power','ac-mode'):
            import ctypes
            class PowerStatus(ctypes.Structure):
                _fields_ = [('ac', ctypes.c_ubyte), ('flag', ctypes.c_ubyte), ('percent', ctypes.c_ubyte), ('reserved', ctypes.c_ubyte), ('life', ctypes.c_ulong), ('full', ctypes.c_ulong)]
            status=PowerStatus()
            if not ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(status)) or status.ac != 1:
                raise RuntimeError('Power trial requires confirmed AC power')
            if action.target == 'power' and action.desired.lower() not in run(['powercfg','/list']).lower():
                raise RuntimeError('Requested existing power plan is unavailable; no plan will be created.')
            if action.target == 'ac-mode' and self.read('power') != '381b4222-f694-41f0-9685-ff5bb260df2e':
                raise RuntimeError('AC power-mode trial requires the Balanced base plan. Do not combine with High performance plan.')

    def backup(self, target, folder):
        if not self.supported(): raise RuntimeError('Windows required')
        if target.startswith('task:'):
            from .windows_controls import task_read
            task_read(target,folder / 'original-task.xml')
        if target == 'power':
            run(['powercfg', '/export', str(folder / 'original.pow'), self.read(target)])

class MockBackend:
    def __init__(self):
        self.values = {'power': '381b4222-f694-41f0-9685-ff5bb260df2e', 'fax': 'Manual', 'ac-mode':'00000000-0000-0000-0000-000000000000', 'recording-policy':{'exists':False}}
    def supported(self): return True
    def read(self, target): return self.values[target]
    def write(self, target, value): self.values[target] = value
    def backup(self, target, folder): pass
