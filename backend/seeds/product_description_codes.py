"""
제품 설명 코드 시드 데이터
docs/samples/sales-export/ 엑셀의 키워드_디스크립션 시트 기반
"""

SEED_DATA = [
    # TYPE: 커넥터 타입
    {"segment_type": "TYPE", "code": "PSD", "description_en": "-Plug with Dust Cap", "sort_order": 1},
    {"segment_type": "TYPE", "code": "RJS", "description_en": "-Receptacle, Jam nut, Standard, Dust cap", "sort_order": 2},
    {"segment_type": "TYPE", "code": "RJN", "description_en": "-Receptacle, Jam Nut, No Boot, Dust cap", "sort_order": 3},
    {"segment_type": "TYPE", "code": "RJL", "description_en": "-Receptacle, Jam Nut, Low Profile, Dust cap", "sort_order": 4},
    {"segment_type": "TYPE", "code": "RQS", "description_en": "-Receptacle, Square Flange, Standard, Dust cap", "sort_order": 5},
    {"segment_type": "TYPE", "code": "RQN", "description_en": "-Receptacle, Square Flange, No Boot, Dust cap", "sort_order": 6},
    {"segment_type": "TYPE", "code": "RQL", "description_en": "-Receptacle, Square Flange, Low Profile, Dust cap", "sort_order": 7},

    # MATERIAL: 재질
    {"segment_type": "MATERIAL", "code": "B", "description_en": "-Aluminium alloy, Black hard anodizing", "sort_order": 1},
    {"segment_type": "MATERIAL", "code": "S", "description_en": "-Stainless Steel", "sort_order": 2},

    # CHANNEL: 채널 수 (O prefix)
    {"segment_type": "CHANNEL", "code": "O2", "description_en": "-2 CH", "sort_order": 1},
    {"segment_type": "CHANNEL", "code": "O4", "description_en": "-4 CH", "sort_order": 2},
    {"segment_type": "CHANNEL", "code": "O6", "description_en": "-6 CH", "sort_order": 3},
    {"segment_type": "CHANNEL", "code": "O8", "description_en": "-8 CH", "sort_order": 4},
    {"segment_type": "CHANNEL", "code": "OA", "description_en": "-10 CH", "sort_order": 5},
    {"segment_type": "CHANNEL", "code": "OC", "description_en": "-12 CH", "sort_order": 6},
    {"segment_type": "CHANNEL", "code": "OE", "description_en": "-14 CH", "sort_order": 7},
    {"segment_type": "CHANNEL", "code": "OG", "description_en": "-16 CH", "sort_order": 8},

    # CHANNEL: 채널 수 (0 prefix - 레거시)
    {"segment_type": "CHANNEL", "code": "02", "description_en": "-2 CH", "sort_order": 11},
    {"segment_type": "CHANNEL", "code": "04", "description_en": "-4 CH", "sort_order": 12},
    {"segment_type": "CHANNEL", "code": "06", "description_en": "-6 CH", "sort_order": 13},
    {"segment_type": "CHANNEL", "code": "08", "description_en": "-8 CH", "sort_order": 14},
    {"segment_type": "CHANNEL", "code": "0A", "description_en": "-10 CH", "sort_order": 15},
    {"segment_type": "CHANNEL", "code": "0C", "description_en": "-12 CH", "sort_order": 16},
    {"segment_type": "CHANNEL", "code": "0E", "description_en": "-14 CH", "sort_order": 17},
    {"segment_type": "CHANNEL", "code": "0G", "description_en": "-16 CH", "sort_order": 18},

    # FIBER: 광섬유 타입
    {"segment_type": "FIBER", "code": "S1", "description_en": ", 9 \u03bcm core Singlemode fiber", "sort_order": 1},
    {"segment_type": "FIBER", "code": "M1", "description_en": ", 62.5 \u03bcm core Multimode fiber", "sort_order": 2},
    {"segment_type": "FIBER", "code": "M2", "description_en": ", 50 \u03bcm core Multimode fiber", "sort_order": 3},
    {"segment_type": "FIBER", "code": "M3", "description_en": ", 50 \u03bcm core Multimode fiber", "sort_order": 4},
    {"segment_type": "FIBER", "code": "M4", "description_en": ", 50 \u03bcm core Multimode fiber", "sort_order": 5},

    # CABLE: 케이블 사양
    {"segment_type": "CABLE", "code": "S09", "description_en": "- \u00d8 0.9 mm Buffered Fiber", "sort_order": 1},
    {"segment_type": "CABLE", "code": "S20", "description_en": "- \u00d8 2.0 mm Jacketed Cable", "sort_order": 2},
    {"segment_type": "CABLE", "code": "D55", "description_en": "-for out diameter 5.5mm Outdoor cable", "sort_order": 3},
    {"segment_type": "CABLE", "code": "D65", "description_en": "-for out diameter 6.5mm Outdoor cable", "sort_order": 4},

    # PRODUCT: 제품군
    {"segment_type": "PRODUCT", "code": "HXB15", "description_en": "", "sort_order": 1},
    {"segment_type": "PRODUCT", "code": "HXB13", "description_en": "", "sort_order": 2},
    {"segment_type": "PRODUCT", "code": "HXB11", "description_en": "", "sort_order": 3},
    {"segment_type": "PRODUCT", "code": "HXB17", "description_en": "", "sort_order": 4},
    {"segment_type": "PRODUCT", "code": "HXB15AS", "description_en": "-ConnA: ", "sort_order": 5},
    {"segment_type": "PRODUCT", "code": "HXB13AS", "description_en": "-ConnA: ", "sort_order": 6},
    {"segment_type": "PRODUCT", "code": "HXB11AS", "description_en": "-ConnA: ", "sort_order": 7},
    {"segment_type": "PRODUCT", "code": "HXB17AS", "description_en": "-ConnA: ", "sort_order": 8},

    # CONNECTOR: 커넥터 조합
    {"segment_type": "CONNECTOR", "code": "SA", "description_en": "-ConnB: same as Conn A", "sort_order": 1},
]


def seed_product_description_codes(db):
    """시드 데이터 삽입 (중복 시 건너뜀)"""
    from app.models.product_description_code import ProductDescriptionCode

    created = 0
    for data in SEED_DATA:
        existing = db.query(ProductDescriptionCode).filter(
            ProductDescriptionCode.segment_type == data["segment_type"],
            ProductDescriptionCode.code == data["code"],
        ).first()
        if not existing:
            db.add(ProductDescriptionCode(**data))
            created += 1
    db.commit()
    return created
