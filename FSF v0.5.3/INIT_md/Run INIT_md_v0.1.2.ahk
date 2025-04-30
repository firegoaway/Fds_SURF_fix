#NoEnv  ; Recommended for performance and compatibility with future AutoHotkey releases.
; #Warn  ; Enable warnings to assist with detecting common errors.
SendMode Input  ; Recommended for new scripts due to its superior speed and reliability.
SetWorkingDir %A_ScriptDir%  ; Ensures a consistent starting directory.

;	Генерируем УИН для каждого нового инстанса
ProcessID := DllCall("GetCurrentProcessId")
UniqueID := ProcessID

filePath := A_ScriptDir "\06c856a8_nfs.fds"
filePathIni := A_ScriptDir "\inis\filePath_" UniqueID ".ini"

IniWrite, %filePath%, %filePathIni%, filePath, 

Run, python.exe "E:\FIREGOAWAY\GitHub\Fds_SURF_fix\FSF v0.5.0\INIT_md\p_libs\INIT_md_v0.1.2.cpython-311.pyc" %ProcessID%, , , PID
Return