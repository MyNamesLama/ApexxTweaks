"""Hardware-aware supported UI recommendations; no game-file modification."""
from .analysis import rows

def recommendations(hardware, installations=()):
    gpus=rows(hardware.get('gpu')); cpus=rows(hardware.get('cpu'))
    names=' '.join(str(g.get('Name','')) for g in gpus).lower()
    notes=[]
    if 'nvidia' in names:
        notes.append('NVIDIA detected: compare the supported in-game Reflex On option. Test Boost separately for clock/thermal costs. Reflex is not a network-latency setting.')
    if 'amd' in names or 'radeon' in names:
        notes.append('AMD detected: compare supported in-game rendering modes and a sustainable frame cap. Do not enable injection-based driver latency tools for protected games.')
    if 'intel' in names:
        notes.append('Intel graphics detected: confirm the active game GPU in Task Manager and install the supported OEM/Intel driver. Shared-memory pressure can affect integrated graphics.')
    if len(gpus)>1:
        notes.append('Multiple GPU devices detected: use Windows Graphics Settings → Fortnite → Options to review the intended high-performance GPU. Inventory does not prove which GPU currently renders the game; do not write undocumented UserGpuPreferences values.')
    ram=float((hardware.get('memory') or {}).get('totalMB') or 0)
    if ram and ram<16*1024:
        notes.append('Under 16 GiB RAM detected: collect memory-pressure samples while playing; close unused browser tabs/apps if pressure and frame spikes coincide. Capacity alone does not prove a bottleneck.')
    refresh=[int(g.get('CurrentRefreshRate') or 0) for g in gpus]
    if any(1<rate<=60 for rate in refresh):
        notes.append('A reported display mode is ≤60 Hz. Check Advanced display for your actual gaming monitor and supported refresh modes. Video-controller data can describe another display; no automatic refresh change.')
    if any('intel' in str(c.get('Name','')).lower() for c in cpus):
        notes.append('Intel CPU detected: preserve Windows scheduling and security defaults. Hybrid-core affinity pinning is not applied; use supported Windows updates and compare per-core activity.')
    notes.extend([
        'Compare the supported Performance and DirectX 12 options shown by your installed Fortnite version. Warm shaders before repeated matched captures; no fixed rendering mode is universally fastest.',
        'If GPU-limited, reduce shadows/effects/render resolution in-game one at a time. If CPU/background-limited, test approved optional-app EcoQoS separately and compare repeated 1%/0.1% lows.',
        'Guided Game Mode: Settings → Gaming → Game Mode. Prefer enabling for a baseline and compare. Captures: turn off Record what happened only if you do not need background clips. Windows 11 writes remain user-driven through Settings.',
        'Graphics: use the supported per-app Windows Settings UI. Windowed optimizations target compatible DX10/11 presentation paths; do not assume a DX12 or Performance mode gain. Restart the game after changing GPU preferences.',
        'Use a repeatable route and frame cap, identical graphics and driver configuration. End-to-end input latency and thermal throttling need external supported instrumentation.'
    ])
    return {'installations':list(installations),'hardware':hardware,'recommendations':notes,
            'evidence':'Hardware-specific guidance; no measured performance improvement or anti-cheat certification.'}
