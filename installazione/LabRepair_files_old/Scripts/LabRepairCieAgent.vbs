' Avvia l'agent CIE locale (lettore Bit4id) se non e' gia' attivo.
Option Explicit

Dim sh, fso, agentDir, exe, http, started

Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

agentDir = sh.ExpandEnvironmentStrings("%LOCALAPPDATA%\LabRepairCieAgent")
exe = agentDir & "\cie_reader.exe"

If Not fso.FileExists(exe) Then
  ' Prova cartella accanto a questo script (deploy manuale).
  Dim localExe
  localExe = fso.BuildPath(fso.GetParentFolderName(WScript.ScriptFullName), "cie_agent\cie_reader.exe")
  If fso.FileExists(localExe) Then
    exe = localExe
  Else
    WScript.Quit 0
  End If
End If

If IsAgentHealthy() Then
  WScript.Quit 0
End If

On Error Resume Next
sh.Run """" & exe & """ --serve", 0, False
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
  http.Open "GET", "http://127.0.0.1:17345/health", False
  http.setTimeouts 500, 500, 1000, 1000
  http.Send
  IsAgentHealthy = (http.Status = 200)
End Function
