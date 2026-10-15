import re
import urllib.request

# 读取 /baokan/ 和 /site 页面，提取所有河南报纸的 showpress ID
papers_map = {
    "郑州日报": {"official": "https://zzrb.zynews.cn/", "showpress": "http://www.53bk.com/site/showpress/1120.html"},
    "郑州晚报": {"official": "https://zzwb.zynews.cn/", "showpress": "http://www.53bk.com/site/showpress/1121.html"},
    "河南日报": {"official": "https://newpaper.dahe.cn/hnrb/", "showpress": "http://www.53bk.com/site/showpress/408.html"},
    "大河报": {"official": "https://newpaper.dahe.cn/dhb/", "showpress": "http://www.53bk.com/site/showpress/404.html"},
    "河南法制报": {"official": "http://epaper.hnfzb.com:8080/", "showpress": "http://www.53bk.com/site/showpress/409.html"},
    "河南商报": {"official": "https://newpaper.dahe.cn/hnsb/", "showpress": "http://www.53bk.com/site/showpress/404.html"},
    "开封日报": {"official": "https://www.kf.cn/", "showpress": "http://www.53bk.com/site/showpress/398.html"},
    "汴梁晚报": {"official": "https://www.kf.cn/", "showpress": "http://www.53bk.com/site/showpress/398.html"},
    "洛阳日报": {"official": "http://lyrb.lyd.com.cn/", "showpress": "http://www.53bk.com/site/showpress/411.html"},
    "洛阳晚报": {"official": "http://lywb.lyd.com.cn/", "showpress": "http://www.53bk.com/site/showpress/411.html"},
    "平顶山日报": {"official": "http://epaper.pdsxww.com/pdsrb/", "showpress": "http://www.53bk.com/site/showpress/413.html"},
    "平顶山晚报": {"official": "http://epaper.pdsxww.com/pdswb/", "showpress": "http://www.53bk.com/site/showpress/413.html"},
    "安阳日报": {"official": "https://www.ayrbs.com/szb/", "showpress": "http://www.53bk.com/site/showpress/407.html"},
    "鹤壁日报": {"official": "https://paper.hebiw.com/epaper/hbrb/", "showpress": "http://www.53bk.com/site/showpress/416.html"},
    "新乡日报": {"official": "http://rb.xxrb.com.cn/", "showpress": "http://www.53bk.com/site/showpress/417.html"},
    "平原晚报": {"official": "http://wb.xxrb.com.cn/", "showpress": "http://www.53bk.com/site/showpress/10907.html"},
    "焦作日报": {"official": "http://epaper.jzrb.com/", "showpress": "http://www.53bk.com/site/showpress/419.html"},
    "焦作晚报": {"official": "http://wbpaper.jzrb.com/", "showpress": "http://www.53bk.com/site/showpress/419.html"},
    "濮阳日报": {"official": "http://pyrb.pyxww.com/", "showpress": "http://www.53bk.com/site/showpress/421.html"},
    "许昌日报": {"official": "http://www.21xc.com/", "showpress": "http://www.53bk.com/site/showpress/1119.html"},
    "许昌晨报": {"official": "http://szb.21xc.com/xccb/", "showpress": "http://www.53bk.com/site/showpress/1119.html"},
    "漯河日报": {"official": "http://www.lhrb.com.cn/", "showpress": "http://www.53bk.com/site/showpress/10910.html"},
    "三门峡日报": {"official": "https://szb.ismx.cn/smxrb/", "showpress": "http://www.53bk.com/site/showpress/398.html"},
    "南阳日报": {"official": "http://epaper.01ny.cn/", "showpress": "http://www.53bk.com/site/showpress/13229.html"},
    "南阳晚报": {"official": "http://epaper.01ny.cn/", "showpress": "http://www.53bk.com/site/showpress/13229.html"},
    "商丘日报": {"official": "https://epaper.sqrb.com.cn/", "showpress": "http://www.53bk.com/site/showpress/13488.html"},
    "京九晚报": {"official": "https://epaper.sqrb.com.cn/", "showpress": "http://www.53bk.com/site/showpress/13488.html"},
    "信阳日报": {"official": "https://ribao.xyxww.com.cn/", "showpress": "http://www.53bk.com/site/showpress/419.html"},
    "周口日报": {"official": "http://www.zhld.com/", "showpress": "http://www.53bk.com/site/showpress/412.html"},
    "驻马店日报": {"official": "http://zmdrb.zmdnews.cn/", "showpress": "http://www.53bk.com/site/showpress/13488.html"},
    "济源日报": {"official": "http://www.jyrb.cn/", "showpress": "http://www.53bk.com/site/showpress/421.html"}
}
print(f"Total mapped papers: {len(papers_map)}")
