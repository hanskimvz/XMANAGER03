"""
기존 부품명 마이그레이션 스크립트 (v0.21.0)

부품명이 "부품"이거나 비어있는 경우 description에서 추출하여 업데이트합니다.

사용법:
    cd backend
    python -m scripts.migrate_part_names
"""

import sys
import os

# 프로젝트 루트를 path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.models.parts import Part
from app.utils.part_name_helper import get_part_name, is_valid_part_name


def migrate_part_names(dry_run: bool = True):
    """
    부품명 마이그레이션 실행

    Args:
        dry_run: True이면 실제 업데이트 없이 대상만 출력
    """
    db = SessionLocal()
    try:
        # 부품명이 없거나 "부품"인 항목 조회
        parts = db.query(Part).filter(
            (Part.part_name == None) |
            (Part.part_name == '') |
            (Part.part_name == '부품')
        ).all()

        print(f"\n총 {len(parts)}개의 부품이 마이그레이션 대상입니다.\n")

        updated_count = 0
        skipped_count = 0

        for part in parts:
            old_name = part.part_name or '(없음)'
            new_name = get_part_name(
                part.part_name,
                part.description,
                part.part_number  # fallback
            )

            # 변경이 필요한 경우만 처리
            if new_name != part.part_name:
                print(f"  [{part.id}] {part.part_number}")
                print(f"      현재: '{old_name}'")
                print(f"      변경: '{new_name}'")
                print(f"      설명: {part.description[:50] if part.description else '(없음)'}...")
                print()

                if not dry_run:
                    part.part_name = new_name
                    updated_count += 1
            else:
                skipped_count += 1

        if not dry_run:
            db.commit()
            print(f"\n완료: {updated_count}개 업데이트, {skipped_count}개 건너뜀")
        else:
            print(f"\n[DRY RUN] 실제 업데이트하려면 --execute 옵션을 사용하세요.")
            print(f"  대상: {len(parts) - skipped_count}개")
            print(f"  건너뜀: {skipped_count}개")

    finally:
        db.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='부품명 마이그레이션')
    parser.add_argument(
        '--execute',
        action='store_true',
        help='실제 업데이트 실행 (기본: dry-run 모드)'
    )

    args = parser.parse_args()

    print("=" * 50)
    print("부품명 마이그레이션 스크립트 (v0.21.0)")
    print("=" * 50)

    if args.execute:
        print("\n[!] 실제 업데이트 모드로 실행합니다.\n")
        confirm = input("계속하시겠습니까? (y/N): ")
        if confirm.lower() == 'y':
            migrate_part_names(dry_run=False)
        else:
            print("취소되었습니다.")
    else:
        print("\n[DRY RUN 모드] 변경 사항만 미리 확인합니다.\n")
        migrate_part_names(dry_run=True)
