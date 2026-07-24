' LabRepair App - finestra dedicata (senza schede browser)
' Doppio clic, oppure crea un collegamento sul Desktop.
' Per cambiare server: modifica la riga Origin = ...

Option Explicit

Dim sh, fso, Origin, Login, Profile, Browser, Args, Desktop, Lnk

Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

Origin = "http://192.168.200.30:8000"
Login = Origin & "/login/?app=1"
Profile = sh.ExpandEnvironmentStrings("%LOCALAPPDATA%\LabRepairApp")

If Not fso.FolderExists(Profile) Then
  fso.CreateFolder Profile
End If

Browser = FindBrowser()
If Browser = "" Then
  MsgBox "Chrome o Edge non trovati. Installali e riprova.", vbCritical, "LabRepair"
  WScript.Quit 1
End If

' --app = sembra un'applicazione (niente barra indirizzi / schede)
Args = "--app=""" & Login & """" & _
       " --user-data-dir=""" & Profile & """" & _
       " --unsafely-treat-insecure-origin-as-secure=" & Origin & _
       " --test-type" & _
       " --disable-features=InsecureDownloadWarnings"

' Lettore CIE sul PC client: avvia agent locale se installato.
Dim cieAgentVbs
cieAgentVbs = fso.BuildPath(fso.GetParentFolderName(WScript.ScriptFullName), "LabRepairCieAgent.vbs")
If fso.FileExists(cieAgentVbs) Then
  sh.Run "wscript.exe //nologo """ & cieAgentVbs & """", 0, False
End If

sh.Run """" & Browser & """ " & Args, 1, False

' Crea/aggiorna collegamento Desktop "LabRepair"
On Error Resume Next
Desktop = sh.SpecialFolders("Desktop")
IconFile = fso.BuildPath(fso.GetParentFolderName(WScript.ScriptFullName), "LabRepair.ico")
Set Lnk = sh.CreateShortcut(Desktop & "\LabRepair.lnk")
Lnk.TargetPath = WScript.ScriptFullName
Lnk.WorkingDirectory = fso.GetParentFolderName(WScript.ScriptFullName)
Lnk.WindowStyle = 1
If fso.FileExists(IconFile) Then
  Lnk.IconLocation = IconFile & ",0"
Else
  Lnk.IconLocation = Browser & ",0"
End If
Lnk.Description = "LabRepair"
Lnk.Save
On Error GoTo 0

WScript.Quit 0

Function FindBrowser()
  Dim candidates, i, path
  candidates = Array( _
    sh.ExpandEnvironmentStrings("%ProgramFiles%\Google\Chrome\Application\chrome.exe"), _
    sh.ExpandEnvironmentStrings("%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"), _
    sh.ExpandEnvironmentStrings("%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"), _
    sh.ExpandEnvironmentStrings("%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"), _
    sh.ExpandEnvironmentStrings("%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe") _
  )
  For i = 0 To UBound(candidates)
    path = candidates(i)
    If path <> "" And fso.FileExists(path) Then
      FindBrowser = path
      Exit Function
    End If
  Next
  FindBrowser = ""
End Function
