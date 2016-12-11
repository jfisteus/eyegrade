;NSIS Eyegrade script

;--------------------------------
;Includes

  ; Modern UI
  !include "MUI2.nsh"

  ; For computing installation size
  !include "FileFunc.nsh"
 
;--------------------------------
;General
  !define VERSION "0.7b2"
  !define EYEGRADE_DIR "..\.."
  
  ;Name and file
  Name "Eyegrade ${VERSION}"
  OutFile "${EYEGRADE_DIR}\dist\eyegrade-setup-${VERSION}.exe"

  ;Default installation folder
  InstallDir "$LOCALAPPDATA\Eyegrade"
  
  ;Get installation folder from registry if available
  InstallDirRegKey HKCU "Software\Eyegrade" ""

  ;Request application privileges for Windows Vista
  RequestExecutionLevel user

;--------------------------------
;Variables

  Var StartMenuFolder

;--------------------------------
;Interface Settings

  !define MUI_ABORTWARNING

;--------------------------------
;Pages

  !insertmacro MUI_PAGE_LICENSE "${EYEGRADE_DIR}\COPYING.TXT"
  ;!insertmacro MUI_PAGE_COMPONENTS
  !insertmacro MUI_PAGE_DIRECTORY
  
  ;Start Menu Folder Page Configuration
  !define MUI_STARTMENUPAGE_REGISTRY_ROOT "HKCU" 
  !define MUI_STARTMENUPAGE_REGISTRY_KEY "Software\Eyegrade" 
  !define MUI_STARTMENUPAGE_REGISTRY_VALUENAME "Start Menu Folder"
  
  !insertmacro MUI_PAGE_STARTMENU Application $StartMenuFolder
  
  !insertmacro MUI_PAGE_INSTFILES
  !define MUI_FINISHPAGE_NOAUTOCLOSE
  !define MUI_FINISHPAGE_RUN
  !define MUI_FINISHPAGE_RUN_NOTCHECKED
  !define MUI_FINISHPAGE_RUN_TEXT "$(MsgRunEyegrade)"
  !define MUI_FINISHPAGE_RUN_FUNCTION "LaunchApplication"
  !insertmacro MUI_PAGE_FINISH
  
  !insertmacro MUI_UNPAGE_CONFIRM
  !insertmacro MUI_UNPAGE_INSTFILES

;--------------------------------
;Languages
 
  !insertmacro MUI_LANGUAGE "English"
  !insertmacro MUI_LANGUAGE "Spanish"
  !insertmacro MUI_LANGUAGE "Galician"

  LangString MsgEyegradeRunning ${LANG_ENGLISH} \
             "Eyegrade is running. Please, close it and try again" 
  LangString MsgEyegradeRunning ${LANG_SPANISH} \
             "Eyegrade se está ejecutando. Por favor, ciérrelo y vuélvalo a intentar" 
  LangString MsgEyegradeRunning ${LANG_GALICIAN} \
             "Eyegrade estase a executar. Por favor, cérreo e volva intentalo" 
  LangString MsgRunEyegrade ${LANG_ENGLISH} \
             "Run Eyegrade when finished"
  LangString MsgRunEyegrade ${LANG_SPANISH} \
             "Ejecutar Eyegrade al finalizar"
  LangString MsgRunEyegrade ${LANG_GALICIAN} \
             "Executar Eyegrade ó rematar"

;--------------------------------
;Installer Sections

Section "" UninstallPreviousVersion
;  MessageBox MB_OK "check for previous version"
  ReadRegStr $R0 HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Eyegrade" \
             "QuietUninstallString"
  StrCmp $R0 "" done
  ExecWait '$R0'
done:

SectionEnd


