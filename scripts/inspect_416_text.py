# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')
import subprocess
import bs4

html = subprocess.check_output(['curl.exe', '-k', '-s', 'https://hnsggzyjy.henan.gov.cn/jyxx/002003/002003007/20261010/28777cef49f741749bd7c7f1385a7970.html']).decode('utf-8', errors='ignore')
soup = bs4.BeautifulSoup(html, 'html.parser')
text = soup.get_text()
for line in text.splitlines():
    line = line.strip()
    if any(k in line for k in ['挂牌', '起拍', '底价', '租金', '万元', '元', '价']):
        print("MATCH:", line[:100])
