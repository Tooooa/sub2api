#!/usr/bin/env python3
"""Install a small LaunchAgent; keep runtime, state and backups on external storage."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import plistlib
import shlex
import shutil
import subprocess
import sys

LABEL = 'com.toooa.sub2api.account-auth-alerts'


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True)
    parser.add_argument('--runtime-dir', required=True)
    parser.add_argument('--backup-dir', required=True)
    args = parser.parse_args()
    config_path = Path(args.config).expanduser().resolve()
    config = json.loads(config_path.read_text())
    runtime = Path(args.runtime_dir).expanduser().resolve()
    backups = Path(args.backup_dir).expanduser().resolve()
    runtime.mkdir(parents=True, exist_ok=True)
    backups.mkdir(parents=True, exist_ok=True)
    launcher_dir = Path.home() / 'Library/Application Support/mini-relay/launchd-scripts'
    launcher_dir.mkdir(parents=True, exist_ok=True)
    agent_dir = Path.home() / 'Library/LaunchAgents'
    agent_dir.mkdir(parents=True, exist_ok=True)
    launcher = launcher_dir / 'sub2api-account-auth-alerts.sh'
    log = launcher_dir / 'sub2api-account-auth-alerts.log'
    plist = agent_dir / (LABEL + '.plist')
    files = [launcher, plist, runtime / 'monitor.py', runtime / 'README.md']
    stamp = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    saved = []
    for index, file in enumerate(files):
        if file.exists():
            destination = backups / (str(index) + '-' + file.name + '.' + stamp)
            shutil.copy2(file, destination)
            saved.append(str(destination))
    source = Path(__file__).resolve().parent
    for name in ['monitor.py', 'README.md']:
        if (source / name).resolve() != (runtime / name).resolve():
            shutil.copy2(source / name, runtime / name)
    python = str(Path(sys.executable).resolve())
    launch_text = '#!/bin/bash\nset -euo pipefail\numask 077\n'
    launch_text += 'if [ -f ' + shlex.quote(str(log)) + ' ] && [ "$(/usr/bin/stat -f %z ' + shlex.quote(str(log)) + ')" -gt 1048576 ]; then\n  : > ' + shlex.quote(str(log)) + '\nfi\n'
    launch_text += 'exec ' + ' '.join(shlex.quote(p) for p in [python, str(runtime / 'monitor.py'), '--config', str(config_path), '--send']) + '\n'
    launcher.write_text(launch_text)
    launcher.chmod(0o700)
    subprocess.run(['/bin/bash', '-n', str(launcher)], check=True)
    environment = {'PATH': '/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:' + str(Path.home() / '.local/bin')}
    if config.get('lark_cli'):
        environment['LARK_CLI'] = config['lark_cli']
        environment['PATH'] = str(Path(config['lark_cli']).parent) + ':' + environment['PATH']
    data = {'Label': LABEL, 'ProgramArguments': ['/bin/bash', str(launcher)],
            'RunAtLoad': True, 'StartInterval': 300, 'ThrottleInterval': 30,
            'ProcessType': 'Background', 'EnvironmentVariables': environment,
            'StandardOutPath': str(log), 'StandardErrorPath': str(log)}
    with plist.open('wb') as file:
        plistlib.dump(data, file)
    subprocess.run(['/usr/bin/plutil', '-lint', str(plist)], check=True)
    target = 'gui/' + str(os.getuid())
    subprocess.run(['launchctl', 'bootout', target + '/' + LABEL], capture_output=True)
    subprocess.run(['launchctl', 'bootstrap', target, str(plist)], check=True)
    manifest = {'label': LABEL, 'runtime': str(runtime), 'config': str(config_path),
                'plist': str(plist), 'launcher': str(launcher), 'log': str(log),
                'interval_seconds': 300, 'backed_up': saved, 'installed_at': stamp}
    (backups / 'installation.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(manifest, ensure_ascii=False))


if __name__ == '__main__':
    main()
