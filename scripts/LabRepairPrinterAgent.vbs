' Avvia l'agent stampanti locale se non e' gia' attivo.
Option Explicit

Dim sh, fso, agentDir, ps1, http

Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

agentDir = sh.ExpandEnvironmentStrings("%LOCALAPPDATA%\LabRepairPrinterAgent")
ps1 = agentDir & "\printer_agent.ps1"

If Not fso.FileExists(ps1) Then
  Dim localPs1
  localPs1 = fso.BuildPath(fso.GetParentFolderName(WScript.ScriptFullName), "..\tools\printer_agent\printer_agent.ps1")
  If fso.FileExists(localPs1) Then
    ps1 = localPs1
  Else
    WScript.Quit 0
  End If
End If

If IsAgentHealthy() Then
  WScript.Quit 0
End If

On Error Resume Next
sh.Run "powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -WindowStyle Hidden -File """ & ps1 & """", 0, False
WScript.Quit 0

Function IsAgentHealthy()
  On Error Resume Next
  Set http = CreateObject("MSXML2.ServerXMLHTTP.6.0")
  If http Is Nothing Then
    Set http = CreateObject("MSXML2.ServerXMLHTTP")
  End If
  If http Is Nothing Then
    IsAgentHealthy = False
    Exit Function
  End If
  http.Open "GET", "http://127.0.0.1:17346/health", False
  http.setTimeouts 500, 500, 1000, 1000
  http.Send
  IsAgentHealthy = (http.Status = 200)
End Function
