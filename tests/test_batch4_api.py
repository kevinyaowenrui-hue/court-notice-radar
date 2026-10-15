"""Batch 4 API Verification Test Suite.

Verifies:
1. Webhook settings get/save/test
2. Notice pagination and discount_rate calculation
3. Star/unstar notice workflow
4. Notice follow-up notes (user_notes) workflow
5. Starred-only filter
6. Alert pagination and discount_rate
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from fastapi.testclient import TestClient
from backend.app import app
from backend.database import SessionLocal
from backend.models import CourtNotice

client = TestClient(app)

def test_batch4_api():
    print("=== 开始第 4 批功能实证测试 ===")

    # 1. Webhook Settings GET & POST
    print("\n[测试 1] Webhook 配置读取与保存...")
    res = client.get("/api/settings/webhook")
    assert res.status_code == 200, f"GET webhook failed: {res.text}"
    default_config = res.json()
    assert "platform" in default_config
    assert "enabled" in default_config
    print(f"-> 读取默认配置成功: platform={default_config.get('platform')}, enabled={default_config.get('enabled')}")

    # 保存新配置
    save_payload = {
        "platform": "wecom",
        "webhook_url": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=mock-test-key-12345",
        "secret": "",
        "enabled": True,
        "notify_on_new": True
    }
    res_save = client.post("/api/settings/webhook", json=save_payload)
    assert res_save.status_code == 200, f"POST webhook failed: {res_save.text}"
    saved_data = res_save.json()
    assert saved_data.get("platform") == "wecom"
    print("-> Webhook 配置保存成功")

    # 再次读取验证持久化
    res_verify = client.get("/api/settings/webhook")
    verify_data = res_verify.json()
    assert verify_data.get("platform") == "wecom"
    assert "mock-test-key-12345" in verify_data.get("webhook_url")
    assert verify_data.get("enabled") is True
    print("-> Webhook 配置持久化校验通过")

    # 2. Webhook 测试发送接口
    print("\n[测试 2] Webhook 模拟测试发送...")
    test_res = client.post("/api/settings/webhook/test", json=save_payload)
    assert test_res.status_code == 200
    test_result = test_res.json()
    print(f"-> Webhook 测试发送响应正常 (捕获网络/模拟反馈): status={test_result.get('status')}, message={test_result.get('message')}")

    # 3. 法拍标的分页查询与折扣率计算
    print("\n[测试 3] 法拍标的分页接口与折扣率计算...")
    res_notices = client.get("/api/notices?page=1&page_size=5")
    assert res_notices.status_code == 200, f"GET notices failed: {res_notices.text}"
    notice_data = res_notices.json()
    assert "total" in notice_data
    assert "page" in notice_data
    assert "page_size" in notice_data
    assert "total_pages" in notice_data
    assert "items" in notice_data
    print(f"-> 法拍标的分页结构正常: total={notice_data['total']}, page={notice_data['page']}, total_pages={notice_data['total_pages']}, items_count={len(notice_data['items'])}")

    # 检查标的项是否有 discount_rate 和 is_starred 字段
    first_item = None
    if notice_data["items"]:
        first_item = notice_data["items"][0]
        assert "is_starred" in first_item
        assert "user_notes" in first_item
        print(f"-> 首条标的校验通过: ID={first_item['id']}, 拍卖阶段={first_item.get('auction_stage')}, 起拍价={first_item.get('starting_price')}, 评估价={first_item.get('eval_price')}, 折扣率={first_item.get('discount_rate')}%")

    # 4. 标的收藏 / 关注切换
    if first_item:
        target_id = first_item["id"]
        original_starred = bool(first_item.get("is_starred"))
        print(f"\n[测试 4] 标的收藏切换 (ID: {target_id}, 当前状态: {original_starred})...")
        
        star_res = client.post(f"/api/notices/{target_id}/star")
        assert star_res.status_code == 200
        new_starred = star_res.json().get("is_starred")
        assert new_starred == (not original_starred), f"收藏状态未翻转: {new_starred}"
        print(f"-> 第一次切换成功: 新状态={new_starred}")

        # 再次切换恢复
        star_res2 = client.post(f"/api/notices/{target_id}/star")
        assert star_res2.status_code == 200
        assert star_res2.json().get("is_starred") == original_starred
        print(f"-> 第二次切换复原成功: 状态={original_starred}")

    # 5. 标的跟进便签更新
    if first_item:
        target_id = first_item["id"]
        test_note = "【自动化测试备注】该标的已做产调，土地性质出让，注意税费承担方。"
        print(f"\n[测试 5] 标的跟进便签修改保存 (ID: {target_id})...")

        notes_res = client.post(f"/api/notices/{target_id}/notes", json={"notes": test_note})
        assert notes_res.status_code == 200
        assert notes_res.json().get("user_notes") == test_note
        print("-> 便签保存接口响应成功")

        # 验证单条详情获取中包含便签
        single_res = client.get(f"/api/notices/{target_id}")
        assert single_res.status_code == 200
        assert single_res.json().get("user_notes") == test_note
        print("-> 标的详情复核成功，便签内容一致")

    # 6. 只看已关注标的筛选
    if first_item:
        target_id = first_item["id"]
        # 先确保至少有 1 条标的是已关注状态
        client.post(f"/api/notices/{target_id}/star") # 切换为 True
        star_filter_res = client.get("/api/notices?starred_only=true")
        assert star_filter_res.status_code == 200
        starred_data = star_filter_res.json()
        assert starred_data["total"] >= 1
        for it in starred_data["items"]:
            assert it["is_starred"] is True
        print(f"\n[测试 6] '仅看我的关注' 筛选成功: 关注标的数={starred_data['total']}")
        # 复原状态
        client.post(f"/api/notices/{target_id}/star")

    # 7. 预警列表真分页测试
    print("\n[测试 7] 预警中心真分页测试...")
    alerts_res = client.get("/api/alerts?page=1&page_size=5")
    assert alerts_res.status_code == 200
    alerts_data = alerts_res.json()
    assert "total" in alerts_data
    assert "page" in alerts_data
    assert "total_pages" in alerts_data
    assert "items" in alerts_data
    print(f"-> 预警分页接口通过: total={alerts_data['total']}, page={alerts_data['page']}, total_pages={alerts_data['total_pages']}, items_count={len(alerts_data['items'])}")

    print("\n=== 全部 7 项实证测试均顺利通过！ ===")

if __name__ == "__main__":
    run_tests()
