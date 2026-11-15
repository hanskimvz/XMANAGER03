"""dev 서버(192.168.0.221)에서 운용 서버(192.168.0.223)로 XMANAGER(web, api)를 배포하는 스크립트.

인증: SSH_PASSWORD 또는 SSH_PRIVATE_KEY_PATH 환경변수를 사용한다.
둘 다 없으면 실행 시 비밀번호를 물어본다. (비밀번호를 소스에 적지 말 것)
"""

import getpass
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile

import paramiko

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOCAL_DIR = SCRIPT_DIR

CONFIG = {
    'host': os.getenv('SSH_HOST', '192.168.0.223'),
    'username': os.getenv('SSH_USERNAME', 'hanskim'),
    'password': os.getenv('SSH_PASSWORD'),
    'private_key': os.getenv('SSH_PRIVATE_KEY_PATH'),
}

DEST_DIR = os.getenv('REMOTE_DEST_DIR', '/ext/xmanager/').rstrip('/') + '/'
SERVICE_NAME = os.getenv('REMOTE_SERVICE_NAME', 'xmanager.service')

WEB_ARCHIVE = 'web.tar.gz'
API_ARCHIVE = 'api.tar.gz'
NGINX_CONF = 'nginx.xmanager.conf'
SERVICE_FILE = 'xmanager.service'

# tar에 포함하지 않을 항목 (디렉터리/파일 이름 기준)
EXCLUDE_NAMES = {'__pycache__', '.pytest_cache', '.git', '.vscode', 'node_modules', 'venv', '.venv', 'log', 'logs', '.env'}
EXCLUDE_SUFFIXES = ('.pyc', '.pyo', '.pyd', '.log', '.tar.gz')

# 배포 단계 기본 선택값. 실행 시 화살표/스페이스로 고르는 메뉴가 뜨고, 여기 값은 초기 체크 상태로 쓰인다.
#   python3 release_codes.py            → 선택 메뉴
#   python3 release_codes.py -y         → 메뉴 없이 아래 기본값으로 실행
#   python3 release_codes.py --steps web_build,web,restart   → 지정한 단계만 실행
DEPLOY_STEPS = {
    'cleanup': False,
    'web_build': True,
    'web': True,
    'nginx': True,
    'service': True,
    'api': True,
    'pycache_cleanup': True,
    'restart': True,   # sudo -n systemctl restart (sudoers 설정 없으면 경고만 출력)
}

STEP_LABELS = {
    'cleanup': '원격 web/, api/ 디렉터리 초기화 (주의: 전체 삭제)',
    'web_build': '프론트엔드 npm run build',
    'web': '웹(dist) 배포',
    'nginx': f'{NGINX_CONF} 업로드',
    'service': f'{SERVICE_FILE} 업로드',
    'api': 'API(backend) 배포',
    'pycache_cleanup': '원격 api/ 아래 __pycache__ 정리',
    'restart': f'{SERVICE_NAME} 재시작',
}


# ----------------------------------------------------------------------------
# 배포 단계 선택 UI
# ----------------------------------------------------------------------------

def _select_steps_curses(defaults):
    """curses 체크박스 메뉴. ↑↓/jk 이동, Space 토글, a 전체 토글, Enter 확정, q/Esc 취소(None)."""
    import curses

    names = list(defaults)
    checked = dict(defaults)

    def draw(stdscr, cursor):
        stdscr.erase()
        stdscr.addstr(0, 0, f"배포 단계 선택  →  {CONFIG['username']}@{CONFIG['host']}:{DEST_DIR}", curses.A_BOLD)
        stdscr.addstr(1, 0, '↑↓ 이동   Space 선택/해제   a 전체 토글   Enter 실행   q 취소')
        for i, name in enumerate(names):
            mark = '[x]' if checked[name] else '[ ]'
            line = f' {mark} {name:<16} {STEP_LABELS.get(name, "")}'
            attr = curses.A_REVERSE if i == cursor else curses.A_NORMAL
            stdscr.addstr(3 + i, 0, line[: curses.COLS - 1], attr)
        selected = [n for n in names if checked[n]]
        stdscr.addstr(4 + len(names), 0, f'선택됨: {", ".join(selected) if selected else "(없음)"}')
        stdscr.refresh()

    def loop(stdscr):
        curses.curs_set(0)
        stdscr.keypad(True)
        cursor = 0
        while True:
            draw(stdscr, cursor)
            key = stdscr.getch()
            if key in (curses.KEY_UP, ord('k')):
                cursor = (cursor - 1) % len(names)
            elif key in (curses.KEY_DOWN, ord('j')):
                cursor = (cursor + 1) % len(names)
            elif key == ord(' '):
                checked[names[cursor]] = not checked[names[cursor]]
            elif key == ord('a'):
                all_on = all(checked.values())
                for n in names:
                    checked[n] = not all_on
            elif key in (curses.KEY_ENTER, 10, 13):
                return [n for n in names if checked[n]]
            elif key in (ord('q'), 27):
                return None

    return curses.wrapper(loop)


