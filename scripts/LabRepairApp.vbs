' LabRepair App - finestra dedicata (senza schede browser)
' Doppio clic, oppure crea un collegamento sul Desktop.
' Per cambiare server: modifica origin.txt accanto a questo file.

Option Explicit

Dim sh, fso, Origin, Login, Profile, Browser, Args, Desktop, Lnk, ComputerName
Dim IconFile, originFile, ts, line

Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

Origin = "http://127.0.0.1:8000"
originFile = fso.BuildPath(fso.GetParentFolderName(WScript.ScriptFullName), "origin.txt")
If fso.FileExists(originFile) Then
  Set ts = fso.OpenTextFile(originFile, 1)
  If Not ts.AtEndOfStream Then
    line = Trim(ts.ReadLine)
    If line <> "" Then Origin = line
  End If
  ts.Close
End If
If Right(Origin, 1) = "/" Then Origin = Left(Origin, Len(Origin) - 1)

ComputerName = sh.ExpandEnvironmentStrings("%COMPUTERNAME%")
Login = Origin & "/login/?app=1&pc=" & ComputerName
Profile = sh.ExpandEnvironmentStrings("%LOCALAPPDATA%\LabRepairApp")

If Not fso.FolderExists(Profile) Then
  fso.CreateFolder Profile
End If

' Policy utente: evita etichetta "Non sicuro" su HTTP LAN (Chrome/Edge).
ApplyInsecureOriginPolicy Origin

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
       " --disable-features=InsecureDownloadWarnings,HttpsFirstBalancedModeAutoEnable,HttpsUpgrades,HttpsFirstModeV2,HttpsFirstModeV2ForEngagedSites,HttpsFirstModeV2ForTypicallySecureUsers"

' Lettore CIE sul PC client: avvia agent locale se installato.
Dim cieAgentVbs
cieAgentVbs = fso.BuildPath(fso.GetParentFolderName(WScript.ScriptFullName), "LabRepairCieAgent.vbs")
If fso.FileExists(cieAgentVbs) Then
  sh.Run "wscript.exe //nologo """ & cieAgentVbs & """", 0, False
End If

' Agent stampanti sul PC client (Brother / stampanti di cassa).
Dim printerAgentVbs
printerAgentVbs = fso.BuildPath(fso.GetParentFolderName(WScript.ScriptFullName), "LabRepairPrinterAgent.vbs")
If fso.FileExists(printerAgentVbs) Then
  sh.Run "wscript.exe //nologo """ & printerAgentVbs & """", 0, False
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
  ' Preferisci Chrome: su Server 2022 Edge in --app mostra spesso "Non sicuro".
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

Sub ApplyInsecureOriginPolicy(ByVal originUrl)
  On Error Resume Next
  ' Stessa policy documentata da Microsoft/Google: toglie "Not secure" / "Non sicuro".
  sh.RegWrite "HKCU\Software\Policies\Google\Chrome\OverrideSecurityRestrictionsOnInsecureOrigin\1", originUrl, "REG_SZ"
  sh.RegWrite "HKCU\Software\Policies\Microsoft\Edge\OverrideSecurityRestrictionsOnInsecureOrigin\1", originUrl, "REG_SZ"
  ' Anche machine-wide se abbiamo privilegi (ignore se Access denied).
  sh.RegWrite "HKLM\SOFTWARE\Policies\Google\Chrome\OverrideSecurityRestrictionsOnInsecureOrigin\1", originUrl, "REG_SZ"
  sh.RegWrite "HKLM\SOFTWARE\Policies\Microsoft\Edge\OverrideSecurityRestrictionsOnInsecureOrigin\1", originUrl, "REG_SZ"
  On Error GoTo 0
End Sub
