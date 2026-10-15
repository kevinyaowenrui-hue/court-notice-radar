# 司法案件公示与法拍监控采集系统 (CourtNoticeRadar)

> 一套集 **阿里法拍**、**京东拍卖**、**《人民法院报》公告网**、**53BK 全国数字报刊** 于一体的法院案件公示与法拍标的定向监控、智能预警与检索平台。

---

## 🌟 核心特性

1. **多源全渠道覆盖**：
   * **阿里法拍 (sf.taobao.com)**：拍卖房产、工业厂房、采矿权、车辆等司法处置资产。
   * **京东拍卖 (paimai.jd.com)**：高频实时资产标的、评估价、拍卖阶段变动监控。
   * **《人民法院报》（人民法院公告网 rmfygg.court.gov.cn）**：全国权威开庭传票、送达裁判文书、执行公告、破产重整法定公示。
   * **53BK 地方电子报纸库 (www.53bk.com)**：深度利用 53BK 汇集建立全国 340+ 重点省市官方电子报纸入口字典，定向巡检本地《日报》《晚报》的第 3/4 版公告与声明专版，解决下沉基层案件无法获取的痛点。

2. **智能监控与规则匹配引擎**：
   * 支持按**重点当事人/债务人企业**、**执行法院**、**案号关键词/前缀**、**标的物全文关键词**、**起拍价格区间**灵活创建规则。
   * 采集入库时实时匹配，命中即生成高亮依据并推入预警中心。

3. **现代极简 Web 看板 (Zero-Jank 架构)**：
   * 🔔 **预警中心**：未读红点角标、命中依据卡片、一键直达官方原站、批量标记已读。
   * 📋 **公示与法拍检索库**：多维条件过滤、价格区间滑块、一键导出规范 Excel/CSV 报表。
   * ⚙️ **监控规则管理**：规则一键启停、多标签可视化编辑。
   * 📰 **53BK 地方报纸库**：全国 34 省市电子报纸导航，一键开启/暂停某份报刊的每日定向巡检。
   * 🚀 **采集任务大屏**：查看各渠道调度状态、耗时与增量统计，支持随时一键手动执行抓取。

4. **轻量无人值守部署**：
   * 后端基于 Python FastAPI + SQLAlchemy + SQLite (WAL 模式，零外部依赖，极速并发)。
   * 支持 Windows 本地一键运行 (`start.bat`)，以及 Linux/Docker 7×24 小时无人值守部署。

---

## 🚀 快速启动

### 方式 A：Windows 本地一键运行 (推荐)

直接双击运行根目录下的：
```cmd
start.bat
```
脚本将自动启动后台调度服务与 Web 管理界面，浏览器访问：
👉 **http://127.0.0.1:5220**

### 方式 B：命令行手动启动

```bash
# 1. 安装 Python 依赖
pip install -r requirements.txt

# 2. 编译前端静态页面（若需要更新界面）
cd frontend
npm install
npm run build
cd ..

# 3. 启动后台服务 (绑定 127.0.0.1:5220)
set SERVER_PORT=5220
python -m backend.app
```

### 方式 C：Docker 一键部署 (云服务器 7×24h 常驻)

```bash
docker compose up -d
```

---

## 📁 目录结构

```
.
├── backend/                  # Python 后端工程
│   ├── app.py               # FastAPI 路由与静态托管服务
│   ├── config.py            # 服务端口 (5220) 与运行配置
│   ├── database.py          # SQLite WAL 数据库连接
│   ├── models.py            # 统一公示与法拍数据模型、规则模型、种子模型
│   ├── mock_data.py         # 数据库初始化与初始数据同步
│   ├── engine/
│   │   ├── rule_matcher.py  # 智能规则匹配与高亮生成引擎
│   │   └── scheduler.py     # APScheduler 定时巡检后台调度器
│   └── crawlers/
│       ├── seed_53bk.py     # 53BK 全国报纸目录与电子报入口抽取器
│       ├── rmfyb_crawler.py # 《人民法院报》公告网官方采集器
│       ├── jd_crawler.py    # 京东司法拍卖采集器
│       ├── ali_crawler.py   # 阿里司法拍卖混合引擎
│       └── local_paper_crawler.py # 地方数字报公告专版智能扫描器
├── frontend/                 # Vite + React + Tailwind CSS 前端工程
│   ├── src/
│   │   ├── components/      # 看板组件 (AlertCenter, NoticeExplorer, RulesManager, etc.)
│   │   ├── api.js           # REST API 通信模块
│   │   └── App.jsx          # 主看板应用
│   └── dist/                # 编译打包好的生产静态资源
├── data/                    # 本地持久化数据存储目录 (SQLite WAL)
├── start.bat                # Windows 一键拉起脚本
├── Dockerfile               # 生产 Docker 容器镜像定义
└── docker-compose.yml       # Docker Compose 编排文件
```

---

## 🎯 53BK 报纸整合机制说明

针对用户提出的 `www.53bk.com` 报纸汇集网站：
1. **定位认知**：53BK 本身是数字报刊建站系统，站内不存储报纸全文，但聚合了全国 400+ 地区的官方电子报官网直链。
2. **落地实现**：本项目将 53BK 打造为系统的**“全国报刊雷达种子库 (PaperSeed)”**，已自动同步 340+ 份地方《日报》《晚报》的官网入口。
3. **精准降噪**：系统巡检时针对地方报刊只扫描其**第 3 版、第 4 版或“公告/声明专版”**，跳过冗余生活新闻，以极低资源消耗精准捕获地方涉案公告。