def _select_steps_plain(defaults):
    """curses를 쓸 수 없을 때의 번호 입력 방식. Enter만 치면 기본값."""
    names = list(defaults)
    print('\n배포 단계 선택 (번호를 공백으로 구분해 입력, Enter = 기본값, q = 취소)')
    for i, name in enumerate(names, 1):
        mark = 'x' if defaults[name] else ' '
        print(f'  {i}. [{mark}] {name:<16} {STEP_LABELS.get(name, "")}')
    while True:
        answer = input('> ').strip()
        if answer.lower() == 'q':
            return None
        if not answer:
            return [n for n in names if defaults[n]]
        try:
            idx = sorted({int(tok) for tok in answer.split()})
            if all(1 <= i <= len(names) for i in idx):
                return [names[i - 1] for i in idx]
        except ValueError:
            pass
        print(f'1~{len(names)} 사이의 번호를 입력하세요.')


def choose_steps(argv):
    """명령행 옵션과 터미널 상태에 따라 실행할 단계 목록을 돌려준다. 취소하면 None."""
    if '-y' in argv or '--yes' in argv:
        return [n for n, on in DEPLOY_STEPS.items() if on]

    for i, arg in enumerate(argv):
        if arg.startswith('--steps='):
            wanted = arg.split('=', 1)[1]
        elif arg == '--steps' and i + 1 < len(argv):
            wanted = argv[i + 1]
        else:
            continue
        names = [s.strip() for s in wanted.split(',') if s.strip()]
        unknown = [n for n in names if n not in DEPLOY_STEPS]
        if unknown:
            print(f'알 수 없는 단계: {", ".join(unknown)}  (가능: {", ".join(DEPLOY_STEPS)})')
            return None
        return [n for n in DEPLOY_STEPS if n in names]  # 정해진 순서 유지

    if not sys.stdin.isatty():
        return [n for n, on in DEPLOY_STEPS.items() if on]

    try:
        import curses  # noqa: F401
        return _select_steps_curses(DEPLOY_STEPS)
    except Exception:  # curses 미설치, TERM 미설정 등
        return _select_steps_plain(DEPLOY_STEPS)


def _section(title):
    print(f"\n{'=' * 40}")
    print(title)
    print('=' * 40)


def _progress_callback(transferred, total):
    if total <= 0:
        return
    percentage = (transferred / total) * 100
    bar_length = 40
    filled_length = int(bar_length * transferred // total)
    bar = '█' * filled_length + '-' * (bar_length - filled_length)
    print(f'\r[{bar}] {percentage:.1f}% ({transferred}/{total} bytes)', end='', flush=True)


def connect_ssh():
    ssh = paramiko.SSHClient()
    ssh.load_system_host_keys()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"서버 연결 중: {CONFIG['username']}@{CONFIG['host']}")

    kwargs = {'hostname': CONFIG['host'], 'username': CONFIG['username']}
    if CONFIG['private_key']:
        kwargs['key_filename'] = os.path.expanduser(CONFIG['private_key'])
        method = 'SSH 키'
    else:
        password = CONFIG['password'] or getpass.getpass(f"{CONFIG['username']}@{CONFIG['host']} 비밀번호: ")
        kwargs['password'] = password
        kwargs['look_for_keys'] = False
        kwargs['allow_agent'] = False
        method = '비밀번호'

    ssh.connect(**kwargs)
    print(f'SSH {method} 인증 성공')
    return ssh


