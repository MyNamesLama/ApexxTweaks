"""Bounded read-only sampling, one PowerShell invocation to limit startup overhead."""
from .platform import psjson
from .analysis import rows, sustained

def collect(count=8, interval=1):
    if not 3<=count<=15 or not 1<=interval<=2: raise ValueError('Sampling bounds: 3–15 samples, interval 1–2 seconds')
    script=r'''& {
      $logical=[Environment]::ProcessorCount
      @(1..COUNT | ForEach-Object {
        $gameIds=@(Get-CimInstance Win32_Process -Filter "Name='FortniteClient-Win64-Shipping.exe'" | Select-Object -ExpandProperty ProcessId)
        $cpu=@(Get-CimInstance Win32_PerfFormattedData_PerfOS_Processor | Where-Object Name -ne '_Total' | Select-Object Name,PercentProcessorTime)
        $processes=@(Get-CimInstance Win32_PerfFormattedData_PerfProc_Process | Where-Object {$_.Name -notin @('_Total','Idle')} | Select-Object Name,IDProcess,PercentProcessorTime,WorkingSetPrivate,IODataBytesPersec)
        $gpu=@(Get-CimInstance Win32_PerfFormattedData_GPUPerformanceCounters_GPUEngine -ErrorAction SilentlyContinue | Where-Object {$_.Name -like '*engtype_3D*'} | Select-Object Name,UtilizationPercentage)
        $memory=@(Get-CimInstance Win32_PerfFormattedData_PerfOS_Memory | Select-Object AvailableMBytes,PagesInputPersec,PercentCommittedBytesInUse)
        [pscustomobject]@{timestamp=[DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds();logical_processors=$logical;game_pids=$gameIds;cpu=$cpu;processes=$processes;gpu=$gpu;memory=$memory}
        if($_ -lt COUNT){Start-Sleep -Seconds INTERVAL}
      })
    }'''.replace('COUNT',str(count)).replace('INTERVAL',str(interval))
    samples=rows(psjson(script))
    return {'analysis':sustained(samples),'samples':samples}
