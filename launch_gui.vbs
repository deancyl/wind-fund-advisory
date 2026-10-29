' =========================================================================
' AGY2 Quantitative Robo-Advisory Workstation - Root Launcher Trampoline
' =========================================================================

Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

currentDir = fso.GetParentFolderName(WScript.ScriptFullName)
targetVbs = currentDir & "\AGY2_FundAdvisory\launch_gui.vbs"

If fso.FileExists(targetVbs) Then
    WshShell.Run "wscript.exe """ & targetVbs & """", 0, False
End If

Set WshShell = Nothing
Set fso = Nothing
