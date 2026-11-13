"""Strictly scoped Windows controls; imported on Linux without loading Windows DLLs."""
import ctypes
import hashlib
import ntpath
import uuid
import xml.etree.ElementTree as ET
from contextlib import contextmanager
from .targets import decode, executable, approved_image, RUN_KEY, PUBLISHERS
from .branding import OPTIONAL_TASK_PATHS

ABSENT = {'exists': False}

def literal(value):
    # PowerShell single-quoted literals escape quote by doubling it.
    return "'" + str(value).replace("'", "''") + "'"

def signature(path):
    from .platform import psjson
    result = psjson("Get-AuthenticodeSignature -LiteralPath " + literal(path) +
                    " | Select-Object @{n='status';e={$_.Status.ToString()}},@{n='subject';e={$_.SignerCertificate.Subject}}")
    if not result or not approved_image(path, result['status'], result['subject']):
        raise RuntimeError('Executable signature is not an approved optional-app publisher.')

def reg_read(key, name):
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key, 0, winreg.KEY_READ) as handle:
            value, kind = winreg.QueryValueEx(handle, name)
            if kind not in (winreg.REG_SZ, winreg.REG_DWORD):
                raise RuntimeError('Unsupported registry type; refusing loss of original data.')
            return {'exists': True, 'type': kind, 'value': value}
    except FileNotFoundError: return dict(ABSENT)

def reg_write(key, name, value):
    import winreg
    if value == ABSENT:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key, 0, winreg.KEY_SET_VALUE) as handle:
                winreg.DeleteValue(handle, name)
        except FileNotFoundError: pass
    else:
        if value.get('type') not in (winreg.REG_SZ, winreg.REG_DWORD): raise ValueError('Invalid registry type')
        # Never create preference keys for features absent from this OS/profile.
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key, 0, winreg.KEY_SET_VALUE) as handle:
            winreg.SetValueEx(handle, name, 0, value['type'], value['value'])

def startup_spec(target):
    spec = decode(target, 'startup')
    if set(spec) != {'name', 'command'} or not spec['name'] or len(spec['name'])>256:
        raise ValueError('Invalid startup descriptor')
    path = executable(spec['command'])
    return spec, path

def startup_read(target):
    spec, path = startup_spec(target)
    current = reg_read(RUN_KEY, spec['name'])
    if current != ABSENT and (current.get('type') != 1 or current.get('value') != spec['command']):
        raise RuntimeError('Startup command changed since discovery; rescan first.')
    return current

def startup_write(target, value):
    spec, path = startup_spec(target)
    startup_read(target)
    if value != ABSENT and value != {'exists':True,'type':1,'value':spec['command']}:
        raise ValueError('Restore command differs from approved snapshot')
    signature(path)
    reg_write(RUN_KEY, spec['name'], value)


def mode(write=None):
    from ctypes import wintypes as w
    class GUID(ctypes.Structure):
        _fields_=[('raw',ctypes.c_ubyte*16)]
    lib=ctypes.WinDLL('powrprof',use_last_error=True)
    name='PowerGetUserConfiguredACPowerMode' if write is None else 'PowerSetUserConfiguredACPowerMode'
    try: fn=getattr(lib,name)
    except AttributeError: raise RuntimeError('This Windows version does not expose the supported AC power-mode API.')
    fn.argtypes=[ctypes.POINTER(GUID)]; fn.restype=w.DWORD
    guid=GUID()
    if write is not None:
        if write not in ('00000000-0000-0000-0000-000000000000','ded574b5-45a0-4f42-8737-46345c09c238','961cc777-2547-4f9d-8174-7d86181b8a7a'):
            raise ValueError('Unsupported AC power mode')
        ctypes.memmove(ctypes.byref(guid),uuid.UUID(write).bytes_le,16)
    error=fn(ctypes.byref(guid))
    if error: raise ctypes.WinError(error)
    return str(uuid.UUID(bytes_le=bytes(guid.raw)))


