# -*- coding: utf-8 -*-
with open('data/debug_page.html', 'r', encoding='utf-8') as f:
    c = f.read()

idx = c.find("主动风险预警哨")
if idx != -1:
    print("Found around idx:", idx)
    print("=== PREV 500 ===")
    print(c[max(0, idx-500):idx])
    print("=== NEXT 500 ===")
    print(c[idx:idx+500])
else:
    print("Not found")
