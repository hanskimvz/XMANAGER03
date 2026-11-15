"""
부품명 마이그레이션 독립 실행 스크립트 (v0.21.0)

의존성: psycopg2 (또는 psycopg2-binary)

사용법:
    cd backend
    python scripts/migrate_part_names_standalone.py
"""

import re

# 데이터베이스 연결 정보 (필요시 수정)
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "xmanager_dev",
    "user": "xmanager",
    "password": "xmanager1014"
}


def is_valid_part_name(part_name):
    """부품명이 유효한지 확인"""
    if not part_name:
        return False
    trimmed = part_name.strip()
    return trimmed != '' and trimmed != '부품'


def extract_part_name_from_description(description):
    """설명에서 부품명 추출 (/ 기준 처음 3개)"""
    if not description:
        return None

    parts = re.split(r'\s*/\s*', description)
    parts = [p.strip() for p in parts if p.strip()]

    if not parts:
        return None

    result = ' '.join(parts[:3])
    return result if result else None


def migrate():
    try:
        import psycopg2
    except ImportError:
        print("오류: psycopg2가 설치되어 있지 않습니다.")
        print("설치: pip install psycopg2-binary")
        return

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    try:
        # 대상 조회
        cur.execute("""
            SELECT id, part_number, part_name, description
            FROM parts
            WHERE part_name IS NULL OR part_name = '' OR part_name = '부품'
        """)

        rows = cur.fetchall()
        print(f"\n총 {len(rows)}개의 부품이 마이그레이션 대상입니다.\n")

        if not rows:
            print("마이그레이션할 데이터가 없습니다.")
            return

        # 미리보기
        print("=" * 60)
        print("변경 미리보기:")
        print("=" * 60)

        updates = []
        for row in rows:
            part_id, part_number, part_name, description = row
            old_name = part_name or '(없음)'
            new_name = extract_part_name_from_description(description) or part_number

            if new_name and new_name != part_name:
                updates.append((new_name, part_id))
                print(f"\n[{part_id}] {part_number}")
                print(f"    현재: '{old_name}'")
                print(f"    변경: '{new_name}'")
                desc_preview = description[:50] + '...' if description and len(description) > 50 else (description or '(없음)')
                print(f"    설명: {desc_preview}")

        if not updates:
            print("\n변경할 항목이 없습니다.")
            return

        print(f"\n{'=' * 60}")
        print(f"총 {len(updates)}개 항목을 업데이트합니다.")
        print("=" * 60)

        confirm = input("\n실행하시겠습니까? (y/N): ")
        if confirm.lower() != 'y':
            print("취소되었습니다.")
            return

        # 업데이트 실행
        cur.executemany(
            "UPDATE parts SET part_name = %s WHERE id = %s",
            updates
        )
        conn.commit()

        print(f"\n완료: {len(updates)}개 업데이트됨")

    except Exception as e:
        conn.rollback()
        print(f"\n오류 발생: {e}")
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    print("=" * 60)
    print("부품명 마이그레이션 스크립트 (v0.21.0)")
    print("=" * 60)
    migrate()
