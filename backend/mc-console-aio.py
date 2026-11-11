#!/usr/bin/env python3
"""Supplemental terminal UI for the Cockpit-managed Minecraft helper.
Uses the existing mc-console helper for server discovery and RCON.
"""
import datetime
import json
import os
import pathlib
import re
import shlex
import shutil
import socket
import struct
import subprocess
import sys
import time

CFG = pathlib.Path('/etc/mc-console-aio.json')
MINECRAFT_HOME = pathlib.Path('/opt/minecraft')
DEFAULT_BACKUP_CANDIDATES = [
    '/var/lib/cockpit-minecraft/backups/restic-repo',
    '/var/lib/cockpit-minecraft/backups',
    '/opt/minecraft/backups',
    '/var/backups/cockpit-minecraft',
    '/var/lib/cockpit-minecraft/backups',
]


def load_config():
    try:
        data = json.loads(CFG.read_text()) if CFG.is_file() else {}
        if not isinstance(data, dict):
            return {}
        return data
    except (OSError, ValueError) as exc:
        print('Warning: cannot read AIO config: ' + str(exc), file=sys.stderr)
        return {}


def clean(value):
    return re.sub(r'§[0-9a-fk-orx]', '', str(value), flags=re.I)


def servers(helper):
    data = helper('list')
    if not isinstance(data, list):
        raise RuntimeError('Minecraft helper did not return a server list')
    return data


def find_server(items, sid):
    for item in items:
        if item.get('id') == sid:
            return item
    raise RuntimeError('Unknown server ID: ' + sid + '. Run mc-console list.')


def active(s):
    return s.get('state') == 'active'


def unit_for(s):
    unit = s.get('unit')
    if not isinstance(unit, str) or not re.fullmatch(r'[A-Za-z0-9_.@:-]+\.service', unit):
        raise RuntimeError('No valid systemd unit reported for ' + str(s.get('id')))
    return unit


def status_values(unit):
    result = subprocess.run(['systemctl','show',unit,
        '--property=ActiveState,SubState,MainPID,MemoryCurrent,ExecMainStartTimestamp,CPUUsageNSec',
        '--no-pager'], text=True, capture_output=True, timeout=8)
    return dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)


def ping_mc(host, port, timeout=1.5):
    """Vanilla Minecraft Java status query; only best-effort, no credentials."""
    def varint(n):
        out = bytearray()
        while True:
            b = n & 127
            n >>= 7
            out.append(b | (128 if n else 0))
            if not n: return bytes(out)
    def readvar(sock):
        num = 0
        for i in range(5):
            c = sock.recv(1)
            if not c: raise OSError('Closed')
            num |= (c[0] & 127) << (7*i)
            if not (c[0] & 128): return num
        raise OSError('Invalid VarInt')
    def recvbytes(sock, n):
        buf = bytearray()
        while len(buf) < n:
            chunk = sock.recv(n-len(buf))
            if not chunk: raise OSError('Closed')
            buf.extend(chunk)
        return bytes(buf)
    port = int(port)
    if not 1 <= port <= 65535: return None
    with socket.create_connection((host, port), timeout=timeout) as sock:
        sock.settimeout(timeout)
        name = host.encode('utf-8')
        payload = b'\x00' + varint(760) + varint(len(name)) + name + struct.pack('>H', port) + b'\x01'
        sock.sendall(varint(len(payload)) + payload + b'\x01\x00')
        length = readvar(sock)
        if not 1 <= length <= 1048576: return None
        if readvar(sock) != 0: return None
        n = readvar(sock)
        if n > 1048576: return None
        raw = recvbytes(sock, n)
        return json.loads(raw.decode('utf-8'))


def mc_info(s):
    if not active(s): return None
    try:
        return ping_mc('127.0.0.1', s.get('port'), 1)
    except (ValueError, KeyError, OSError, json.JSONDecodeError):
        return None


def fmt_bytes(n):
    try:
        n = float(n)
        if n < 0 or n > 10**18: return '-'
        for suffix in ('B','KiB','MiB','GiB','TiB'):
            if n < 1024 or suffix == 'TiB': return f'{n:.1f} {suffix}'
            n /= 1024
    except (ValueError, TypeError):
        return '-'


