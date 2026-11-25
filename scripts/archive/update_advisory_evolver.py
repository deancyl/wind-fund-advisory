from pathlib import Path

TARGET_FILE = Path("AGY2_FundAdvisory/advisory_engine.py")

def main():
    content = TARGET_FILE.read_text(encoding="utf-8")
    
    target_str = '"nav_dynamic": [round(float(x), 4) for x in nav_dyn[1:]],'
    replacement_str = '''"nav_dynamic": [round(float(x), 4) for x in nav_dyn[1:]],
            "dynamic_nav": [round(float(x), 4) for x in nav_dyn[1:]],'''

    target_stat = '"nav_static": [round(float(x), 4) for x in nav_stat[1:]],'
    replacement_stat = '''"nav_static": [round(float(x), 4) for x in nav_stat[1:]],
            "static_nav": [round(float(x), 4) for x in nav_stat[1:]],'''

    if target_str in content:
        content = content.replace(target_str, replacement_str, 1)
    if target_stat in content:
        content = content.replace(target_stat, replacement_stat, 1)

    TARGET_FILE.write_text(content, encoding="utf-8")
    print("✅ Aliases dynamic_nav and static_nav added!")

if __name__ == "__main__":
    main()
