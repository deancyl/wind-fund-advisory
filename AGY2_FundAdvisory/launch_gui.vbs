' =========================================================================
' AGY2 Quantitative Robo-Advisory Workstation - Windows Desktop Launcher
' Pure background silent execution with MS Edge App Mode (No console window)
' =========================================================================

Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' Get current workspace directory
currentDir = fso.GetParentFolderName(WScript.ScriptFullName)

' Function to check if Streamlit HTTP server on port 8501 is responding
Function IsPortListening(port)
    On Error Resume Next
    Set http = CreateObject("MSXML2.ServerXMLHTTP.6.0")
    http.setTimeouts 500, 500, 500, 500
    http.open "GET", "http://127.0.0.1:" & port & "/_stcore/health", False
    http.send
    If Err.Number = 0 Then
        IsPortListening = True
    Else
        IsPortListening = False
    End If
    Set http = Nothing
    On Error Goto 0
End Function

' 1. If Streamlit is not yet listening, silently launch in background (SW_HIDE = 0)
If Not IsPortListening(8501) Then
    pythonExe = "python"
    If fso.FileExists("C:\Users\deanc\AppData\Local\Programs\Python\Python311\python.exe") Then
        pythonExe = """C:\Users\deanc\AppData\Local\Programs\Python\Python311\python.exe"""
    End If
    WshShell.CurrentDirectory = currentDir
    cmdStart = "cmd.exe /c cd /d """ & currentDir & """ && " & pythonExe & " -m streamlit run app_gui.py --server.headless=true --server.port=8501"
    WshShell.Run cmdStart, 0, False
    
    ' Wait for Streamlit to start listening (up to 12 seconds)
    For i = 1 To 12
        WScript.Sleep 1000
        If IsPortListening(8501) Then
            Exit For
        End If
    Next
End If

' 2. Locate Microsoft Edge executable
edgePath = ""
If fso.FileExists("C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe") Then
    edgePath = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
ElseIf fso.FileExists("C:\Program Files\Microsoft\Edge\Application\msedge.exe") Then
    edgePath = "C:\Program Files\Microsoft\Edge\Application\msedge.exe"
End If

' 3. Launch in standalone Desktop App Mode (--app=..., no address bar, no tabs)
If edgePath <> "" Then
    WshShell.Run """" & edgePath & """ --app=http://localhost:8501", 1, False
Else
    ' Fallback to system default handler
    WshShell.Run "cmd.exe /c start msedge --app=http://localhost:8501", 0, False
End If

Set WshShell = Nothing
Set fso = Nothing
