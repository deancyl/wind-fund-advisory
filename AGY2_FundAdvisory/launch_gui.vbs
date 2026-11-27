' =========================================================================
' AGY2 Quantitative Robo-Advisory Workstation - Windows Desktop Launcher
' Pure background silent execution with MS Edge App Mode (No console window)
' Hardened with Windows 8.3 ShortPath against CMD quote-stripping pitfalls
' Adaptive Port Discovery (8501 -> 8585 fallback) for Windows WinNAT Exclusion
' =========================================================================

Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' Get current workspace directory
currentDir = fso.GetParentFolderName(WScript.ScriptFullName)
If fso.FolderExists(currentDir) Then
    currentDir = fso.GetFolder(currentDir).ShortPath
End If

' Function to check if Streamlit HTTP server on a port is responding
Function IsPortListening(port)
    On Error Resume Next
    Set http = CreateObject("MSXML2.ServerXMLHTTP.6.0")
    http.setTimeouts 500, 500, 500, 500
    http.open "GET", "http://127.0.0.1:" & port & "/_stcore/health", False
    http.send
    If Err.Number = 0 And (http.status = 200 Or http.status = 304) Then
        IsPortListening = True
    Else
        IsPortListening = False
    End If
    Set http = Nothing
    On Error Goto 0
End Function

' 1. Detect active port
activePort = 0
If IsPortListening(8501) Then
    activePort = 8501
ElseIf IsPortListening(8585) Then
    activePort = 8585
End If

' 2. If neither port is listening, launch Streamlit
If activePort = 0 Then
    pythonExe = "python"
    localPy = WshShell.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\Programs\Python\Python311\python.exe"
    If fso.FileExists(localPy) Then
        pythonExe = fso.GetFile(localPy).ShortPath
    End If
    WshShell.CurrentDirectory = currentDir

    ' Try 8501 first
    cmdStart8501 = """" & pythonExe & """ -m streamlit run app_gui.py --server.headless=true --server.port=8501"
    WshShell.Run cmdStart8501, 0, False

    For i = 1 To 4
        WScript.Sleep 1000
        If IsPortListening(8501) Then
            activePort = 8501
            Exit For
        End If
    Next

    ' If 8501 failed (e.g. WinError 10013 port exclusion), fallback to 8585
    If activePort = 0 Then
        cmdStart8585 = """" & pythonExe & """ -m streamlit run app_gui.py --server.headless=true --server.port=8585"
        WshShell.Run cmdStart8585, 0, False
        For i = 1 To 12
            WScript.Sleep 1000
            If IsPortListening(8585) Then
                activePort = 8585
                Exit For
            End If
        Next
    End If
End If

' Default fallback port
If activePort = 0 Then
    activePort = 8585
End If

' 3. Locate Microsoft Edge executable
edgePath = ""
If fso.FileExists("C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe") Then
    edgePath = fso.GetFile("C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe").ShortPath
ElseIf fso.FileExists("C:\Program Files\Microsoft\Edge\Application\msedge.exe") Then
    edgePath = fso.GetFile("C:\Program Files\Microsoft\Edge\Application\msedge.exe").ShortPath
End If

' 4. Launch in standalone Desktop App Mode (--app=..., no address bar, no tabs)
appUrl = "http://127.0.0.1:" & activePort
If edgePath <> "" Then
    WshShell.Run edgePath & " --app=" & appUrl, 1, False
Else
    WshShell.Run "cmd.exe /c start msedge --app=" & appUrl, 0, False
End If

Set WshShell = Nothing
Set fso = Nothing