def show_list(helper):
    items = servers(helper)
    print('\nCOCKPIT-MANAGED MINECRAFT SERVERS')
    print('=' * 95)
    print(f"{'SERVER':<24} {'STATE':<10} {'TYPE/VERSION':<25} {'PLAYERS':<10} {'PORT':<7} {'RCON'}")
    print('-' * 95)
    for s in items:
        info = mc_info(s)
        version = (info or {}).get('version', {}).get('name') if info else None
        label = clean(version or s.get('label') or '-')[:25]
        count = (info or {}).get('players', {}) if info else {}
        people = f"{count.get('online','?')}/{count.get('max','?')}" if info else '-'
        state = 'RUNNING' if active(s) else str(s.get('state','STOPPED')).upper()
        print(f"{str(s.get('id'))[:24]:<24} {state[:10]:<10} {label:<25} {people:<10} {str(s.get('port','-')):<7} {'ready' if s.get('rcon') else 'not configured'}")
    print('-' * 95)
    if not items:
        print('No managed servers were returned by Cockpit.')
    else:
        print('Stopped server: mc-console start SERVER_ID')
        print('Running server: mc-console console SERVER_ID')
        print('Backup locations: mc-console backups [SERVER_ID]\n')


def show_status(helper, sid):
    s = find_server(servers(helper), sid)
    unit = unit_for(s)
    meta = status_values(unit)
    info = mc_info(s)
    print('\nSERVER STATUS: ' + sid)
    print('=' * 65)
    print('Cockpit state :', s.get('state','unknown'))
    print('Service       :', unit)
    print('Systemd       :', meta.get('ActiveState','?') + '/' + meta.get('SubState','?'))
    print('Configured port:', s.get('port','-'))
    print('RCON          :', 'configured' if s.get('rcon') else 'not configured')
    print('Started       :', meta.get('ExecMainStartTimestamp','-'))
    print('MemoryCurrent :', fmt_bytes(meta.get('MemoryCurrent')))
    pid = meta.get('MainPID','0')
    if pid.isdigit() and int(pid) > 0:
        p = subprocess.run(['ps','-p',pid,'-o','%cpu=,rss=,etime=,comm='],capture_output=True,text=True,timeout=5)
        if p.stdout.strip(): print('Service process:', p.stdout.strip(), '(CPU%, RSS KiB, elapsed, command)')
    if info:
        print('Version       :', clean(info.get('version', {}).get('name','unknown')))
        pop = info.get('players', {})
        print('Players       :', f"{pop.get('online','?')}/{pop.get('max','?')}")
    else:
        print('Status ping   : unavailable (may be starting, modded, or restricted)')
    print()


def run_systemctl(action, s):
    unit = unit_for(s)
    proc = subprocess.run(['sudo','systemctl',action,unit], check=False)
    if proc.returncode != 0: raise RuntimeError('systemctl ' + action + ' failed; inspect mc-console errors ' + s['id'])
    state = subprocess.run(['systemctl','is-active',unit],capture_output=True,text=True,timeout=6)
    print(f"{s['id']} -> {state.stdout.strip() or 'unknown'} (service {unit})")


def confirm(prompt):
    return input(prompt + ' [y/N]: ').strip().lower() == 'y'


