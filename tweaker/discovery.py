"""Discover optional control targets; everything else remains read-only."""
import ntpath
import platform as system_platform
from .actions import optional_action
from .targets import encode, RUN_KEY, executable
from .windows_controls import signature, task_definition, eco, literal
from .analysis import rows
from .branding import OPTIONAL_TASK_PATHS

def discover():
    from .platform import WINDOWS, psjson
    if not WINDOWS: raise RuntimeError('Optional application discovery requires Windows')
    import winreg
    actions=[]; rejected=[]
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,RUN_KEY) as key:
            index=0
            while True:
                try: name,command,kind=winreg.EnumValue(key,index)
                except OSError as error:
                    if error.winerror==259: break
                    raise
                index+=1
                if kind!=winreg.REG_SZ: continue
                try:
                    path=executable(command); signature(path)
                    target=encode('startup',name=name,command=command)
                    actions.append(optional_action('startup',target,'Skip logon launch: '+name,{'exists':False}))
                except (ValueError,RuntimeError) as error: rejected.append({'startup':name,'reason':str(error)})
    except FileNotFoundError: pass
    # Public CIM metadata only for allowlisted optional apps. No game paths/handles.
    candidates=psjson("Get-CimInstance Win32_Process -Filter \"Name='Spotify.exe' OR Name='Discord.exe'\" | Select-Object ProcessId,ExecutablePath,CreationDate")
    for process in rows(candidates):
        try:
            if int(system_platform.version().split('.')[-1])<22000:
                raise RuntimeError('Optional EcoQoS actions require Windows 11')
            path=process['ExecutablePath']
            if not path: raise RuntimeError('Process executable path unavailable')
            signature(path)
            # CreationDate serialization from CIM is not a FILETIME contract. Query
            # the exact creation FILETIME through a query-only handle before binding.
            created=creation_time(int(process['ProcessId']))
            target=encode('eco',pid=int(process['ProcessId']),created=str(created),path=path)
            current=eco(target)
            desired={'control':current['control']|1,'state':current['state']|1}
            actions.append(optional_action('eco',target,'EcoQoS: '+ntpath.basename(path)+' PID '+str(process['ProcessId']),desired))
        except Exception as error: rejected.append({'process':process.get('ProcessId'),'reason':str(error)})
    tasks=[]
    for namespace in OPTIONAL_TASK_PATHS:
        tasks.extend(rows(psjson("& { $sid=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value; @(Get-ScheduledTask -TaskPath " + literal(namespace) + " -ErrorAction SilentlyContinue | ForEach-Object { [pscustomobject]@{name=$_.TaskName;path=$_.TaskPath;sid=$sid;xml=(Export-ScheduledTask -TaskName $_.TaskName -TaskPath $_.TaskPath)} }) }")))
    for task in rows(tasks):
        try:
            path,_,fingerprint=task_definition(task['xml'],task['sid']); signature(path)
            target=encode('task',name=task['name'],path=task['path'],fingerprint=fingerprint)
            actions.append(optional_action('task',target,'Pause optional launch task: '+task['name'],{'enabled':False,'fingerprint':fingerprint}))
        except Exception as error: rejected.append({'task':task.get('name'),'reason':str(error)})
    return actions,rejected


def creation_time(pid):
    import ctypes
    from ctypes import wintypes as w
    k=ctypes.WinDLL('kernel32',use_last_error=True)
    k.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD]; k.OpenProcess.restype=w.HANDLE
    k.GetProcessTimes.argtypes=[w.HANDLE]+[ctypes.POINTER(w.FILETIME)]*4; k.GetProcessTimes.restype=w.BOOL
    k.CloseHandle.argtypes=[w.HANDLE]; k.CloseHandle.restype=w.BOOL
    handle=k.OpenProcess(0x1000,False,pid)
    if not handle: raise ctypes.WinError(ctypes.get_last_error())
    try:
        times=[w.FILETIME() for _ in range(4)]
        if not k.GetProcessTimes(handle,*(ctypes.byref(v) for v in times)): raise ctypes.WinError(ctypes.get_last_error())
        return (times[0].dwHighDateTime<<32)|times[0].dwLowDateTime
    finally: k.CloseHandle(handle)
