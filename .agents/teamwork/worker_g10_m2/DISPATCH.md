## 2026-11-08T04:31:04Z
You are a versatile worker specializing in service lifecycle and UI verification (teamwork_worker).
Your working directory is: d:\Google\Workspace\Wind\.agents\teamwork\worker_g10_m2\

Mandatory read inputs:
- Read d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
- Read d:\Google\Workspace\Wind\GEMINI.md
- Read d:\Google\Workspace\Wind\AGENT_SPEC.md
- Read d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_11\SCOPE.md

Mission: Milestone M2 Service Smooth Restart & Multi-Modal Walkthrough
1. Terminate Old Service & Smooth Restart:
   - Follow GEMINI.md Rule 12 on transient port collision defense: run `netstat -ano | findstr 8501` to identify the listening PID. Terminate the old listening process.
   - Start the new Streamlit server in background:
     `py -3 -m streamlit run AGY2_FundAdvisory/app_gui.py --server.port 8501 --server.headless true`
   - Poll and verify the health endpoint `http://127.0.0.1:8501/_stcore/health` returns HTTP 200.
2. Multimodal Visual & Logic Walkthrough:
   - Check the running app on http://localhost:8501 (via AppTest, headless browser, or Python requests/probes):
     a. Double-wing dashboard: verify correlation stress mutation warning indicator card and stress test liquidity metrics in right wing (col_sentry);
     b. Tab 1 & Tab 2: verify large order liquidity haircut table and Plotly 3D Monte Carlo distribution chart;
     c. Theme adaptability (light, dark) and 640px mobile responsive layout (zero truncation, zero horizontal overflow, safe_markdown_html CommonMark 4+ space immunity).
3. Test & Verification Script:
   - Execute an AppTest / probe script verifying that all G10 UI components mount and render without raising exceptions.
4. Output:
   Write your detailed report with endpoint response, health verification, and UI component status to d:\Google\Workspace\Wind\.agents\teamwork\worker_g10_m2\handoff.md.
   When finished, send a message to your caller indicating you are done.
