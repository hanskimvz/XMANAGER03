-- 개발 DB 생성 (db_list.json 끝에 붙어 있던 메모를 옮김)
-- 실행: sudo -u postgres psql -f tool/create_dev_db.sql
CREATE DATABASE xmanager_dev
    OWNER = xmanager
    ENCODING = 'UTF8'
    LC_COLLATE = 'ko_KR.UTF-8'
    LC_CTYPE = 'ko_KR.UTF-8'
    TEMPLATE = template0;
