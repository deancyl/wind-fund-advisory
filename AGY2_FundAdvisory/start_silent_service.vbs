' =========================================================================
' Streamlit Background Daemon Launcher (Pure Silent No-Window Detached)
' =========================================================================
Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

currentDir = fso.GetParentFolderName(WScript.ScriptFullName)
pythonExe = "py -3.11"
If fso.FileExists("C:\Users\deanc\AppData\Local\Programs\Python\Python311\python.exe") Then
    pythonExe = """C:\Users\deanc\AppData\Local\Programs\Python\Python311\python.exe"""
End If

WshShell.CurrentDirectory = currentDir
cmdStart = "cmd.exe /c cd /d """ & currentDir & """ && " & pythonExe & " -m streamlit run app_gui.py --server.headless=true --server.port=8501"
WshShell.Run cmdStart, 0, False

Set WshShell = Nothing
Set fso = Nothing