def task_definition(xml, sid):
    """Only same-user, non-elevated direct app-launch tasks; no updates/scripts/COM."""
    tree=ET.fromstring(xml)
    ns={'t':'http://schemas.microsoft.com/windows/2004/02/mit/task'}
    principals=tree.findall('t:Principals/t:Principal',ns)
    if len(principals)!=1: raise RuntimeError('Unsupported task principal')
    p=principals[0]
    if p.findtext('t:UserId',namespaces=ns)!=sid or p.findtext('t:RunLevel',default='LeastPrivilege',namespaces=ns)!='LeastPrivilege':
        raise RuntimeError('Only current-user non-elevated tasks can be changed')
    if p.findtext('t:LogonType',namespaces=ns) not in ('InteractiveToken','S4U'):
        raise RuntimeError('Unsupported task logon type')
    actions=tree.findall('t:Actions/*',ns)
    if len(actions)!=1 or actions[0].tag!='{'+ns['t']+'}Exec': raise RuntimeError('Only a single direct executable action is supported')
    action=actions[0]
    path=action.findtext('t:Command',default='',namespaces=ns)
    args=action.findtext('t:Arguments',default='',namespaces=ns)
    executable('"'+path.strip('"')+'" '+args)
    settings=tree.find('t:Settings',ns)
    if settings is None: raise RuntimeError('Missing task settings')
    enabled=settings.find('t:Enabled',ns)
    is_enabled=enabled is None or enabled.text=='true'
    if enabled is not None: settings.remove(enabled)
    # Ignore task enable/disable only; preserve a fingerprint of the rest.
    canonical=ET.canonicalize(ET.tostring(tree,encoding='unicode'),strip_text=True)
    return path.strip('"'), is_enabled, hashlib.sha256(canonical.encode()).hexdigest()


def task_read(target, export_to=None):
    from .platform import psjson
    spec=decode(target,'task')
    if set(spec)!={'path','name','fingerprint'} or not spec['path'].startswith('\\') or spec['path'].lower().startswith('\\microsoft\\'):
        raise ValueError('Invalid or protected task target')
    # Only opt-in optional namespace: no accidental updater/scheduler targeting.
    if spec['path'] not in OPTIONAL_TASK_PATHS: raise ValueError('Task is outside the optional namespace')
    script="& { $sid=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value; $xml=Export-ScheduledTask -TaskPath " + literal(spec['path']) + ' -TaskName ' + literal(spec['name']) + "; [pscustomobject]@{sid=$sid;xml=$xml} }"
    result=psjson(script)
    path, enabled, fingerprint=task_definition(result['xml'],result['sid'])
    if fingerprint!=spec['fingerprint']: raise RuntimeError('Task definition changed; refusing to overwrite it')
    if export_to is not None: export_to.write_text(result['xml'],encoding='utf-8')
    return {'enabled':enabled,'fingerprint':fingerprint}

def task_write(target,value):
    from .platform import powershell
    spec=decode(target,'task'); current=task_read(target)
    if set(value)!={'enabled','fingerprint'} or value['fingerprint']!=current['fingerprint'] or type(value['enabled']) is not bool:
        raise ValueError('Invalid task state')
    # Signature verified at write time too, after reading definition.
    from .platform import psjson
    raw=psjson("& { [pscustomobject]@{sid=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value;xml=(Export-ScheduledTask -TaskPath "+literal(spec['path'])+' -TaskName '+literal(spec['name'])+")} }")
    path,_,fingerprint=task_definition(raw['xml'],raw['sid'])
    if fingerprint!=current['fingerprint']: raise RuntimeError('Task changed during review')
    signature(path)
    verb='Enable' if value['enabled'] else 'Disable'
    powershell(verb+'-ScheduledTask -TaskPath '+literal(spec['path'])+' -TaskName '+literal(spec['name'])+' | Out-Null')


class ProcessExpired(RuntimeError): pass

