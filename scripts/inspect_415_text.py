# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')
import subprocess
import bs4
import re

html = subprocess.check_output(['curl.exe', '-k', '-s', 'https://hnsggzyjy.henan.gov.cn/jyxx/002003/002003001/20261010/eaacf5cc-c2d4-4452-ad7c-5857d588bb2e.html']).decode('utf-8', errors='ignore')
soup = bs4.BeautifulSoup(html, 'html.parser')
text = soup.get_text()
for line in text.splitlines():
    line = line.strip()
    if any(k in line for k in ['挂牌', '起拍', '底价', '租金', '万元', '元']):
        print("MATCH:", line[:100])
