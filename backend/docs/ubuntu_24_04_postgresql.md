# Ubuntu 24.04 PostgreSQL 데이터 저장소(PGDATA) 경로 변경 매뉴얼

운영 환경에서 서비스 안정성과 데이터 무결성을 유지하면서 PostgreSQL 18의 데이터 디렉터리를 신규 저장소(`/ext/postgresql/`)로 이관하기 위한 작업 문서입니다.

## 📋 작업 개요

데이터 무결성 유지를 위해 서비스를 중지한 상태에서 `rsync`를 활용해 데이터를 안전하게 복사하며, Ubuntu 24.04의 **AppArmor** 보안 정책에 맞춰 경로 예외(`alias`) 설정을 함께 진행합니다.

| 항목 | 상세 내용 | 
| :--- | :--- | 
| **운영체제** | Ubuntu 24.04 LTS | 
| **대상 소프트웨어** | PostgreSQL 18 | 
| **기존 데이터 경로** | `/var/lib/postgresql/18/main` | 
| **신규 데이터 경로** | `/ext/postgresql/` | 
| **핵심 작업 요소** | 서비스 중단 후 `rsync` 이관, `postgresql.conf` 수정, AppArmor 별칭 추가 | 

## 1단계: 현재 데이터 경로 및 버전 확인

작업을 시작하기 전, 현재 실행 중인 PostgreSQL의 실제 데이터 디렉터리 경로를 확인합니다.

```bash
sudo -u postgres psql -c "SHOW data_directory;"
```

* **검증 방법:** 출력 결과로 `/var/lib/postgresql/18/main`이 표시되는지 확인합니다.

## 2단계: PostgreSQL 서비스 중지 및 신규 디렉터리 준비

데이터 손상을 방지하기 위해 DB 서비스를 중지하고, 신규 저장소 경로(`/ext/postgresql/`)의 소유권과 접근 권한을 설정합니다.

### 1. PostgreSQL 서비스 중지

```bash
sudo systemctl stop postgresql
```

* **검증 방법:** `sudo systemctl is-active postgresql` 실행 시 `inactive`가 출력되어야 합니다.

### 2. 신규 저장소 디렉터리 생성 및 권한 부여

```bash
sudo mkdir -p /ext/postgresql
sudo chown -R postgres:postgres /ext/postgresql
sudo chmod 700 /ext/postgresql
```

* **검증 방법:** `ls -ld /ext/postgresql` 실행 시 권한이 `drwx------`이며, 소유자 및 그룹이 `postgres:postgres`로 설정되어 있는지 확인합니다.

## 3단계: 기존 데이터 복사 (`rsync`)

권한, 타임스탬프, 심볼릭 링크를 그대로 유지하면서 기존 데이터를 신규 경로로 복사합니다.

```bash
sudo rsync -av /var/lib/postgresql/18/main/ /ext/postgresql/
```

> **주의:** 경로 끝의 슬래시(`/`) 표기를 정확히 입력해야 하위 디렉터리 구조가 동일하게 복사됩니다.

* **검증 방법:** `sudo ls /ext/postgresql` 실행 시 `PG_VERSION`, `base`, `global`, `pg_wal` 등의 폴더와 파일이 정상적으로 복제되었는지 확인합니다.

## 4단계: PostgreSQL 설정 파일(`postgresql.conf`) 수정

PostgreSQL 서비스가 새로운 저장소 경로를 참조하도록 설정 파일을 수정합니다.

### 1. 설정 파일 열기

```bash
sudo nano /etc/postgresql/18/main/postgresql.conf
```

### 2. `data_directory` 항목 수정

파일 내 `data_directory` 항목을 찾아 신규 경로로 변경한 후 저장합니다.

```text
data_directory = '/ext/postgresql'
```

## 5단계: AppArmor 접근 권한 허용 (Ubuntu 24.04 필수)

Ubuntu 24.04에서는 AppArmor 보안 정책이 기본 경로(`/var/lib/postgresql/`) 외의 디렉터리 접근을 차단하므로, 경로 별칭(`alias`)을 등록해야 서비스가 정상 시작됩니다.

### 1. AppArmor alias 설정 파일 열기

```bash
sudo nano /etc/apparmor.d/tunables/alias
```

### 2. 파일 최하단에 alias 구문 추가

파일 가장 아랫부분에 아래 내용을 추가한 뒤 저장합니다.

```text
alias /var/lib/postgresql/ -> /ext/postgresql/,
```

> **주의:** 경로 끝의 슬래시(`/`)와 쉼표(`,`)를 빠뜨리지 않도록 정확히 입력하세요.

### 3. AppArmor 서비스 재시작

```bash
sudo systemctl restart apparmor
```

* **검증 방법:** 오류 메시지 없이 정상적으로 터미널 프롬프트가 반환되는지 확인합니다.

## 6단계: 서비스 시작 및 최종 검증

### 1. PostgreSQL 서비스 시작

```bash
sudo systemctl start postgresql
```

* **검증 방법:** `sudo systemctl is-active postgresql` 실행 시 `active`가 출력되는지 확인합니다.

### 2. 변경된 데이터 경로 및 DB 정상 조회 확인

```bash
sudo -u postgres psql -c "SHOW data_directory;"
```

* **검증 방법:**
  * 출력 결과에 `/ext/postgresql`이 표시되는지 확인합니다.
  * `sudo -u postgres psql`로 접속 후 `\l` 명령어를 입력하여 기존 데이터베이스 목록이 정상적으로 조회되는지 확인합니다.

### 3. 기존 데이터 백업 및 정리 (선택 사항)

며칠간 서비스 운영 상태를 충분히 검증한 뒤, 기존 폴더의 이름을 변경하여 백업하고 추후 삭제하여 디스크 용량을 확보합니다.

```bash
sudo mv /var/lib/postgresql/18/main /var/lib/postgresql/18/main.bak
```

## ⚠️ 운영 시 주의사항

* **외장 드라이브 또는 별도 파티션 마운트 설정:** `/ext/postgresql/` 경로가 별도의 디스크나 파티션에 위치한 경우, 시스템 재부팅 시 자동 마운트되도록 `/etc/fstab`에 반드시 마운트 정보를 등록해야 합니다.
* **상위 디렉터리 실행 권한 확인:** `postgres` 계정이 최종 경로까지 진입할 수 있도록 상위 디렉터리(`/ext`)에 실행(`x`) 권한이 부여되어 있는지 확인하세요. (`sudo chmod +x /ext`)