@contextmanager
def _checked_process_handle(spec, write=False):
    from ctypes import wintypes as w
    if set(spec)!={'pid','created','path'} or type(spec['pid']) is not int or spec['pid']<=0 or ntpath.basename(spec['path']).lower() not in PUBLISHERS:
        raise ValueError('Not an approved optional process target')
    k=ctypes.WinDLL('kernel32',use_last_error=True)
    k.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD]; k.OpenProcess.restype=w.HANDLE
    k.CloseHandle.argtypes=[w.HANDLE]; k.CloseHandle.restype=w.BOOL
    k.QueryFullProcessImageNameW.argtypes=[w.HANDLE,w.DWORD,w.LPWSTR,ctypes.POINTER(w.DWORD)]; k.QueryFullProcessImageNameW.restype=w.BOOL
    k.GetProcessTimes.argtypes=[w.HANDLE]+[ctypes.POINTER(w.FILETIME)]*4; k.GetProcessTimes.restype=w.BOOL
    k.GetExitCodeProcess.argtypes=[w.HANDLE,ctypes.POINTER(w.DWORD)]; k.GetExitCodeProcess.restype=w.BOOL
    handle=k.OpenProcess(0x1000 | (0x0200 if write else 0),False,spec['pid'])
    if not handle:
        error=ctypes.get_last_error()
        if error==87: raise ProcessExpired('Original process exited')
        raise ctypes.WinError(error)
    try:
        code=w.DWORD()
        if not k.GetExitCodeProcess(handle,ctypes.byref(code)): raise ctypes.WinError(ctypes.get_last_error())
        if code.value!=259: raise ProcessExpired('Original process exited')
        times=[w.FILETIME() for _ in range(4)]
        if not k.GetProcessTimes(handle,*(ctypes.byref(v) for v in times)): raise ctypes.WinError(ctypes.get_last_error())
        created=(times[0].dwHighDateTime<<32)|times[0].dwLowDateTime
        if str(created)!=str(spec['created']): raise ProcessExpired('PID reused; original process no longer exists')
        buffer=ctypes.create_unicode_buffer(32768); size=w.DWORD(len(buffer))
        if not k.QueryFullProcessImageNameW(handle,0,buffer,ctypes.byref(size)): raise ctypes.WinError(ctypes.get_last_error())
        if ntpath.normcase(buffer.value)!=ntpath.normcase(spec['path']): raise RuntimeError('Executable identity changed')
        k.GetCurrentProcess.restype=w.HANDLE
        if token_sid(handle)!=token_sid(k.GetCurrentProcess()):
            raise RuntimeError('Only optional processes owned by the current user are eligible')
        signature(buffer.value)
        yield k,handle
    finally: k.CloseHandle(handle)


@contextmanager
def process_handle(spec, write=False):
    # Validate lifetime/image/user using query-only access FIRST. Keep that handle
    # alive while acquiring and revalidating a write-capable handle. A reused PID
    # detected by the first check is never opened with SET_INFORMATION access.
    with _checked_process_handle(spec,write=False) as query:
        if write:
            with _checked_process_handle(spec,write=True) as writable:
                yield writable
        else: yield query


def eco(target, value=None):
    from ctypes import wintypes as w
    spec=decode(target,'eco')
    class State(ctypes.Structure):
        _fields_=[('version',w.ULONG),('control',w.ULONG),('state',w.ULONG)]
    with process_handle(spec,write=value is not None) as (k,handle):
        get=k.GetProcessInformation; get.argtypes=[w.HANDLE,ctypes.c_int,ctypes.c_void_p,w.DWORD]; get.restype=w.BOOL
        state=State(1,0,0)
        if not get(handle,4,ctypes.byref(state),ctypes.sizeof(state)): raise ctypes.WinError(ctypes.get_last_error())
        if value is not None:
            if set(value)!={'control','state'} or any(type(v) is not int or v<0 or v>0xffffffff for v in value.values()): raise ValueError('Invalid QoS snapshot')
            # Only bit 0 can change: all other policy flags must match current state.
            if (value['control']^state.control)&~1 or (value['state']^state.state)&~1:
                raise RuntimeError('Other power-throttling flags changed outside ApexxTweaks')
            state=State(1,value['control'],value['state'])
            put=k.SetProcessInformation; put.argtypes=get.argtypes; put.restype=w.BOOL
            if not put(handle,4,ctypes.byref(state),ctypes.sizeof(state)): raise ctypes.WinError(ctypes.get_last_error())
        return {'control':int(state.control),'state':int(state.state)}