def manage(helper, action, sid, force=False, delay=10):
    items = servers(helper)
    s = find_server(items, sid)
    running = active(s)
    if action == 'start' and running:
        print(sid + ' is already running.')
        return
    if action == 'stop' and not running:
        print(sid + ' is already stopped.')
        return
    if action == 'restart' and not running:
        raise RuntimeError('Server is stopped. Use: mc-console start ' + sid)
    if action == 'start':
        conflicts = [str(x.get('id')) for x in items if x.get('id') != sid and active(x) and str(x.get('port')) == str(s.get('port'))]
        if conflicts: raise RuntimeError('Configured port conflict with: ' + ', '.join(conflicts) + '. Use Cockpit switch if intended.')
    if action in ('stop','restart'):
        if not confirm(f'{action.capitalize()} running server {sid}?'):
            print('Cancelled.'); return
        if not force:
            if not s.get('rcon'):
                raise RuntimeError('No configured RCON; cannot warn/save. Retry explicitly with --force to use systemd graceful stop.')
            try:
                helper('command',sid, 'say [Server] Scheduled '+action+' in '+str(delay)+' seconds. Please find a safe place.')
                if delay: print(f'Waiting {delay}s to let players prepare...'); time.sleep(delay)
                helper('command',sid,'save-all flush')
                print('World save command acknowledged.')
            except Exception as exc:
                raise RuntimeError('Could not confirm player warning/save: ' + str(exc) + '. No stop attempted. Retry --force only if safe.')
        else:
            print('FORCE MODE: skipping RCON warning/save; systemd stop still used.')
    print(f'{action.capitalize()}ing {sid} through its Cockpit-managed systemd unit...')
    run_systemctl(action,s)


def log_output(sid, helper, count=60, errors_only=False, follow=False):
    s = find_server(servers(helper),sid)
    unit = unit_for(s)
    cmd = ['sudo','journalctl','-u',unit,'--no-pager','-n',str(max(1,min(count,500)))]
    if follow: cmd += ['-f']
    if not errors_only or follow:
        subprocess.run(cmd,check=False)
    else:
        p = subprocess.run(cmd,capture_output=True,text=True,timeout=12)
        lines = [ln for ln in p.stdout.splitlines() if re.search(r'\b(warn|error|exception|failed|crash|fatal)\b',ln,re.I)]
        print('\n'.join(lines) if lines else 'No matching warning/error lines in last '+str(count)+' journal entries.')


def directory_summary(path):
    try:
        if not path.exists(): return 'absent'
        if not path.is_dir(): return 'file'
        examples=[]
        with os.scandir(path) as scan:
            for entry in scan:
                if entry.name.startswith('.'): continue
                examples.append(entry.name + ('/' if entry.is_dir(follow_symlinks=False) else ''))
                if len(examples) == 5: break
        return 'present; examples: ' + (', '.join(examples) if examples else '(empty or hidden only)')
    except (OSError, PermissionError): return 'present; permission restricted'


def get_backup_dirs(s):
    cfg = load_config()
    result = list(DEFAULT_BACKUP_CANDIDATES)
    sid = str(s.get('id','')) if s else ''
    if sid and re.fullmatch(r'[A-Za-z0-9_.-]+',sid):
        result.extend([
            '/opt/minecraft/managed/'+sid+'/backups',
            '/opt/minecraft/managed/'+sid+'/backup',
            '/var/lib/cockpit-minecraft/backups/'+sid,
            '/var/lib/cockpit-minecraft/backups/'+sid,
        ])
    for val in cfg.get('backup_paths', []):
        if isinstance(val,str) and val.startswith('/'): result.append(val)
    if sid:
        for val in cfg.get('server_backup_paths',{}).get(sid,[]):
            if isinstance(val,str) and val.startswith('/'): result.append(val)
    return list(dict.fromkeys(result))


def backups(helper, sid=None):
    s = find_server(servers(helper), sid) if sid else None
    print('\nMINECRAFT BACKUP LOCATIONS' + (' — '+sid if sid else ''))
    print('='*75)
    print('Locations are discovered candidates; only PRESENT paths are confirmed.')
    print('Cockpit backup scheduling and archive integrity are NOT inferred here.\n')
    for p in get_backup_dirs(s):
        path = pathlib.Path(p)
        print(('PRESENT ' if path.exists() else 'MISSING ') + str(path))
        if path.exists(): print('         ' + directory_summary(path))
    print('\nFor authoritative Cockpit backup destination/settings, check its backup module.')
    print('To register another actual path, edit root-owned '+str(CFG))
    print('To run a configured backup hook: mc-console backup-run SERVER_ID')


