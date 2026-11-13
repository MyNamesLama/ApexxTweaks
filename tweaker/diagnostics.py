import json
import os
import platform
import statistics
import re
from pathlib import Path
from .platform import WINDOWS, psjson, powershell

def inventory():
    if not WINDOWS:
        return {'platform': platform.platform(), 'mode': 'Linux preview — Windows diagnostics unavailable',
                'limitations': 'No Windows hardware readings are simulated.'}
    return psjson("""& {
      $os=Get-CimInstance Win32_OperatingSystem
      [pscustomobject]@{
        platform=$os.Caption; build=$os.BuildNumber
        cpu=@(Get-CimInstance Win32_Processor | Select-Object Name,NumberOfCores,NumberOfLogicalProcessors,MaxClockSpeed)
        gpu=@(Get-CimInstance Win32_VideoController | Select-Object Name,DriverVersion,CurrentRefreshRate,VideoModeDescription)
        memory=[pscustomobject]@{totalMB=[math]::Round($os.TotalVisibleMemorySize/1024);freeMB=[math]::Round($os.FreePhysicalMemory/1024)}
        disks=@(Get-PhysicalDisk | Select-Object FriendlyName,MediaType,HealthStatus,OperationalStatus)
        adapters=@(Get-NetAdapter | Select-Object Name,InterfaceDescription,Status,LinkSpeed)
      }
    }""")

def activity():
    return psjson("""& {
      [pscustomobject]@{
        processes=@(Get-CimInstance Win32_PerfFormattedData_PerfProc_Process | Where-Object {$_.Name -notin @('_Total','Idle')} | Sort-Object PercentProcessorTime -Descending | Select-Object -First 20 Name,IDProcess,PercentProcessorTime,WorkingSetPrivate,IODataBytesPersec)
        memory=@(Get-CimInstance Win32_PerfFormattedData_PerfOS_Memory | Select-Object AvailableMBytes,PagesInputPersec,PercentCommittedBytesInUse)
        cpu=@(Get-CimInstance Win32_PerfFormattedData_PerfOS_Processor | Where-Object Name -ne '_Total' | Select-Object Name,PercentProcessorTime)
        gpu=@(Get-CimInstance Win32_PerfFormattedData_GPUPerformanceCounters_GPUEngine -ErrorAction SilentlyContinue | Where-Object {$_.Name -like '*engtype_3D*'} | Select-Object Name,UtilizationPercentage)
      }
    }""")

def startup():
    return psjson("""& { [pscustomobject]@{
      startup=@(Get-CimInstance Win32_StartupCommand | Select-Object Name,Command,Location,User)
      tasks=@(Get-ScheduledTask | Where-Object {$_.TaskPath -notlike '\\Microsoft\\*'} | Select-Object TaskName,TaskPath,State)
      services=@(Get-CimInstance Win32_Service | Where-Object {$_.StartMode -eq 'Auto'} | Select-Object Name,DisplayName,State)
    }}""")

def fortnite():
    folder = Path(os.environ.get('PROGRAMDATA', 'C:/ProgramData')) / 'Epic/EpicGamesLauncher/Data/Manifests'
    found = []
    for path in folder.glob('*.item'):
        try:
            item = json.loads(path.read_text(encoding='utf-8-sig'))
            if item.get('AppName') == 'Fortnite':
                found.append({'name': item.get('DisplayName'), 'path': item.get('InstallLocation'),
                              'exists': Path(item.get('InstallLocation', '')).is_dir()})
        except (ValueError, OSError): pass
    return found

def network(host, count=20):
    # Pass as a validated literal, never interpolate free text into PowerShell.
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.:-]{0,252}', host):
        raise ValueError('Enter a hostname or IP address without spaces or shell syntax.')
    if not 2 <= count <= 40: raise ValueError('Probe count must be 2–40')
    raw = psjson("& { $p=New-Object System.Net.NetworkInformation.Ping; try { @(1.." + str(count) +
                 " | ForEach-Object { try { $r=$p.Send('" + host +
                 "',1000); if($r.Status -eq 'Success'){[double]$r.RoundtripTime}else{-1} } catch {-1} }) } finally {$p.Dispose()} }")
    values = raw if isinstance(raw, list) else [raw]
    ok = [float(v) for v in values if v is not None and v >= 0]
    return {'target': host, 'sent': len(values), 'loss_percent': 100*(len(values)-len(ok))/len(values),
            'mean_ms': statistics.mean(ok) if ok else None,
            'jitter_mean_adjacent_ms': statistics.mean(abs(b-a) for a,b in zip(ok,ok[1:])) if len(ok)>1 else None,
            'note': 'ICMP response loss may be rate limiting. This is not game-server latency. Probe gateway and remote host separately; no background bandwidth attribution.'}

GUIDANCE = '''FORTNITE • MEASURE FIRST
Compare supported Performance and DirectX 12 rendering options in the game UI. Warm shaders and repeat the same route three times per condition. Do not edit game files.
GPU pressure: lower rendering resolution, shadows and effects in-game; compare visual clarity and frame times. CPU pressure: inspect busy individual cores and background CPU; total CPU alone cannot establish a bottleneck.
NVIDIA Reflex: test the supported in-game option on supported hardware. Boost can increase power/heat. Never stack undocumented queue tweaks.
Use Windows Advanced display to select your monitor's intended refresh rate. Mouse acceleration and sensitivity are preferences; this app makes no input-latency claim.
Use a stable in-game frame cap appropriate to measured sustainable FPS and your VRR range. Compare lows and frame pacing, not just averages.
HAGS and windowed optimizations: hardware/driver dependent; A/B test through Windows Graphics settings. No automatic HAGS toggle.
Memory pressure: sustained low available RAM plus paging is evidence to close your own unused apps or consider more RAM. Never clear standby memory.
Storage: inspect concurrent I/O and free space; leave TRIM, pagefile and maintenance enabled. Disk health here is an OS health flag, not a full SMART assessment.
Thermal throttling, VRAM, end-to-end input latency, GPU render latency and network per-process bandwidth are not measured by this version. Use vendor-supported diagnostics. No FPS improvement is presumed.
Keep Windows and supported GPU drivers current using official vendor channels. Close overlays manually only if you do not need them.
Service and task listings are inventories, not recommendations to disable them. Security, updates, launchers, input, audio, networking and anti-cheat remain untouched.
'''


def fortnite_running():
    # Enumerates public process names only; never requests game handles or memory.
    result=psjson("@(Get-Process -Name 'FortniteClient-Win64-Shipping*' -ErrorAction SilentlyContinue).Count")
    return int(result or 0)>0


def gaming_settings():
    if not WINDOWS: raise RuntimeError('Windows Settings status requires Windows')
    from .windows_controls import reg_read
    result={'game_mode':reg_read(r'Software\Microsoft\GameBar','AutoGameModeEnabled'),
            'game_mode_note':'Documented Windows 11 preference location; an absent value means unknown/default, not disabled. Use the Game Mode Settings page to change it.',
            'captures':'Inspect Record what happened in Captures Settings. No unsupported Windows 11 capture registry writes.',
            'graphics':'Use per-app Graphics Settings. GPU selection and windowed presentation preferences are user-driven; no undocumented preference writes.',
            'effective_state':'Registry/API read-back is configuration verification, not a measurement of game rendering or recording overhead.'}
    return result