Section "Installing Eyegrade Files" InstEyegradeFiles

  SetOutPath "$INSTDIR"
  
  !define SOURCE_DIR "${EYEGRADE_DIR}\dist\eyegrade"
  
  !include "${EYEGRADE_DIR}\build\install_files.nsh"
  
  File "${EYEGRADE_DIR}\eyegrade\data\eyegrade.ico"
  File "${EYEGRADE_DIR}\AUTHORS.TXT"
  File "${EYEGRADE_DIR}\COPYING.TXT"
  File "/oname=README.TXT" "${EYEGRADE_DIR}\README"
  File "/oname=CHANGELOG.TXT" "${EYEGRADE_DIR}\Changelog"

  ;Store installation folder
  WriteRegStr HKCU "Software\Eyegrade" "" $INSTDIR
  WriteRegStr HKCU "Software\Eyegrade" "Version" "${VERSION}"
  
  ;Create uninstaller
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  
  !insertmacro MUI_STARTMENU_WRITE_BEGIN Application
    
    ;Create shortcuts
    CreateDirectory "$SMPROGRAMS\$StartMenuFolder"
    CreateShortcut "$SMPROGRAMS\$StartMenuFolder\Eyegrade.lnk" "$INSTDIR\eyegrade.exe"
    CreateShortcut "$SMPROGRAMS\$StartMenuFolder\Uninstall.lnk" "$INSTDIR\Uninstall.exe"
  
  !insertmacro MUI_STARTMENU_WRITE_END

  ; Information for the uninstall menu
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Eyegrade" \
                   "DisplayName" "Eyegrade"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Eyegrade" \
                   "UninstallString" "$\"$INSTDIR\uninstall.exe$\""
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Eyegrade" \
                   "QuietUninstallString" "$\"$INSTDIR\uninstall.exe$\" /S"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Eyegrade" \
                   "DisplayIcon" "$\"$INSTDIR\eyegrade.ico$\""
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Eyegrade" \
                   "DisplayVersion" "${VERSION}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Eyegrade" \
                   "Publisher" "Jesus Arias Fisteus"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Eyegrade" \
                   "URLInfoAbout" "http://www.eyegrade.org/"
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Eyegrade" \
                     "NoModify" "1"
  ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
  IntFmt $0 "0x%08X" $0
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Eyegrade" \
                     "EstimatedSize" "$0"
  
SectionEnd

;--------------------------------
;Descriptions

  ;Language strings
;  LangString DESC_InstEyegradeFiles ${LANG_ENGLISH} "Eyegrade executable files."

  ;Assign language strings to sections
 ; !insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
 ;   !insertmacro MUI_DESCRIPTION_TEXT ${InstEyegradeFiles} $(DESC_InstEyegradeFiles)
 ; !insertmacro MUI_FUNCTION_DESCRIPTION_END
 
;--------------------------------
;Uninstaller Section

Section "Uninstall"
  
  Delete "$INSTDIR\eyegrade.ico"
  Delete "$INSTDIR\AUTHORS.TXT"
  Delete "$INSTDIR\COPYING.TXT"
  Delete "$INSTDIR\README.TXT"
  Delete "$INSTDIR\CHANGELOG.TXT"
  Delete "$INSTDIR\uninstall.exe"

  !include "${EYEGRADE_DIR}\build\uninstall_files.nsh"
  
  !insertmacro MUI_STARTMENU_GETFOLDER Application $StartMenuFolder
    
  Delete "$SMPROGRAMS\$StartMenuFolder\Eyegrade.lnk"
  Delete "$SMPROGRAMS\$StartMenuFolder\Uninstall.lnk"
  RMDir "$SMPROGRAMS\$StartMenuFolder"
  
  DeleteRegKey HKCU "Software\Eyegrade\Version"
  DeleteRegKey /ifempty HKCU "Software\Eyegrade"
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Eyegrade"
SectionEnd

Function LaunchApplication
  ExecShell "" "$INSTDIR\Eyegrade.exe"
FunctionEnd

Function .onInit
  FindWindow $0 "" "Eyegrade"
  StrCmp $0 0 notRunning
    MessageBox MB_OK|MB_ICONEXCLAMATION "$(MsgEyegradeRunning)" /SD IDOK
    Abort
notRunning:
FunctionEnd

Function un.onInit
  FindWindow $0 "" "Eyegrade"
  StrCmp $0 0 notRunning
    MessageBox MB_OK|MB_ICONEXCLAMATION "$(MsgEyegradeRunning)" /SD IDOK
    Abort
notRunning:
FunctionEnd