def backup_run(helper,sid):
    s = find_server(servers(helper),sid)
    cfg = load_config()
    hook = cfg.get('backup_commands',{}).get(sid)
    if not isinstance(hook,list) or not hook or not all(isinstance(x,str) and x for x in hook):
        raise RuntimeError('No verified backup command configured for '+sid+'. Inspect Cockpit backup settings and /etc/mc-console-aio.json. No action taken.')
    if not confirm('Run the configured existing backup command for '+sid+'?'):
        print('Cancelled.'); return
    cmd = [x.replace('{server_id}',sid) for x in hook]
    print('Running configured backup hook (no shell):',shlex.join(cmd))
    subprocess.run(['sudo',*cmd],check=True)


def doctor(helper,sid):
    s = find_server(servers(helper),sid)
    unit=unit_for(s)
    state=status_values(unit)
    print('\nSERVER DOCTOR: '+sid+'\n'+'='*68)
    print('Systemd active:',state.get('ActiveState','unknown'))
    print('Cockpit state:',s.get('state','unknown'))
    print('Port:',s.get('port','unknown'))
    info=mc_info(s)
    print('Minecraft status ping:','OK — '+clean(info.get('version',{}).get('name','')) if info else 'unavailable')
    print('RCON configured:', 'yes' if s.get('rcon') else 'no')
    try:
        subprocess.run(['java','-version'],capture_output=True,text=True,timeout=4,check=False)
        print('Java executable:',shutil.which('java') or 'not in PATH')
    except (OSError,subprocess.TimeoutExpired): print('Java executable: unavailable')
    other=[str(x.get('id')) for x in servers(helper) if x.get('id')!=sid and active(x) and str(x.get('port'))==str(s.get('port'))]
    print('Other active servers using configured port:',', '.join(other) if other else 'none')
    print('Known backup paths:')
    for p in get_backup_dirs(s):
        if pathlib.Path(p).exists(): print('  '+p)
    print('\nRecent service warnings:')
    log_output(sid,helper,count=100,errors_only=True)


def history_path():
    home=pathlib.Path.home()
    return home/'.local/state/mc-console/history'


def interactive_console(helper,sid):
    s=find_server(servers(helper),sid)
    if not active(s): raise RuntimeError('Server is not running: '+sid)
    if not s.get('rcon'): raise RuntimeError('RCON is not configured: '+sid)
    try:
        import readline
        history=history_path()
        if history.exists(): readline.read_history_file(str(history))
    except (ImportError,OSError):
        readline=None
    print('Connected to '+clean(s.get('label',sid))+'. Type exit/quit to leave.')
    try:
        while True:
            try: line=input(sid+'> ').strip()
            except (EOFError,KeyboardInterrupt): print(); break
            if line.lower() in ('exit','quit'): break
            if not line: continue
            try: print(clean(helper('command',sid,line)))
            except Exception as exc: print('Error: '+str(exc),file=sys.stderr)
    finally:
        if readline:
            try:
                history=history_path(); history.parent.mkdir(parents=True,exist_ok=True)
                readline.write_history_file(str(history)); history.chmod(0o600)
            except OSError: pass


def dashboard(helper):
    print('Minecraft Server Manager — Cockpit-backed terminal dashboard')
    while True:
        try:
            items=servers(helper)
            print('\n'+'='*66)
            for i,s in enumerate(items,1):
                print(f" {i:>2}) {s.get('id','?'):<28} {'RUNNING' if active(s) else 'STOPPED':<9} port {s.get('port','-')}")
            print(' L) List details    B) Backup locations    Q) Quit')
            selection=input('Select server number or action: ').strip().lower()
            if selection in ('q','quit','exit'): break
            if selection=='l': show_list(helper); continue
            if selection=='b': backups(helper); continue
            if not selection.isdecimal() or not 1<=int(selection)<=len(items):
                print('Invalid selection.'); continue
            sid=items[int(selection)-1]['id']
            while True:
                print('\n'+sid+' — 1) Status 2) Console 3) Start 4) Stop 5) Restart')
                print('             6) Logs 7) Errors 8) Doctor 9) Backups 0) Back')
                choice=input('Action: ').strip().lower()
                if choice in ('0','q','back'): break
                try:
                    if choice=='1': show_status(helper,sid)
                    elif choice=='2': interactive_console(helper,sid)
                    elif choice=='3': manage(helper,'start',sid)
                    elif choice=='4': manage(helper,'stop',sid)
                    elif choice=='5': manage(helper,'restart',sid)
                    elif choice=='6': log_output(sid,helper,follow=True)
                    elif choice=='7': log_output(sid,helper,errors_only=True)
                    elif choice=='8': doctor(helper,sid)
                    elif choice=='9': backups(helper,sid)
                    else: print('Unknown action.')
                except (RuntimeError,ValueError,OSError,subprocess.SubprocessError) as exc:
                    print('ERROR:',exc,file=sys.stderr)
        except (EOFError,KeyboardInterrupt): print(); break


