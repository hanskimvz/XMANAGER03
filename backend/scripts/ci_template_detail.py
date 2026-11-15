import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from openpyxl import load_workbook

wb = load_workbook('c:/X-MANAGER_R0.1/docs/samples/sales-export/CI-TEMPLATE.xlsx')
ws = wb.active

# 템플릿의 Package Details ~ 서명 영역 (32~56)
# 테두리만 확인 (MergedCell 에러 방지)
print('=== 테두리 32~56행 ===')
for r in range(32, 57):
    for c in range(1, 16):
        try:
            cell = ws.cell(row=r, column=c)
            b = cell.border
            parts = []
            if b.top and b.top.style: parts.append(f'top={b.top.style}')
            if b.bottom and b.bottom.style: parts.append(f'bot={b.bottom.style}')
            if b.left and b.left.style: parts.append(f'left={b.left.style}')
            if b.right and b.right.style: parts.append(f'right={b.right.style}')
            if parts:
                from openpyxl.utils import get_column_letter
                cl = get_column_letter(c)
                print(f'  {cl}{r}: {parts}')
        except: pass

# 외곽선 확인 (A열, O열)
print()
print('=== 외곽선 (A열, O열) 24~36행 ===')
for r in range(24, 37):
    for c in [1, 15]:  # A, O
        try:
            cell = ws.cell(row=r, column=c)
            b = cell.border
            parts = []
            if b.top and b.top.style: parts.append(f'top={b.top.style}')
            if b.bottom and b.bottom.style: parts.append(f'bot={b.bottom.style}')
            if b.left and b.left.style: parts.append(f'left={b.left.style}')
            if b.right and b.right.style: parts.append(f'right={b.right.style}')
            if parts:
                from openpyxl.utils import get_column_letter
                cl = get_column_letter(c)
                print(f'  {cl}{r}: {parts}')
        except: pass

# 서명 영역 (46, 54)
print()
print('=== 서명 영역 스타일 ===')
for r in [46, 54]:
    for c in range(1, 16):
        try:
            cell = ws.cell(row=r, column=c)
            if cell.value:
                from openpyxl.utils import get_column_letter
                cl = get_column_letter(c)
                print(f'  {cl}{r}: val="{cell.value}" font={cell.font.name}/{cell.font.size}/{cell.font.bold} align={cell.alignment.horizontal}')
                b = cell.border
                parts = []
                if b.top and b.top.style: parts.append(f'top={b.top.style}')
                if b.bottom and b.bottom.style: parts.append(f'bot={b.bottom.style}')
                if parts: print(f'    border: {parts}')
        except: pass
