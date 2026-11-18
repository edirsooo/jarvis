' Abre o Jarvis sem janela de terminal: servidor escondido, janela própria e ícone na bandeja.
Set fso = CreateObject("Scripting.FileSystemObject")
pasta = fso.GetParentFolderName(WScript.ScriptFullName)
Set sh = CreateObject("WScript.Shell")
sh.CurrentDirectory = pasta
sh.Run "pythonw """ & pasta & "\jarvis.py"" --janela", 0, False
