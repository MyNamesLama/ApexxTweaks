import concurrent.futures
import json
import os
import queue
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from .actions import PROFILES
from .branding import APP_NAME, JOURNAL_MUTEX, data_directory, branded_text
from .engine import Engine, atomic_json
from .platform import WindowsBackend, WINDOWS, powershell
from . import diagnostics, benchmark
from .analysis import interpret
from .session import GamingSession
from . import discovery, telemetry
from .fortnite import recommendations
from .targets import classify_inventory

BG='#10141e'; PANEL='#191f2e'; FG='#e8edf7'; MUTED='#9daec9'; ACCENT='#7ae3bd'

class App:
    def __init__(self, root):
        self.root=root
        self.timers=set(); self.closing=False
        self.root.bind('<Destroy>',lambda event:self.shutdown() if event.widget is self.root else None)
        self.root.title(f'{APP_NAME} • Gaming performance lab')
        self.root.geometry('1180x800'); self.root.minsize(920,650); self.root.configure(bg=BG)
        self.pool=concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self.results=queue.Queue(); self.busy=False
        self.data=data_directory()
        self.engine=Engine(WindowsBackend(), self.data)
        self.runs={'Before':[], 'After':[]}
        if (self.data/'benchmarks.json').exists():
            self.runs=json.loads((self.data/'benchmarks.json').read_text())
        self.session=GamingSession(self.engine)
        self.close_after_session=False
        self.action_states={}
        self.last_telemetry=None
        self.watcher_pending=False
        style=ttk.Style(); style.theme_use('clam')
        style.configure('.',background=PANEL,foreground=FG,fieldbackground=BG,font=('Segoe UI',10))
        style.configure('TButton',padding=(12,8)); style.map('TButton',background=[('active','#303e54')])
        style.configure('TNotebook.Tab',padding=(18,12)); style.configure('TFrame',background=BG)
        style.configure('TLabel',background=BG)
        tk.Label(root,text=APP_NAME,fg=ACCENT,bg=BG,font=('Segoe UI',24,'bold')).pack(anchor='w',padx=26,pady=(20,0))
        tk.Label(root,text='Gaming performance lab  /  Observe · Change · Verify · Restore',fg=MUTED,bg=BG,font=('Segoe UI',11)).pack(anchor='w',padx=28,pady=(4,16))
        self.tabs=ttk.Notebook(root); self.tabs.pack(fill='both',expand=True,padx=24)
        self.pages={}
        for name in ['Dashboard','Optimize','Gaming','Benchmark','Advanced','Settings']:
            frame=ttk.Frame(self.tabs,padding=16); self.tabs.add(frame,text=name); self.pages[name]=frame
        self.status=tk.StringVar(value='Ready • Windows-only operations are unavailable on Linux' if not WINDOWS else 'Ready • No changes applied automatically')
        ttk.Label(root,textvariable=self.status).pack(anchor='w',padx=28,pady=12)
        self.dashboard(); self.optimize(); self.gaming(); self.bench(); self.advanced(); self.settings()
        self.schedule(100,self.drain); self.root.protocol('WM_DELETE_WINDOW',self.close)
        if any(r['status'] != 'restored' for r in self.engine.records):
            self.status.set('Saved changes or interrupted operations found. Review Settings → History / Restore.')

    def schedule(self,delay,callback):
        if self.closing: return
        token=None
        def invoke():
            self.timers.discard(token)
            if not self.closing: callback()
        token=self.root.after(delay,invoke)
        self.timers.add(token)
        return token

    def shutdown(self):
        self.closing=True
        for token in list(self.timers):
            self.root.after_cancel(token)
        self.timers.clear()
        self.pool.shutdown(wait=False)

    def text(self,parent,height=15):
        frame=ttk.Frame(parent); frame.pack(fill='both',expand=True,pady=10)
        box=tk.Text(frame,bg=PANEL,fg=FG,insertbackground=FG,wrap='word',relief='flat',padx=16,pady=14,height=height,font=('Segoe UI',11))
        scroll=ttk.Scrollbar(frame,command=box.yview); box.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right',fill='y'); box.pack(fill='both',expand=True)
        box.configure(state='disabled'); return box

    def display(self,box,value):
        box.configure(state='normal'); box.delete('1.0','end')
        box.insert('end',value if isinstance(value,str) else json.dumps(value,indent=2)); box.configure(state='disabled')

    def work(self,fn,callback=None):
        if self.busy:
            messagebox.showinfo('Working','Wait for the current operation to finish.'); return
        self.busy=True; self.status.set('Working…')
        future=self.pool.submit(fn)
        future.add_done_callback(lambda f:self.results.put((f,callback)))

    def drain(self):
        try:
            future,callback=self.results.get_nowait(); self.busy=False
            try:
                value=future.result()
                if callback: callback(value)
                self.status.set('Completed • Inspect results; no performance improvement is assumed')
            except Exception as e:
                self.action_states={}; self.refresh_actions()
                self.engine.log(str(e)); self.status.set('Operation failed — see error and logs')
                messagebox.showerror('ApexxTweaks',str(e))
        except queue.Empty: pass
        self.schedule(100,self.drain)

    def button(self,parent,text,command):
        b=ttk.Button(parent,text=text,command=command); b.pack(side='left',padx=(0,8),pady=5); return b

    def dashboard(self):
        p=self.pages['Dashboard']; row=ttk.Frame(p); row.pack(fill='x')
        self.button(row,'Inspect system',lambda:self.work(diagnostics.inventory,lambda v:self.display(self.system,v)))
        self.button(row,'Sample background activity',lambda:self.work(lambda:interpret(diagnostics.activity()),lambda v:self.display(self.system,v)))
        self.button(row,'Collect sustained samples',self.collect_samples)
        self.system=self.text(p)
        self.display(self.system,'YOUR SYSTEM, WITHOUT A PERFORMANCE SCORE\n\nInspect CPU, GPU driver, display, RAM, disk health and network interfaces.\n\nActivity sampling is read-only and on demand; it never opens game memory or modifies process priority. CPU process counters can exceed 100% across cores. GPU engine counters are individual engines, not an aggregate GPU bottleneck verdict.\n\n'+('Windows diagnostics require Windows 10/11.' if not WINDOWS else 'Select Inspect system to begin.'))

    def optimize(self):
        p=self.pages['Optimize']
        ttk.Label(p,text='Select individual actions • Review effects and risks • Active state requires read-back').pack(anchor='w')
        row=ttk.Frame(p); row.pack(fill='x')
        self.search=tk.StringVar(); ttk.Entry(row,textvariable=self.search,width=26).pack(side='left',padx=(0,8))
        self.category=tk.StringVar(value='All')
        ttk.Combobox(row,textvariable=self.category,values=['All','Power','Recording','Startup','Background','Tasks','Services'],state='readonly',width=14).pack(side='left')
        self.profile=tk.StringVar(value='Balanced')
        ttk.Combobox(row,textvariable=self.profile,values=list(PROFILES),state='readonly',width=14).pack(side='left',padx=8)
        self.button(row,'Select profile',self.review_profile)
        self.button(row,'Discover optional apps',self.discover_optional)
        table=ttk.Frame(p); table.pack(fill='both',expand=True,pady=(12,0))
        self.action_tree=ttk.Treeview(table,columns=('selected','category','title','state'),show='headings',height=8,selectmode='browse')
        for col,title,width in [('selected','Use',45),('category','Category',90),('title','Action',480),('state','Verified state',160)]:
            self.action_tree.heading(col,text=title); self.action_tree.column(col,width=width,stretch=col=='title')
        scroll=ttk.Scrollbar(table,command=self.action_tree.yview); self.action_tree.configure(yscrollcommand=scroll.set)
        self.action_tree.pack(side='left',fill='both',expand=True); scroll.pack(side='right',fill='y')
        self.action_tree.bind('<<TreeviewSelect>>',self.action_detail)
        self.action_tree.bind('<Double-1>',lambda _:self.toggle_action())
        self.action_tree.bind('<space>',lambda _:self.toggle_action())
        self.choices={}
        self.search.trace_add('write',lambda *_:self.refresh_actions())
        self.category.trace_add('write',lambda *_:self.refresh_actions())
        self.details=self.text(p,height=7)
        row=ttk.Frame(p); row.pack(fill='x')
        self.button(row,'Toggle selected',self.toggle_action)
        self.button(row,'Inspect states',lambda:self.work(self.states,self.update_states))
        self.button(row,'Review & apply',self.apply)
        self.button(row,'Undo selected',self.undo_selected)
        self.button(row,'Restore all',self.restore)
        row=ttk.Frame(p); row.pack(fill='x')
        for name,uri in [('Game Mode','gaming-gamemode'),('Captures','gaming-gamedvr'),('Graphics / GPU choice','display-advancedgraphics'),('Display','display-advanced')]:
            self.button(row,name,lambda u=uri:self.open_settings(u))
        self.refresh_actions()
        self.display(self.details,'Search actions, select a row for the full explanation and double-click or press Space to toggle. Discover optional apps creates only validated current-user targets. Game Mode, Windows 11 Captures and GPU preferences use supported Windows Settings pages; their manual changes are outside the rollback journal.')

    def refresh_actions(self):
        selected=self.action_tree.selection()
        self.action_tree.delete(*self.action_tree.get_children())
        query=self.search.get().casefold(); category=self.category.get()
        for a in self.engine.actions.values():
            self.choices.setdefault(a.id,tk.BooleanVar(value=False))
            if category!='All' and a.category!=category: continue
            if query and query not in (a.title+' '+a.description+' '+a.category).casefold(): continue
            state=self.action_states.get(a.id,'Not inspected')
            owned=any(r['action']==a.id and r['status']!='restored' for r in self.engine.records)
            if owned: state+=' • journaled'
            self.action_tree.insert('', 'end',iid=a.id,values=('☑' if self.choices[a.id].get() else '☐',a.category,branded_text(a.title),state))
        if selected and self.action_tree.exists(selected[0]): self.action_tree.selection_set(selected[0])

    def toggle_action(self):
        selected=self.action_tree.selection()
        if selected:
            v=self.choices[selected[0]]; v.set(not v.get()); self.refresh_actions()

    def action_detail(self,event=None):
        selected=self.action_tree.selection()
        if not selected: return
        a=self.engine.actions[selected[0]]
        self.display(self.details,branded_text(f'{a.title}  [{a.id}]\nState: {self.action_states.get(a.id, "Not inspected")}\n\n{a.description}\nExpected effect: {a.benefit}\nRisk: {a.risk}\nPermissions: {a.permissions}\nRequirements: {a.windows}; {a.hardware}\nEvidence: {a.evidence}\nGaming Mode eligible: {a.session_safe}'))

    def states(self):
        states={}
        for a in self.engine.actions.values():
            try:
                current=self.engine.backend.read(a.target)
                states[a.id]='ACTIVE' if current==a.desired else 'Original / different'
            except Exception as e: states[a.id]='Unavailable: '+str(e)
        return states

    def update_states(self,value):
        self.action_states=value; self.refresh_actions()

    def review_profile(self):
        for key,v in self.choices.items(): v.set(key in PROFILES[self.profile.get()])
        self.refresh_actions()
        messagebox.showinfo('Profile','Balanced makes no automatic changes. Competitive selects the Windows 11 AC power-mode experiment only. On Windows 10, select the classic power-plan trial manually if appropriate. Add only optional apps you explicitly approve. Never select both power methods together.')

    def apply(self):
        ids=[k for k,v in self.choices.items() if v.get()]
        if not ids: messagebox.showinfo('No selection','Select an action to review.'); return
        detail='\n\n'.join(branded_text(self.engine.actions[k].title+'\n'+self.engine.actions[k].risk) for k in ids)
        if messagebox.askyesno('Confirm changes',detail+'\n\nOriginal values will be saved first. This persistent batch is per-action, not all-or-nothing. Apply?'):
            def done(value):
                self.action_states={}; self.refresh_actions(); messagebox.showinfo('Result',value)
            self.work(lambda:'\n'.join(k+': '+self.engine.apply(k) for k in ids),done)

    def undo_selected(self):
        selected=self.action_tree.selection()
        if not selected: return
        records=[r for r in self.engine.records if r['action']==selected[0] and r['status']!='restored']
        if not records: messagebox.showinfo('Undo','No owned change for this action.'); return
        if messagebox.askyesno('Undo', 'Restore the exact original value for this action?'):
            self.work(lambda:self.engine.restore(records[-1]),lambda _:self.update_states({}))

    def discover_optional(self):
        def done(result):
            actions,rejected=result; self.engine.register(actions); self.refresh_actions()
            messagebox.showinfo('Discovery',f'{len(actions)} approved actions available. {len(rejected)} items remained read-only.\nTasks are restricted to approved, explicitly opt-in app-launch task folders. No running tasks are stopped.')
            self.display(self.gamebox,{'available':[a.title for a in actions],'read_only':rejected})
        self.work(discovery.discover,done)

    def collect_samples(self):
        def done(result):
            self.last_telemetry=result
            atomic_json(self.data/'last-telemetry.json',result)
            self.display(self.system,result['analysis'])
        self.work(telemetry.collect,done)

    def restore(self):
        if messagebox.askyesno('Restore','Restore all journaled changes in reverse order? External conflicts will be reported.'):
            self.work(self.engine.restore_all,lambda _:self.history())

    def open_settings(self,uri):
        if not WINDOWS: messagebox.showinfo('Windows required','This opens a Windows Settings page on Windows.'); return
        os.startfile('ms-settings:'+uri)

    def gaming(self):
        p=self.pages['Gaming']; row=ttk.Frame(p); row.pack(fill='x')
        self.button(row,'Hardware-specific Fortnite report',lambda:self.work(lambda:recommendations(diagnostics.inventory(),diagnostics.fortnite()),lambda v:self.display(self.gamebox,v)))
        self.button(row,'Startup & task inventory',lambda:self.work(lambda:classify_inventory(diagnostics.startup()),lambda v:self.display(self.gamebox,v)))
        self.button(row,'Guidance',lambda:self.display(self.gamebox,diagnostics.GUIDANCE))
        self.button(row,'Gaming settings status',lambda:self.work(diagnostics.gaming_settings,lambda v:self.display(self.gamebox,v)))
        self.gamebox=self.text(p); self.display(self.gamebox,diagnostics.GUIDANCE)
        ttk.Label(p,text='Gaming Mode temporarily applies selected session-safe actions from Optimize; restores only its own changes.').pack(anchor='w')
        row=ttk.Frame(p); row.pack(fill='x')
        self.button(row,'Start approved Gaming Mode',self.start_session)
        self.button(row,'End Gaming Mode & restore',self.end_session)
        self.auto_session=tk.BooleanVar(value=False)
        ttk.Checkbutton(p,text='Watch Fortnite executable names; restore after observed game exits (5-second polling)',variable=self.auto_session,command=self.toggle_watcher).pack(anchor='w')

    def arm_watcher(self):
        if not self.watcher_pending and self.auto_session.get() and self.session.active:
            self.watcher_pending=True
            self.schedule(5000,self.poll_session)

    def toggle_watcher(self):
        self.arm_watcher()

    def start_session(self):
        if self.session.active: return
        ids=[k for k,v in self.choices.items() if v.get() and self.engine.actions[k].session_safe]
        if not ids: messagebox.showinfo('Gaming Mode','Select session-safe Power, Background or Tasks actions in Optimize. Startup and recording-policy actions are persistent-only.'); return
        details='\n\n'.join(branded_text(self.engine.actions[k].title+'\n'+self.engine.actions[k].risk) for k in ids)
        if messagebox.askyesno('Gaming Mode review',details+'\n\nPersistent-only selections are excluded. Apply temporarily? Failures trigger rollback of this session only.'):
            def started(_):
                self.action_states={}; self.refresh_actions()
                if self.auto_session.get(): self.arm_watcher()
            self.work(lambda:self.session.start(ids),started)

    def poll_session(self):
        self.watcher_pending=False
        if not self.session.active or not self.auto_session.get(): return
        if self.busy:
            self.arm_watcher(); return
        def detected(result):
            if result.get('error'):
                self.auto_session.set(False)
                messagebox.showwarning('Watcher stopped',result['error']+'\nGaming Mode remains active. End it manually to restore.')
            elif result['ended']: self.update_states({})
            elif self.session.active: self.arm_watcher()
        def poll():
            try: return {'ended':self.session.observe(diagnostics.fortnite_running())}
            except Exception as error: return {'error':str(error)}
        self.work(poll,detected)

    def end_session(self):
        if self.session.active:
            def done(_):
                self.action_states={}; self.refresh_actions()
                if self.close_after_session: self.close()
            self.work(self.session.end,done)

    def bench(self):
        p=self.pages['Benchmark']; row=ttk.Frame(p); row.pack(fill='x')
        for label in ['Before','After']:
            self.button(row,'Import '+label+' CSV',lambda l=label:self.import_run(l))
        self.button(row,'Compare repeated runs',self.compare)
        self.button(row,'Export results',self.export)
        self.button(row,'New experiment',self.new_experiment)
        row=ttk.Frame(p); row.pack(fill='x')
        ttk.Label(row,text='Matched experiment context (scene / hardware / graphics / cap):').pack(side='left')
        self.context=tk.StringVar(value='')
        ttk.Entry(row,textvariable=self.context,width=52).pack(side='left',padx=8)
        self.benchbox=self.text(p,height=9)
        self.display(self.benchbox,'Import a single-process, single-swapchain CSV with frame times in milliseconds. Minimum 1000 frames.\n\nUse external captures only where permitted. This app does not install or launch capture tools.\nMatch scene, resolution, rendering mode, cap, temperatures and duration; warm up shaders. Capture at least three runs per condition. Record the applied changes in your run label. 0.1% lows are noisy with short runs.\n\nLows = 1000 / mean of slowest 1% or 0.1% of frame times. No input latency is inferred.')
        self.chart=tk.Canvas(p,height=180,bg=PANEL,highlightthickness=0); self.chart.pack(fill='x')

    def import_run(self,label):
        path=filedialog.askopenfilename(filetypes=[('Frame-time CSV','*.csv')])
        if not path: return
        context=self.context.get().strip()
        if not context:
            messagebox.showinfo('Context required','Enter a matched experiment context before importing.'); return
        def done(result):
            if any(r.get('source_sha256')==result['source_sha256'] for runs in self.runs.values() for r in runs):
                raise ValueError('This exact CSV is already imported. Re-importing one capture is not an independent repeat run.')
            result['context']=context
            result['source']=Path(path).name
            result['changes']=[r['action'] for r in self.engine.records if r['status']=='applied']
            self.runs[label].append(result); atomic_json(self.data/'benchmarks.json',self.runs)
            self.display(self.benchbox,result); self.draw(result['histogram'])
        self.work(lambda:benchmark.load_csv(path),done)

    def draw(self,hist):
        self.chart.delete('all'); width=max(self.chart.winfo_width(),700)
        labels=['<4','4–8','8–12','12–16.7','16.7–25','25–50','≥50']
        peak=max(hist) or 1
        for i,(n,label) in enumerate(zip(hist,labels)):
            x=25+i*(width-40)/7; w=(width-40)/7-15; h=n/peak*115
            self.chart.create_rectangle(x,140-h,x+w,140,fill=ACCENT,outline='')
            self.chart.create_text(x+w/2,155,text=label+' ms',fill=FG)
            self.chart.create_text(x+w/2, max(12,130-h),text=str(n),fill=MUTED)

    def compare(self):
        def done(result):
            self.display(self.benchbox,result); self.draw_comparison(result)
        self.work(lambda:benchmark.advanced_compare(self.runs['Before'],self.runs['After']),done)

    def draw_comparison(self,report):
        self.chart.delete('all')
        width=max(self.chart.winfo_width(),700)
        for i,(key,metric) in enumerate(report['metrics'].items()):
            y=18+i*42; unit='ms' if key=='p99_ms' else 'FPS'
            self.chart.create_text(10,y+7,text=key,fill=FG,anchor='w')
            peak=max(metric['before_mean'],metric['after_mean']) or 1
            available=max(100,width-420)
            for j,(label,color) in enumerate([('before_mean',MUTED),('after_mean',ACCENT)]):
                length=metric[label]/peak*available
                self.chart.create_rectangle(140,y+j*12,140+length,y+9+j*12,fill=color,outline='')
            self.chart.create_text(width-260,y+8,anchor='w',text=f"{metric['before_mean']:.2f} → {metric['after_mean']:.2f} {unit} ({metric['percent']:+.1f}%)",fill=FG)
        self.chart.create_text(10,178,anchor='w',text='Gray: before • Mint: after • Each row has its own scale • Bootstrap intervals in report',fill=MUTED)

    def new_experiment(self):
        if self.busy: return
        if messagebox.askyesno('Archive experiment','Archive current runs and start an empty Before/After experiment? Backups and action history are preserved.'):
            import time
            atomic_json(self.data/('benchmarks-archive-'+str(time.time_ns())+'.json'),self.runs)
            self.runs={'Before':[],'After':[]}
            atomic_json(self.data/'benchmarks.json',self.runs)
            self.context.set(''); self.chart.delete('all')
            self.display(self.benchbox,'New experiment ready. Set a matched context before importing.')

    def export(self):
        path=filedialog.asksaveasfilename(defaultextension='.json')
        if path:
            atomic_json(Path(path),{'runs':self.runs,'history':self.engine.records,'telemetry':self.last_telemetry})

    def advanced(self):
        p=self.pages['Advanced']; row=ttk.Frame(p); row.pack(fill='x')
        ttk.Label(row,text='ICMP target:').pack(side='left'); self.host=tk.StringVar(value='')
        ttk.Entry(row,textvariable=self.host,width=28).pack(side='left',padx=8)
        self.button(row,'Probe 20 packets',self.probe)
        self.netbox=self.text(p)
        self.display(self.netbox,'Probe your local gateway first, then an authorized remote endpoint. ICMP loss may reflect filtering, not game packet loss. Jitter here is mean absolute difference of consecutive successful RTTs (successful replies, including across loss gaps).\n\nNo TCP registry tweaks, adapter writes, timer hacks, priorities, memory cleaners, security changes, injection or kernel components.\n\nThermal throttling and CPU/GPU bottleneck causality cannot be determined from one snapshot. Compare repeated external captures and per-core utilization. The app intentionally makes no automatic causal diagnosis.')

    def probe(self):
        target=self.host.get()
        self.work(lambda:diagnostics.network(target),lambda v:self.display(self.netbox,v))

    def settings(self):
        p=self.pages['Settings']; row=ttk.Frame(p); row.pack(fill='x')
        self.button(row,'History / recovery',self.history)
        self.button(row,'Undo latest action',self.undo)
        self.button(row,'Restore original settings',self.restore)
        self.button(row,'Offer restore point',self.restore_point)
        self.historybox=self.text(p)
        self.display(self.historybox,f'Backups and logs: {self.data}\n\nRestore points are optional, may require an administrator and System Protection, and may be rate limited. Per-action snapshots are always required before a write.\n\nThe application never silently elevates. For Fax changes or restore points, explicitly run as administrator only if needed. Do not run two instances. Logs and exports may contain local paths/usernames; review before sharing.\n\nClosing an active manual session restores its owned session changes. Interrupted operations remain in the journal for recovery next launch.')

    def history(self):
        self.action_states={}; self.refresh_actions()
        self.display(self.historybox,self.engine.records)
    def undo(self):
        records=[r for r in self.engine.records if r['status']!='restored']
        if records and messagebox.askyesno('Undo', 'Restore '+records[-1]['action']+'?'):
            self.work(lambda:self.engine.restore(records[-1]),lambda _:self.history())
    def restore_point(self):
        if messagebox.askyesno('Restore point','Ask Windows to create a restore point? Administrator and System Protection may be required.'):
            self.work(lambda:powershell("Checkpoint-Computer -Description 'ApexxTweaks user-requested checkpoint' -RestorePointType MODIFY_SETTINGS"),lambda _:messagebox.showinfo('Windows','Checkpoint command completed. Check System Protection for availability.'))
    def close(self):
        if self.busy:
            messagebox.showinfo('Working','Wait for the operation before closing.'); return
        if self.session.active:
            self.close_after_session=True
            self.end_session(); return
        self.shutdown(); self.root.destroy()

def main(smoke=False):
    root=tk.Tk()
    # Single-instance lock prevents concurrent journals and overlapping changes.
    lock=None
    if WINDOWS:
        import ctypes
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.CreateMutexW.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_wchar_p]
        kernel.CreateMutexW.restype=ctypes.c_void_p
        lock=kernel.CreateMutexW(None,False,JOURNAL_MUTEX)
        if not lock or ctypes.get_last_error()==183:
            messagebox.showerror('ApexxTweaks','ApexxTweaks is already running or cannot acquire its journal lock.'); root.destroy(); return
    try:
        app=App(root)
        if smoke:
            root.withdraw(); root.update()
            app.draw([1,2,3,4,5,6,7]); root.update()
            app.shutdown(); root.destroy()
        else: root.mainloop()
    finally:
        if lock:
            import ctypes
            close=ctypes.WinDLL('kernel32').CloseHandle; close.argtypes=[ctypes.c_void_p]; close(lock)