def recording_policy(value=None):
    """Documented Windows 10 desktop Pro+ GameDVR policy; never override management."""
    import platform
    import winreg
    from .platform import psjson
    build=int(platform.version().split('.')[-1])
    if not 19041<=build<=19045: raise RuntimeError('GameDVR policy is documented only for Windows 10 desktop; use Captures Settings here.')
    info=psjson("Get-CimInstance Win32_OperatingSystem | Select-Object OperatingSystemSKU")
    if int(info['OperatingSystemSKU']) not in (4,27,48,49,72,121,122,125,126,161,162):
        raise RuntimeError('GameDVR policy requires a supported Pro/Enterprise/Education edition')
    if psjson("(Get-CimInstance Win32_ComputerSystem).PartOfDomain"):
        raise RuntimeError('Domain-managed devices are excluded from local capture-policy changes')
    for key in (r'SOFTWARE\Microsoft\Enrollments',r'SOFTWARE\Microsoft\Provisioning\OMADM\Accounts'):
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,key) as handle:
                if winreg.QueryInfoKey(handle)[0]: raise RuntimeError('Enrollment records found; use your managed Settings instead')
        except FileNotFoundError: pass
    key=r'SOFTWARE\Policies\Microsoft\Windows\GameDVR'; name='AllowGameDVR'
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,key) as handle:
            data,kind=winreg.QueryValueEx(handle,name)
            if kind!=winreg.REG_DWORD or data not in (0,1): raise RuntimeError('Unsupported capture policy value')
            current={'exists':True,'type':kind,'value':data}
    except FileNotFoundError: current=dict(ABSENT)
    if value is not None:
        if value not in (ABSENT,{'exists':True,'type':4,'value':0},{'exists':True,'type':4,'value':1}): raise ValueError('Invalid recording policy value')
        if value==ABSENT:
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,key,0,winreg.KEY_SET_VALUE) as handle: winreg.DeleteValue(handle,name)
            except FileNotFoundError: pass
        else:
            with winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE,key,0,winreg.KEY_SET_VALUE) as handle:
                winreg.SetValueEx(handle,name,0,winreg.REG_DWORD,value['value'])
        return value
    return current


def token_sid(process):
    """Return token user SID, not executable owner or a display-name comparison."""
    from ctypes import wintypes as w
    adv=ctypes.WinDLL('advapi32',use_last_error=True)
    k=ctypes.WinDLL('kernel32',use_last_error=True)
    adv.OpenProcessToken.argtypes=[w.HANDLE,w.DWORD,ctypes.POINTER(w.HANDLE)]; adv.OpenProcessToken.restype=w.BOOL
    adv.GetTokenInformation.argtypes=[w.HANDLE,ctypes.c_int,ctypes.c_void_p,w.DWORD,ctypes.POINTER(w.DWORD)]; adv.GetTokenInformation.restype=w.BOOL
    adv.ConvertSidToStringSidW.argtypes=[ctypes.c_void_p,ctypes.POINTER(w.LPWSTR)]; adv.ConvertSidToStringSidW.restype=w.BOOL
    k.CloseHandle.argtypes=[w.HANDLE]; k.CloseHandle.restype=w.BOOL
    k.LocalFree.argtypes=[ctypes.c_void_p]; k.LocalFree.restype=ctypes.c_void_p
    token=w.HANDLE(); needed=w.DWORD()
    if not adv.OpenProcessToken(process,8,ctypes.byref(token)): raise ctypes.WinError(ctypes.get_last_error())
    try:
        adv.GetTokenInformation(token,1,None,0,ctypes.byref(needed))
        if not needed.value: raise ctypes.WinError(ctypes.get_last_error())
        buffer=ctypes.create_string_buffer(needed.value)
        if not adv.GetTokenInformation(token,1,buffer,needed,ctypes.byref(needed)): raise ctypes.WinError(ctypes.get_last_error())
        sid_pointer=ctypes.cast(buffer,ctypes.POINTER(ctypes.c_void_p))[0]
        text=w.LPWSTR()
        if not adv.ConvertSidToStringSidW(sid_pointer,ctypes.byref(text)): raise ctypes.WinError(ctypes.get_last_error())
        try: return text.value
        finally: k.LocalFree(ctypes.cast(text,ctypes.c_void_p))
    finally: k.CloseHandle(token)