def ssh_exec(ssh, command, *, print_output=True):
    """SSH 명령 실행 후 exit status와 출력을 반환."""
    print(f'실행: {command}')
    _, stdout, stderr = ssh.exec_command(command)
    exit_status = stdout.channel.recv_exit_status()
    output = stdout.read().decode()
    error = stderr.read().decode()

    if print_output:
        if output:
            print('출력:', output)
        if error:
            print('에러:', error)

    return {
        'exit_status': exit_status,
        'output': output,
        'error': error,
        'success': exit_status == 0,
    }


def sftp_upload(ssh, local_path, remote_path):
    print(f'파일 전송: {local_path} -> {remote_path}')
    if not os.path.isfile(local_path):
        print(f'파일 전송 실패: 로컬 파일이 없습니다: {local_path}')
        return False

    remote_dir = os.path.dirname(remote_path)
    if remote_dir and not ssh_exec(ssh, f'mkdir -p "{remote_dir}"', print_output=False)['success']:
        print(f'파일 전송 실패: 원격 디렉터리를 만들 수 없습니다: {remote_dir}')
        return False

    try:
        with ssh.open_sftp() as sftp:
            sftp.put(local_path, remote_path, callback=_progress_callback)
        print()
        print('✓ 파일 전송 완료')
        return True
    except (OSError, paramiko.SSHException) as exc:
        print()
        print(f'파일 전송 실패: {exc}')
        return False


def _tar_filter(tarinfo):
    """캐시, 로그, 비밀 파일, 이전 아카이브를 tar에서 제외."""
    parts = tarinfo.name.split('/')
    if any(part in EXCLUDE_NAMES for part in parts):
        return None
    if tarinfo.name.endswith(EXCLUDE_SUFFIXES):
        return None
    return tarinfo


def create_tar(source_dir, archive_path, arcname):
    """source_dir를 archive_path로 압축. archive_path는 source_dir 바깥(임시 디렉터리)이어야 한다."""
    if not os.path.isdir(source_dir):
        print(f'소스 디렉터리를 찾을 수 없습니다: {source_dir}')
        return False

    print(f'압축 중: {source_dir}')
    try:
        with tarfile.open(archive_path, 'w:gz') as tar:
            tar.add(source_dir, arcname=arcname, filter=_tar_filter)
        size = os.path.getsize(archive_path)
        print(f'✓ 압축 완료: {archive_path} ({size:,} bytes)')
        return True
    except OSError as exc:
        print(f'압축 실패: {exc}')
        return False


def extract_remote_tar(ssh, remote_archive, *, remove_before=()):
    """DEST_DIR에서 아카이브를 풀고 삭제. remove_before에 적힌 상대 경로는 풀기 전에 지운다(stale 파일 방지)."""
    cmds = [f'cd "{DEST_DIR}"']
    for rel in remove_before:
        cmds.append(f'rm -rf "{DEST_DIR}{rel}"')
    cmds.append(f'tar xzf "{remote_archive}"')
    cmds.append(f'rm -f "{remote_archive}"')
    result = ssh_exec(ssh, ' && '.join(cmds), print_output=False)
    if not result['success']:
        print(f"압축 해제 실패 (exit code: {result['exit_status']})")
        if result['error']:
            print(f"에러: {result['error']}")
        return False
    print('✓ 압축 해제 완료')
    return True


def swap_remote_dir(ssh, staging_rel, target_rel):
    """staging 디렉터리를 target 자리로 교체 (이전 버전은 삭제)."""
    staging = f'{DEST_DIR}{staging_rel}'
    target = f'{DEST_DIR}{target_rel}'
    old = f'{target}.old'
    cmd = (
        f'rm -rf "{old}" && '
        f'(test -e "{target}" && mv "{target}" "{old}" || true) && '
        f'mv "{staging}" "{target}" && '
        f'rm -rf "{old}"'
    )
    result = ssh_exec(ssh, cmd, print_output=False)
    if not result['success']:
        print(f"디렉터리 교체 실패: {result['error']}")
        return False
    print(f'✓ {target_rel} 교체 완료')
    return True


