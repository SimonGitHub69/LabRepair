' LabRepair App - finestra dedicata (senza schede browser)
' Doppio clic, oppure crea un collegamento sul Desktop.
' Per cambiare server: modifica origin.txt accanto a questo file.

Option Explicit

Dim sh, fso, Origin, Login, Profile, Browser, Args, Desktop, Lnk, ComputerName
Dim IconFile, originFile, ts, line
Dim AppDir, updateScript, psCmd

Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

AppDir = fso.GetParentFolderName(WScript.ScriptFullName)
Origin = "http://127.0.0.1:8000"
originFile = fso.BuildPath(AppDir, "origin.txt")
If fso.FileExists(originFile) Then
  Set ts = fso.OpenTextFile(originFile, 1)
  If Not ts.AtEndOfStream Then
    line = Trim(ts.ReadLine)
    If line <> "" Then Origin = line
  End If
  ts.Close
End If
If Right(Origin, 1) = "/" Then Origin = Left(Origin, Len(Origin) - 1)

' All'avvio: controlla aggiornamenti client dal server (silenzioso se non disponibili).
updateScript = fso.BuildPath(AppDir, "check_client_update.ps1")
If fso.FileExists(updateScript) Then
  On Error Resume Next
  ' -STA serve alla finestra di avanzamento WinForms durante update.
  psCmd = "powershell.exe -NoProfile -ExecutionPolicy Bypass -STA -WindowStyle Hidden -File """ & updateScript & """ -Origin """ & Origin & """ -AppDir """ & AppDir & """"
  sh.Run psCmd, 0, True
  On Error GoTo 0
End If

ComputerName = sh.ExpandEnvironmentStrings("%COMPUTERNAME%")
Login = Origin & "/login/?app=1&pc=" & ComputerName
Profile = sh.ExpandEnvironmentStrings("%LOCALAPPDATA%\LabRepairApp")

If Not fso.FolderExists(Profile) Then
  fso.CreateFolder Profile
End If

ApplyInsecureOriginPolicy Origin

Browser = FindBrowser()
If Browser = "" Then
  MsgBox "Chrome o Edge non trovati. Installali e riprova.", vbCritical, "LabRepair"
  WScript.Quit 1
End If

Args = "--app=""" & Login & """" & _
       " --user-data-dir=""" & Profile & """" & _
       " --unsafely-treat-insecure-origin-as-secure=" & Origin & _
       " --test-type" & _
       " --disable-features=InsecureDownloadWarnings,HttpsFirstBalancedModeAutoEnable,HttpsUpgrades,HttpsFirstModeV2,HttpsFirstModeV2ForEngagedSites,HttpsFirstModeV2ForTypicallySecureUsers,LocalNetworkAccessChecks,BlockInsecurePrivateNetworkRequests,PrivateNetworkAccessSendPreflights"

Dim cieAgentVbs
cieAgentVbs = fso.BuildPath(AppDir, "LabRepairCieAgent.vbs")
If fso.FileExists(cieAgentVbs) Then
  sh.Run "wscript.exe //nologo """ & cieAgentVbs & """", 0, False
End If

Dim printerAgentVbs
printerAgentVbs = fso.BuildPath(AppDir, "LabRepairPrinterAgent.vbs")
If fso.FileExists(printerAgentVbs) Then
  sh.Run "wscript.exe //nologo """ & printerAgentVbs & """", 0, False
End If

sh.Run """" & Browser & """ " & Args, 1, False

On Error Resume Next
Desktop = sh.SpecialFolders("Desktop")
IconFile = fso.BuildPath(AppDir, "LabRepair.ico")
Set Lnk = sh.CreateShortcut(Desktop & "\LabRepair.lnk")
Lnk.TargetPath = WScript.ScriptFullName
Lnk.WorkingDirectory = AppDir
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

Sub ApplyInsecureOriginPolicy(ByVal originUrl)
  On Error Resume Next
  sh.RegWrite "HKCU\Software\Policies\Google\Chrome\OverrideSecurityRestrictionsOnInsecureOrigin\1", originUrl, "REG_SZ"
  sh.RegWrite "HKCU\Software\Policies\Microsoft\Edge\OverrideSecurityRestrictionsOnInsecureOrigin\1", originUrl, "REG_SZ"
  sh.RegWrite "HKCU\Software\Policies\Google\Chrome\LocalNetworkAccessAllowedForUrls\1", originUrl, "REG_SZ"
  sh.RegWrite "HKCU\Software\Policies\Microsoft\Edge\LocalNetworkAccessAllowedForUrls\1", originUrl, "REG_SZ"
  sh.RegWrite "HKCU\Software\Policies\Google\Chrome\InsecurePrivateNetworkRequestsAllowedForUrls\1", originUrl, "REG_SZ"
  sh.RegWrite "HKCU\Software\Policies\Microsoft\Edge\InsecurePrivateNetworkRequestsAllowedForUrls\1", originUrl, "REG_SZ"
  sh.RegWrite "HKLM\SOFTWARE\Policies\Google\Chrome\OverrideSecurityRestrictionsOnInsecureOrigin\1", originUrl, "REG_SZ"
  sh.RegWrite "HKLM\SOFTWARE\Policies\Microsoft\Edge\OverrideSecurityRestrictionsOnInsecureOrigin\1", originUrl, "REG_SZ"
  sh.RegWrite "HKLM\SOFTWARE\Policies\Google\Chrome\LocalNetworkAccessAllowedForUrls\1", originUrl, "REG_SZ"
  sh.RegWrite "HKLM\SOFTWARE\Policies\Microsoft\Edge\LocalNetworkAccessAllowedForUrls\1", originUrl, "REG_SZ"
  On Error GoTo 0
End Sub
