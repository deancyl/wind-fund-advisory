' AGY2-FundAdvisory Modern Web App Silent Launcher (No Console Window)
' Single-port architecture: FastAPI (127.0.0.1:8000) + Edge --app mode

Option Explicit
Dim fso, shell, scriptDir, url, http, i, ready, pyCmd, edgePath

Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
url = "http://127.0.0.1:8000/"

Function IsServerReady()
    On Error Resume Next
    Set http = CreateObject("MSXML2.ServerXMLHTTP.6.0")
    http.setTimeouts 400, 400, 400, 400
    http.Open "GET", "http://127.0.0.1:8000/api/v1/ledgers", False
    http.Send
    IsServerReady = (Err.Number = 0 And http.Status = 200)
    On Error GoTo 0
End Function

If Not IsServerReady() Then
    shell.CurrentDirectory = scriptDir
    If shell.Run("cmd.exe /c where py >nul 2>&1", 0, True) = 0 Then
        pyCmd = "py -3 -m uvicorn api_server:app --app-dir AGY2_FundAdvisory --host 127.0.0.1 --port 8000"
    Else
        pyCmd = "python -m uvicorn api_server:app --app-dir AGY2_FundAdvisory --host 127.0.0.1 --port 8000"
    End If
    shell.Run pyCmd, 0, False
    ready = False
    For i = 1 To 30
        WScript.Sleep 500
        If IsServerReady() Then
            ready = True
            Exit For
        End If
    Next
End If

edgePath = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
If Not fso.FileExists(edgePath) Then
    edgePath = "C:\Program Files\Microsoft\Edge\Application\msedge.exe"
End If

If fso.FileExists(edgePath) Then
    shell.Run """" & edgePath & """ --app=" & url, 1, False
Else
    shell.Run url, 1, False
End If
