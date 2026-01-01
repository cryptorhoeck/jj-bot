' JJ-Bot Silent Launcher
' This script launches JJ-Bot without showing command prompt windows
' Double-click this file or create a shortcut to it on your desktop

Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")

' Get the directory where this script is located
ScriptDir = FSO.GetParentFolderName(WScript.ScriptFullName)

' Change to script directory
WshShell.CurrentDirectory = ScriptDir

' Run the batch file hidden (0 = hidden, False = don't wait)
WshShell.Run """" & ScriptDir & "\JJ-Bot.bat""", 0, False