def help_menu():
    print('''
MINECRAFT SERVER MANAGER — AIO (Cockpit-backed)
===================================================
SERVER DISCOVERY & CONTROL
  mc-console                  Interactive server dashboard
  mc-console dashboard        Same interactive dashboard
  mc-console list             Server list, type/version, player counts, RCON
  mc-console status ID        Service state, memory, uptime, version, players
  mc-console start ID         Start a stopped server (port-conflict check)
  mc-console stop ID          Warn players, save world, stop through systemd
  mc-console restart ID       Warn players, save world, restart through systemd
  mc-console stop ID --force  Skip RCON safety if unavailable (confirm required)

CONSOLE, DIAGNOSTICS & LOGS
  mc-console ID               Connect to interactive RCON (command history)
  mc-console console ID       Same interactive console
  mc-console send ID COMMAND  Send one RCON command (original command)
  mc-console logs ID          Follow live systemd logs (original command)
  mc-console recent ID [N]    Show last N log lines (default 60, max 500)
  mc-console errors ID        Show recent errors/warnings
  mc-console doctor ID        Health and startup diagnostics

BACKUPS (EXISTING COCKPIT BACKUPS; NO WORLD DATA DUPLICATION)
  mc-console backups [ID]     Show confirmed and potential backup locations
  mc-console backup-run ID    Invoke an explicitly configured backup command
                              (refuses if no hook configured)

OTHER EXISTING COMMANDS
  mc-console switch ID        Existing Cockpit server-switch workflow
  mc-console enable-rcon ID   Existing RCON setup workflow
  mc-console help             This reference

SAFETY
  - Cockpit helper remains authoritative for server inventory and RCON.
  - Safe stop/restart asks for confirmation, warns players and requests save.
  - --force skips the pre-stop RCON warning/save; systemd still manages stop.
  - Backup location entries are not proof an archive is complete.
  - Configure real backup paths/hooks in /etc/mc-console-aio.json.
  - Minecraft world/server backup data is not copied by this addon.
''')


def dispatch(args,helper):
    if not args or args[0] in ('dashboard','menu'):
        dashboard(helper); return True
    action=args[0]
    if action=='help': help_menu(); return True
    if action=='list': show_list(helper); return True
    if action=='status' and len(args)==2: show_status(helper,args[1]); return True
    if action in ('start','stop','restart'):
        if len(args)<2 or len(args)>3 or (len(args)==3 and args[2]!='--force'):
            raise RuntimeError('Usage: mc-console '+action+' SERVER_ID [--force]')
        manage(helper,action,args[1],force='--force' in args); return True
    if action in ('backups','backup-info') and len(args) <= 2:
        backups(helper,args[1] if len(args)==2 else None); return True
    if action=='backup-run' and len(args)==2: backup_run(helper,args[1]); return True
    if action=='doctor' and len(args)==2: doctor(helper,args[1]); return True
    if action=='recent' and 2<=len(args)<=3:
        count=int(args[2]) if len(args)==3 else 60
        log_output(args[1],helper,count=count); return True
    if action=='errors' and len(args)==2: log_output(args[1],helper,errors_only=True); return True
    if action=='console' and len(args)==2: interactive_console(helper,args[1]); return True
    # Preserve all original handlers (send/logs/switch/enable-rcon/open).
    if len(args)==1 and action not in ('send','logs','switch','enable-rcon','open'):
        ids=[s.get('id') for s in servers(helper)]
        if action in ids: interactive_console(helper,action); return True
    return False
