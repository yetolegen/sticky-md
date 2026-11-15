$dir = Split-Path -Parent $MyInvocation.MyCommand.Path
$py = (Get-Command pythonw).Source
$link = Join-Path ([Environment]::GetFolderPath("Desktop")) "sticky-md.lnk"
$s = (New-Object -ComObject WScript.Shell).CreateShortcut($link)
$s.TargetPath = $py
$s.Arguments = "`"$dir\stickies.py`""
$s.WorkingDirectory = $dir
$s.IconLocation = "$py,0"
$s.Save()
