"""Evidence-qualified snapshot interpretation. Never claims causality or FPS gains."""
def rows(value):
    return value if isinstance(value,list) else [value] if value else []

def interpret(sample):
    notes=[]
    memory=rows(sample.get('memory'))
    for m in memory:
        if float(m.get('AvailableMBytes',999999)) < 1024 and float(m.get('PagesInputPersec',0)) > 10:
            notes.append('Memory-pressure candidate: <1 GiB available with page reads. Re-sample during stutter; page reads can include file-backed activity. Close your own unused applications before considering RAM upgrades.')
    cores=rows(sample.get('cpu'))
    if any(float(c.get('PercentProcessorTime',0)) >= 90 for c in cores):
        notes.append('A logical processor is ≥90% busy. CPU limitation is possible even with low total CPU. Compare sustained samples, GPU data and game frame times; this snapshot cannot identify the game thread.')
    engines=rows(sample.get('gpu'))
    if any(float(g.get('UtilizationPercentage',0)) >= 95 for g in engines):
        notes.append('A 3D engine is ≥95% utilized. Test lower in-game rendering resolution; engine utilization alone does not prove the selected game is GPU limited.')
    processes=rows(sample.get('processes'))
    heavy=[str(p.get('Name')) for p in processes if float(p.get('IODataBytesPersec',0))>20*1024*1024]
    if heavy:
        notes.append('High I/O candidates: '+', '.join(heavy)+'. Counter includes network and device I/O, not just disk. Correlate timestamps with frame spikes before attributing stutter.')
    if not notes: notes.append('No strong candidate from this snapshot. This does not establish that the system is bottleneck-free. Repeated captures are needed.')
    return {'interpretation':notes,'sample':sample,'confidence':'Screening only; no causal diagnosis or measured FPS improvement.'}


def sustained(samples):
    """Repeated-counter screening with explicit coverage and game GPU attribution."""
    import re
    if len(samples)<3: raise ValueError('At least three timestamped samples required')
    cores={}; gpu=[]; memory=[]; background={}; memory_apps={}; missing_gpu=0
    for sample in samples:
        for core in rows(sample.get('cpu')):
            cores.setdefault(str(core['Name']),[]).append(float(core.get('PercentProcessorTime') or 0))
        processes=rows(sample.get('processes'))
        game_pids={int(pid) for pid in sample.get('game_pids',[])}
        game_pids.update(int(p['IDProcess']) for p in processes if str(p.get('Name','')).lower().startswith('fortniteclient-win64-shipping'))
        engines=[]
        for engine in rows(sample.get('gpu')):
            match=re.search(r'pid_(\d+)_',str(engine.get('Name','')))
            if match and int(match.group(1)) in game_pids and engine.get('UtilizationPercentage') is not None:
                engines.append(float(engine.get('UtilizationPercentage') or 0))
        if engines: gpu.append(max(engines))
        else: missing_gpu+=1
        for m in rows(sample.get('memory')):
            if m.get('AvailableMBytes') is None or m.get('PagesInputPersec') is None: continue
            memory.append(float(m.get('AvailableMBytes') or 0)<1024 and float(m.get('PagesInputPersec') or 0)>10)
        logical=int(sample.get('logical_processors') or 1)
        for process in processes:
            if int(process.get('IDProcess') or 0) in game_pids: continue
            key=(str(process.get('Name')),int(process.get('IDProcess') or 0))
            background.setdefault(key,[]).append(float(process.get('PercentProcessorTime') or 0)/logical)
            if process.get('WorkingSetPrivate') is not None:
                memory_apps.setdefault(key,[]).append(float(process['WorkingSetPrivate'])/(1024*1024))
    hot=[key for key,values in cores.items() if len(values)>=len(samples)*.8 and sum(v>=90 for v in values)/len(values)>=.7]
    gpu_busy=bool(len(gpu)>=len(samples)*.8 and sum(v>=95 for v in gpu)/len(gpu)>=.7)
    pressure=bool(len(memory)>=len(samples)*.8 and sum(memory)/len(memory)>=.7)
    notes=[]
    if hot and not gpu_busy:
        notes.append('Sustained busy logical processors ('+', '.join(hot)+'). CPU/background limitation is a candidate; compare a lower-resolution run. Low GPU coverage is unknown, not evidence of CPU limitation.')
    if gpu_busy: notes.append('Fortnite-attributed 3D engine ≥95% in ≥70% of covered samples. GPU limitation is a candidate: test lower in-game rendering resolution and compare lows.')
    if pressure: notes.append('Sustained low available RAM with page reads. Close unused apps and compare; paging also includes file-backed reads.')
    if not notes: notes.append('No sustained candidate met the thresholds; thermal, power and game-thread limitations remain unmeasured.')
    return {'samples':len(samples),'first_timestamp':samples[0].get('timestamp'),'last_timestamp':samples[-1].get('timestamp'),
            'hot_logical_processors':hot,'gpu_game_coverage':len(gpu)/len(samples),'gpu_missing_samples':missing_gpu,
            'gpu_busy_candidate':gpu_busy,'memory_coverage':len(memory)/len(samples),'memory_pressure_candidate':pressure,'recommendations':notes,
            'background_cpu_mean_percent_of_machine':sorted(
                [{'name':name,'pid':pid,'cpu_percent':sum(v)/len(samples),'coverage':len(v)/len(samples)} for (name,pid),v in background.items()],
                key=lambda p:p['cpu_percent'],reverse=True)[:10],
            'background_private_working_set_mib':sorted(
                [{'name':name,'pid':pid,'mean_mib':sum(values)/len(samples)} for (name,pid),values in memory_apps.items()],
                key=lambda p:p['mean_mib'],reverse=True)[:10],
            'limitations':'Candidate screening, not causal diagnosis. No thermal, VRAM or game-thread access. Sampling adds overhead; use the same monitoring in A/B runs.'}
