# -*- coding: utf-8 -*-
with open('data/debug_page.html', 'r', encoding='utf-8') as f:
    c = f.read()

idx = c.find("stExpanderDetails")
if idx != -1:
    print(c[idx:idx+3000])
