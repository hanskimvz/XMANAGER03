-- 기본 코드 마스터 초기 데이터
-- 최소한의 샘플 데이터만 입력 (웹 UI로 추가 가능)
-- 인코딩: UTF-8

-- PostgreSQL 클라이언트 인코딩 설정
SET client_encoding = 'UTF8';

-- 대분류 (개발구분)
INSERT INTO major_category (code, name_ko, name_en, description, sort_order, is_active) VALUES
('D', '개발품', 'Developed Part', '자체 설계/개발 부품', 1, true),
('S', '규격품', 'Standard Part', '표준 규격 부품', 2, true),
('M', '상용품', 'Market Part', '시중 구매 부품', 3, true),
('R', '원소재', 'Raw Material', '원자재', 4, true),
('C', '주문품', 'Custom Part', '고객 맞춤 부품', 5, true),
('P', '공정', 'Process', '제조 공정', 6, true);

-- 중분류 (부품유형) - 주요 항목만
INSERT INTO middle_category (code, name_ko, name_en, description, sort_order, is_active) VALUES
('P', '가공품', 'Processed Part', '기계 가공 부품', 1, true),
('I', '사출품', 'Injection Part', '사출 성형품', 2, true),
('A', '조립품', 'Assembly', '조립품', 3, true),
('E', '고무품', 'Elastomer Part', '고무 재질 부품', 4, true),
('F', '체결품', 'Fastener', '볼트, 너트 등 체결품', 5, true);

-- 소분류 (제품라인) - 주요 항목만
INSERT INTO minor_category (code, name_ko, name_en, description, sort_order, is_active) VALUES
('TF1', 'TFOCA', 'TFOCA Connector', 'TFOCA 커넥터', 1, true),
('HB1', 'HXB11', 'HXB11 Expanded Beam', 'Expanded Beam 11핀', 2, true),
('HB3', 'HXB13', 'HXB13 Expanded Beam', 'Expanded Beam 13핀', 3, true),
('COM', '상용품', 'Commercial', '상용 구매품', 10, true);

-- 재질 코드 - 주요 항목만
INSERT INTO material (code, name_ko, name_en, description, sort_order, is_active) VALUES
('A6', 'AL6061', 'Aluminum 6061', '알루미늄 6061 합금', 1, true),
('S4', 'STS304', 'Stainless Steel 304', '스테인리스 304', 2, true),
('NB', 'NBR', 'Nitrile Rubber', '니트릴 고무', 3, true),
('AB', 'ABS', 'ABS Plastic', 'ABS 플라스틱', 4, true),
('BR', 'Brass', 'Brass', '황동', 5, true),
('XX', '미지정', 'Unspecified', '복합재질/미정의', 99, true);

-- 후처리 코드 - 주요 항목만
INSERT INTO treatment (code, name_ko, name_en, description, sort_order, is_active) VALUES
('NN', '없음', 'None', '후처리 없음', 1, true),
('WA', '백색 아노다이징', 'White Anodizing', '백색 아노다이징', 2, true),
('CD', '카드뮴', 'Cadmium Plating', '국방색 카드뮴 도금', 3, true),
('NK', '니켈', 'Nickel Plating', '니켈 도금', 4, true),
('HB', '하드 블랙', 'Hard Black Anodizing', '하드 아노다이징 (블랙)', 5, true);

-- 레벨 코드 (BOM 단계)
INSERT INTO level (code, name_ko, name_en, bom_level, default_unit, description, sort_order, is_active) VALUES
('F', '완제품', 'Finished Good', 0, 'FP', 'BOM Level 0', 1, true),
('P', '패키지', 'Package', 1, 'PKG', 'BOM Level 1', 2, true),
('K', '키트', 'Kit', 2, 'KIT', 'BOM Level 2', 3, true),
('S', '서브어셈블리', 'Sub-Assembly', 3, 'SET', 'BOM Level 3', 4, true),
('R', '단품', 'Raw/Component', 4, 'EA', 'BOM Level 4', 5, true),
('M', '조립공정', 'Manufacturing', NULL, 'EA', '조립 공정', 6, true);

-- 조달 구분
INSERT INTO procurement_type (code, name_ko, name_en, description, sort_order, is_active) VALUES
('MFG', '가공품', 'Manufactured', '자체/외주 기계가공', 1, true),
('PUR', '구매품', 'Purchased', '외부 구매 완제품', 2, true),
('INJ', '사출품', 'Injection', '사출 성형품', 3, true),
('SEM', '반제품', 'Semi-finished', '중간 조립품', 4, true),
('FIN', '완제품', 'Finished', '최종 제품', 5, true);

-- 단위 코드
INSERT INTO unit (code, name_ko, name_en, description, sort_order, is_active) VALUES
('EA', '개', 'Each', '개별 단품', 1, true),
('SET', '세트', 'Set', '세트 (서브어셈블리)', 2, true),
('KIT', '키트', 'Kit', '키트', 3, true),
('PKG', '패키지', 'Package', '패키지', 4, true),
('FP', '완제품', 'Finished Product', '완제품', 5, true),
('M', '미터', 'Meter', '미터 (케이블류)', 6, true),
('G', '그램', 'Gram', '그램 (화학품)', 7, true),
('ML', '밀리리터', 'Milliliter', '밀리리터', 8, true);

-- 확인 쿼리
SELECT '대분류: ' || COUNT(*) || '건' as result FROM major_category
UNION ALL
SELECT '중분류: ' || COUNT(*) || '건' FROM middle_category
UNION ALL
SELECT '소분류: ' || COUNT(*) || '건' FROM minor_category
UNION ALL
SELECT '재질: ' || COUNT(*) || '건' FROM material
UNION ALL
SELECT '후처리: ' || COUNT(*) || '건' FROM treatment
UNION ALL
SELECT '레벨: ' || COUNT(*) || '건' FROM level
UNION ALL
SELECT '조달: ' || COUNT(*) || '건' FROM procurement_type
UNION ALL
SELECT '단위: ' || COUNT(*) || '건' FROM unit;
