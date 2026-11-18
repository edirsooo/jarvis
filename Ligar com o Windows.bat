@echo off
chcp 65001 >nul
rem Cria (ou remove) o atalho que abre o Jarvis sozinho quando o Windows liga.
set "ATALHO=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\Jarvis.lnk"
if exist "%ATALHO%" (
  move /y "%ATALHO%" "%TEMP%\Jarvis-inicio-desligado.lnk" >nul
  echo O Jarvis NAO abre mais sozinho com o Windows.
) else (
  powershell -NoProfile -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut($env:ATALHO); $s.TargetPath='wscript.exe'; $s.Arguments='\"%~dp0Jarvis.vbs\"'; $s.WorkingDirectory='%~dp0'; $s.Save()"
  echo Pronto: o Jarvis vai abrir sozinho quando o Windows ligar.
  echo Rode este arquivo de novo para desligar.
)
pause
