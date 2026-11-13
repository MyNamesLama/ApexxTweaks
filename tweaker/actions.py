from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class Action:
    id: str
    title: str
    target: str
    desired: Any
    description: str
    benefit: str
    risk: str
    permissions: str
    hardware: str
    windows: str = 'Windows 10 2004+ / Windows 11'
    evidence: str = 'Hardware-dependent; benchmark required'
    category: str = 'Power'
    session_safe: bool = False

ACTIONS = {
    a.id: a for a in [
        Action('power.high', 'Test High performance power plan', 'power',
               '8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c',
               'Switches to the existing Windows High performance scheme. Fails safely if unavailable; does not create or edit plans.',
               'May reduce frequency ramp delays; often no gaming benefit on modern CPUs.',
               'Moderate: higher heat, fan noise and battery drain; may worsen thermal throttling.',
               'Standard user where permitted by policy', 'AC-powered system with an existing High performance plan', session_safe=True),
        Action('service.fax', 'Disable unused Fax startup', 'fax', 'Disabled',
               'Disables startup of the stopped Fax service only if no dependent services exist. Never stops a service.',
               'Avoids optional fax startup only; normally no measurable FPS benefit.',
               'Low: fax functionality unavailable until restored. Select only if you never use fax.',
               'Administrator; application never elevates automatically', 'Fax service installed, stopped, no dependents',
               evidence='Functionality tradeoff; no FPS claim', category='Services')
    ]
}
ACTIONS['power.ac-performance'] = Action(
    'power.ac-performance', 'Test Best performance AC power mode', 'ac-mode',
    'ded574b5-45a0-4f42-8737-46345c09c238',
    'Uses the documented Windows user-configured AC power-mode API; does not change battery mode or CPU affinity.',
    'May reduce power-saving scheduling delays; effective mode can be overridden by system thermal/power signals.',
    'Moderate: increased energy, heat and fan activity. Compare sustained frame times; may regress on thermally limited systems.',
    'Standard user where policy permits', 'Windows 11 API available, AC connected, Balanced base plan',
    windows='Windows 11 with exported API', category='Power', session_safe=True)
ACTIONS['capture.policy-off'] = Action(
    'capture.policy-off', 'Disable Windows game recording policy (Windows 10)', 'recording-policy',
    {'exists':True,'type':4,'value':0},
    'Applies documented AllowGameDVR=0 policy on eligible unmanaged Windows 10 desktop editions. No Game Bar removal.',
    'Removes Windows game-recording activity if it was active; no benefit when recording was already idle.',
    'Moderate: disables game recording/broadcasting for all users. Restart game/sign out may be required; registry verification does not prove recorder stopped.',
    'Administrator', 'Unmanaged Windows 10 Pro/Enterprise/Education; Windows 11 uses guided Captures Settings',
    windows='Windows 10 2004–22H2 desktop Pro+', category='Recording')
PROFILES = {'Balanced': [], 'Competitive': ['power.ac-performance'], 'Custom': []}

def optional_action(kind, target, title, desired):
    from .targets import identifier
    descriptions = {
        'startup': ('Remove only the selected current-user Run value; save its exact type and command for undo.',
                    'Prevents this optional app starting at the next sign-in, reducing its idle resource cost.',
                    'Low: automatic app launch stops. Does not stop an already running app. App updates can recreate the entry.'),
        'task': ('Disable an opt-in current-user non-elevated direct app-launch task under \\FrameWiseOptional\\; never stop a running task.',
                 'Prevents an explicitly selected optional app being launched during play.',
                 'Low: selected launch automation will not run until restored. Existing running instances are unaffected.'),
        'eco': ('Enable only the execution-speed EcoQoS bit on this signed optional app instance using SetProcessInformation.',
                'Can reduce competing background CPU energy/activity on compatible CPUs. Not a CPU cap or guaranteed FPS gain.',
                'Moderate: the selected app can slow down or stutter, including voice/music. No suspension, termination or priority changes.')}
    description, benefit, risk = descriptions[kind]
    return Action(identifier(kind,target),title,target,desired,description,benefit,risk,
                  'Current-user app permissions; no automatic elevation',
                  'Verified Spotify/Discord signed executable; exact identity rechecked before writes',
                  windows='Windows 11' if kind=='eco' else 'Windows 10 2004+ / Windows 11',
                  category={'startup':'Startup','task':'Tasks','eco':'Background'}[kind],session_safe=kind in ('task','eco'))

