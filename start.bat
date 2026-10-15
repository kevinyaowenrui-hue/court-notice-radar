@echo off
chcp 65001 >nul
title 司法案件公示与法拍监控雷达 (CourtNoticeRadar) - 启动中

echo ========================================================
echo  司法案件公示与法拍监控雷达 (CourtNoticeRadar)
echo  数据源: 阿里法拍 / 京东拍卖 / 《人民法院报》 / 53BK地方报纸
echo  访问地址: http://127.0.0.1:5220
echo ========================================================
echo.

cd /d "%~dp0"

REM 检查是否有前端编译产物，若无则自动编译
if not exist "frontend\dist\index.html" (
    echo [1/3] 正在构建现代化前端界面...
    cd frontend
    call npm run build
    cd ..
)

echo [2/3] 正在启动后台调度与 Web 服务...
set SERVER_PORT=5220
python -m backend.app

pause
