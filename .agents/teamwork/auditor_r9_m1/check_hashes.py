import hashlib
import os

files_to_check = [
    ("AGY2_FundAdvisory/judge_engine.py", "76f930371176de7ee6a413174b030101e3210ac6e037f5d10fe229af31cc07be"),
    ("judge_engine.py", "76f930371176de7ee6a413174b030101e3210ac6e037f5d10fe229af31cc07be"),
    ("AGY2_FundAdvisory/holdout_vault.py", "88122eaf647040a410e2fd95da81077db10149a498a47340ff40b670bd031d2a"),
    ("holdout_vault.py", "88122eaf647040a410e2fd95da81077db10149a498a47340ff40b670bd031d2a"),
    ("AGY2_FundAdvisory/AGENT_SPEC.md", "a346586f9bd2dc0ee83e665bd18e7a6471464c9f7b658e392b989b800cd63957"),
    ("AGENT_SPEC.md", "a346586f9bd2dc0ee83e665bd18e7a6471464c9f7b658e392b989b800cd63957"),
    ("tests/test_infra.py", "48bee0da300d7c0a0848ec1376e4b9b2e55224d2736081713b4340f0362cd100")
]

for path, expected in files_to_check:
    if os.path.exists(path):
        with open(path, "rb") as f:
            h = hashlib.sha256(f.read()).hexdigest().lower()
        match = (h == expected.lower())
        print(f"{path}: actual={h} match={match}")
    else:
        print(f"{path}: NOT_FOUND")
