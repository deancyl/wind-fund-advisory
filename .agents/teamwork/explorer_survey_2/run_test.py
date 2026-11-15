import sys
import subprocess

res = subprocess.run([sys.executable, "-m", "pytest", "tests/test_portfolio_manager.py", "-q"], cwd="AGY2_FundAdvisory", capture_output=True, text=True)
print("Return code:", res.returncode)
print(res.stdout)
print(res.stderr)
