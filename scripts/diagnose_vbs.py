import subprocess

vbs_content = r'''Set oShell = CreateObject("WScript.Shell")
oShell.CurrentDirectory = "F:\antigravity exports\英语绘本"
Set oEnv = oShell.Environment("PROCESS")
oEnv("PATH") = "F:\Node.js;" & oEnv("PATH")
oShell.Run "cmd /c npm.cmd run dev > F:\vbs_test.log 2>&1", 0, True
'''

with open(r'F:\test_run.vbs', 'w', encoding='ascii') as f:
    f.write(vbs_content)

subprocess.run(['cscript', '//nologo', r'F:\test_run.vbs'])

try:
    with open(r'F:\vbs_test.log', 'r', encoding='utf-8', errors='ignore') as f:
        print('=== VBS TEST LOG ===')
        print(f.read())
except Exception as e:
    print('Error reading log:', e)