def find_and_remove_pycache(ssh, base_path):
    """지정 경로 아래 __pycache__ 폴더를 찾아 삭제."""
    _section('__pycache__ 정리')
    print(f'__pycache__ 검색 및 삭제: {base_path}')
    result = ssh_exec(ssh, f'find "{base_path}" -type d -name "__pycache__"', print_output=False)
    if not result['success']:
        print(f"__pycache__ 검색 실패: {result['error']}")
        return False

    pycache_dirs = [path.strip() for path in result['output'].splitlines() if path.strip()]
    if not pycache_dirs:
        print('삭제할 __pycache__ 폴더가 없습니다.')
        return True

    print(f'발견된 __pycache__ 폴더 {len(pycache_dirs)}개')
    ok = True
    for dir_path in pycache_dirs:
        rm_result = ssh_exec(ssh, f'rm -rf "{dir_path}"', print_output=False)
        if rm_result['success']:
            print(f'  삭제 완료: {dir_path}')
        else:
            ok = False
            print(f'  삭제 실패: {dir_path} - {rm_result["error"]}')
    return ok


def cleanup_remote_dir(ssh):
    _section('원격 디렉터리 초기화')
    # rm -rf 사고 방지: 절대 경로이고 최소 2단계 깊이여야 한다 (예: /ext/xmanager/)
    depth = len([p for p in DEST_DIR.split('/') if p])
    if not DEST_DIR.startswith('/') or depth < 2:
        print(f'안전하지 않은 DEST_DIR 이므로 초기화를 중단합니다: {DEST_DIR!r}')
        return False

    result = ssh_exec(ssh, f'rm -rf "{DEST_DIR}web" "{DEST_DIR}api"', print_output=False)
    if not result['success']:
        print(f"기존 파일 제거 실패: {result['error']}")
        return False
    print('✓ 기존 web/, api/ 제거 완료')

    for subdir in ('web', 'api'):
        if not ssh_exec(ssh, f'mkdir -p "{DEST_DIR}{subdir}"', print_output=False)['success']:
            print(f'{subdir} 디렉터리 생성 실패')
            return False
        print(f'✓ {subdir} 디렉터리 생성 완료')
    return True


