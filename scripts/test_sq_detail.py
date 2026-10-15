import sys
sys.path.insert(0, '.')
import urllib.request
import ssl
import re
from bs4 import BeautifulSoup

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

req = urllib.request.Request(
    'https://ggzyjy.shangqiu.gov.cn/HNSQ/TradeCenter/ColTableInfo.do?',
    data=b'projectName=&date=&begin_time=&end_time=&dealType=Deal_Type7&noticType=1&area=&huanJie=NOTICE&pageIndex=1',
    headers={'User-Agent': 'Mozilla/5.0', 'Content-Type': 'application/x-www-form-urlencoded'}
)
html = urllib.request.urlopen(req, context=ctx).read().decode('utf-8')
soup = BeautifulSoup(html, 'html.parser')
links = soup.find_all('a')
print(f"Links found: {len(links)}")
for a in links[:3]:
    href = a.get('href')
    title = a.get_text(strip=True)
    full_url = f"https://ggzyjy.shangqiu.gov.cn{href}" if href.startswith('/') else href
    print(f"Title: {title}\nURL: {full_url}")
    # Fetch detail
    try:
        det_req = urllib.request.Request(full_url, headers={'User-Agent': 'Mozilla/5.0'})
        det_html = urllib.request.urlopen(det_req, context=ctx).read().decode('utf-8')
        det_soup = BeautifulSoup(det_html, 'html.parser')
        text = det_soup.get_text(separator=' ', strip=True)
        from backend.utils import extract_starting_and_eval_price
        sp, ep = extract_starting_and_eval_price(title, text)
        print(f"  Extracted SP: {sp}, EP: {ep}")
    except Exception as e:
        print(f"  Detail error: {e}")