def run_web_build():
    _section('웹 빌드')
    frontend_dir = os.path.join(LOCAL_DIR, 'frontend')

    npm = shutil.which('npm')
    if not npm:
        print('npm을 찾을 수 없습니다. PATH를 확인하세요.')
        return False

    print(f'{npm} run build 실행 중...')
    try:
        result = subprocess.run(
            [npm, 'run', 'build'],
            cwd=frontend_dir,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        print(f'빌드 실행 중 오류: {exc}')
        return False

    if result.stdout:
        print('=== 빌드 출력 (마지막 1000자) ===')
        print(result.stdout[-1000:])

    if result.returncode != 0:
        print(f'빌드 실패 (exit code: {result.returncode})')
        if result.stderr:
            print('=== 에러 메시지 ===')
            print(result.stderr)
        return False

    if not os.path.isfile(os.path.join(frontend_dir, 'dist', 'index.html')):
        print('빌드는 끝났지만 dist/index.html 이 없습니다.')
        return False

    print('✓ 빌드 완료')
    return True


def release_web(ssh):
    """dist/ 를 압축해 올리고 web.new 에 풀었다가 web/ 과 교체한다 (이전 빌드 파일 잔존 방지)."""
    _section('웹 배포')
    dist_dir = os.path.join(LOCAL_DIR, 'frontend', 'dist')
    remote_tar_file = f'{DEST_DIR}{WEB_ARCHIVE}'

    with tempfile.TemporaryDirectory(prefix='xmanager_web_') as tmp:
        local_tar_file = os.path.join(tmp, WEB_ARCHIVE)
        if not create_tar(dist_dir, local_tar_file, arcname='web.new'):
            return False
        if not sftp_upload(ssh, local_tar_file, remote_tar_file):
            return False

    if not extract_remote_tar(ssh, remote_tar_file, remove_before=('web.new',)):
        return False
    if not swap_remote_dir(ssh, 'web.new', 'web'):
        return False

    print('✓ 웹 배포 완료')
    print(f'배포 위치: {DEST_DIR}web/')
    return True


def cleanup_stale_api_root_files(ssh):
    """예전 flat 배포에서 api/ 루트에 남은 .py 파일 제거 (start_server.py 제외)."""
    api_dir = f'{DEST_DIR}api'
    cmd = (
        f'find "{api_dir}" -maxdepth 1 -name "*.py" ! -name "start_server.py" '
        f'-print -delete'
    )
    result = ssh_exec(ssh, cmd, print_output=False)
    if result['output']:
        print('✓ api/ 루트 stale 파일 제거:')
        for path in result['output'].splitlines():
            if path.strip():
                print(f'  - {path.strip()}')
    else:
        print('✓ api/ 루트 stale 파일 없음')


def release_api(ssh):
    """backend/ 를 압축해 api/ 에 덧씌운다. 코드 디렉터리(app/, tools/)는 풀기 전에 지워 stale 모듈을 없앤다.
    api/ 전체를 교체하지 않는 이유: 서버에서 생성되는 logs/ 등 런타임 파일을 보존하기 위해서다."""
    _section('API 배포')
    backend_dir = os.path.join(LOCAL_DIR, 'backend')
    remote_tar_file = f'{DEST_DIR}api/{API_ARCHIVE}'

    with tempfile.TemporaryDirectory(prefix='xmanager_api_') as tmp:
        local_tar_file = os.path.join(tmp, API_ARCHIVE)
        if not create_tar(backend_dir, local_tar_file, arcname='api'):
            return False
        if not sftp_upload(ssh, local_tar_file, remote_tar_file):
            return False

    if not extract_remote_tar(ssh, remote_tar_file, remove_before=('api/app', 'api/tools')):
        return False

    cleanup_stale_api_root_files(ssh)

    print('✓ API 배포 완료')
    print(f'배포 위치: {DEST_DIR}api/')
    return True


def restart_service(ssh):
    """운용 서버의 API 서비스를 재시작. sudo 비밀번호가 필요하면(sudo -n 실패) 경고만 출력한다."""
    _section('서비스 재시작')
    result = ssh_exec(ssh, f'sudo -n systemctl restart {SERVICE_NAME}', print_output=False)
    if not result['success']:
        print(f"⚠ 서비스 재시작 실패: {result['error'].strip() or result['output'].strip()}")
        print(f'  수동으로 실행하세요: sudo systemctl restart {SERVICE_NAME}')
        print(f"  (자동화하려면 sudoers에 '{CONFIG['username']} ALL=(root) NOPASSWD: /bin/systemctl restart {SERVICE_NAME}' 추가)")
        return True  # 배포 자체는 완료된 상태이므로 실패로 취급하지 않음

    status = ssh_exec(ssh, f'systemctl is-active {SERVICE_NAME}', print_output=False)
    print(f"✓ 서비스 재시작 완료 (상태: {status['output'].strip()})")
    return status['success']


def upload_config_file(ssh, filename):
    _section(f'{filename} 업로드')
    local_path = os.path.join(LOCAL_DIR, filename)
    remote_path = f'{DEST_DIR}{filename}'
    return sftp_upload(ssh, local_path, remote_path)


def main():
    # (단계 이름, 실행 함수) 순서대로. 하나라도 실패하면 이후 단계를 건너뛰고 exit code 1.
    steps = [
        ('cleanup', cleanup_remote_dir),
        ('web_build', lambda ssh: run_web_build()),
        ('web', release_web),
        ('nginx', lambda ssh: upload_config_file(ssh, NGINX_CONF)),
        ('service', lambda ssh: upload_config_file(ssh, SERVICE_FILE)),
        ('api', release_api),
        ('pycache_cleanup', lambda ssh: find_and_remove_pycache(ssh, f'{DEST_DIR}api')),
        ('restart', restart_service),
    ]

    selected = choose_steps(sys.argv[1:])
    if selected is None:
        print('취소됨')
        return 1
    if not selected:
        print('선택된 단계가 없습니다.')
        return 1
    print(f'실행할 단계: {", ".join(selected)}')

    ssh = connect_ssh()
    failed = None
    try:
        for name, func in steps:
            if name not in selected:
                continue
            if not func(ssh):
                failed = name
                break
    finally:
        ssh.close()
        print('\n서버 연결 종료')

    if failed:
        print(f'\n✗ 배포 실패: {failed} 단계에서 중단됨')
        return 1
    print('\n✓ 배포 완료')
    return 0


if __name__ == '__main__':
    sys.exit(main())
