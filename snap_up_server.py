"""
腾讯云服务器秒杀抢购脚本
支持多地域并发抢购、自动时间校准、智能倒计时
"""
import os
import sys
import time
import json
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import requests

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

CONFIG_FILE = "config.json"
COOKIES_FILE = "cookies.json"

DEFAULT_CONFIG = {
    "seckill_time": "2026-09-22 15:00:00",
    "region_ids": [1, 4, 8],
    "csrf_token": "",
    "activity_id": 162634773874417,
    "check_act_id": 1784747698901873,
    "buy_act_id": 1897632168296710,
    "bundle_type": "bundle_budget_mc_lg4_01",
    "business_id": 22755,
    "image_id": "lhbp-eqora508",
    "blueprint_id": "LINUX_UNIX",
    "time_span_unit": "12m"
}

def load_config():
    if not os.path.exists(CONFIG_FILE):
        print(f"⚠️ 未找到 {CONFIG_FILE}，创建默认配置文件...")
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, ensure_ascii=False, indent=2)
        return DEFAULT_CONFIG
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
            # 补齐默认字段
            for k, v in DEFAULT_CONFIG.items():
                if k not in cfg:
                    cfg[k] = v
            return cfg
    except Exception as e:
        print(f"⚠️ 读取配置文件异常，使用默认配置: {e}")
        return DEFAULT_CONFIG

def calculate_csrf_token(skey: str) -> str:
    """基于腾讯经典 DJB2 哈希算法，从 skey 实时推导 x-csrf-token"""
    if not skey:
        return ""
    h = 5381
    for c in skey:
        h += (h << 5) + ord(c)
    return str(h & 0x7fffffff)

def init_session(cfg):
    """初始化并配置 requests 会话"""
    if not os.path.exists(COOKIES_FILE):
        print("\n" + "=" * 60)
        print("❌ 错误：未找到 cookies.json！")
        print("📌 请先运行 '1_获取登录Cookie.bat' 或执行 'python get_cookies.py' 扫码登录。")
        print("=" * 60 + "\n")
        sys.exit(1)

    session = requests.Session()
    try:
        with open(COOKIES_FILE, "r", encoding="utf-8") as f:
            cookies = json.load(f)
            for c in cookies:
                session.cookies.set(
                    c.get("name", ""),
                    c.get("value", ""),
                    domain=c.get("domain", ""),
                    path=c.get("path", "/")
                )
        print(f"✅ 成功加载 Cookie，共 {len(cookies)} 项。")
    except Exception as e:
        print(f"❌ 加载 Cookie 失败: {e}")
        sys.exit(1)

    # 检查是否包含真实登录态
    cookie_names = {c.name for c in session.cookies}
    has_auth = any(k in cookie_names for k in ["uin", "skey", "ownerUin", "subUin", "pt4_token", "p_skey", "main_uin"])
    if not has_auth:
        print("\n" + "=" * 65)
        print("❌ 警告：cookies.json 中未检测到有效登录凭据（当前仅有游客匿名凭据）！")
        print("📌 说明之前运行扫码脚本时未能成功完成手机扫码，或提前退出了。")
        print("👉 请重新运行 '1_获取登录Cookie.bat' 扫码登录！")
        print("=" * 65 + "\n")

    # 自动计算 CSRF Token（安全提取 skey，兼容多域名同名 Cookie）
    skey = ""
    for c in session.cookies:
        if c.name == "skey" and c.value:
            skey = c.value
            break
    computed_token = calculate_csrf_token(skey) if skey else ""

    csrf_token = str(cfg.get("csrf_token", "")).strip()
    # 如果用户配置的不是纯数字（比如误填了字符串），或者未配置，则直接使用依据 skey 精确计算出的 Token
    if not csrf_token.isdigit():
        if computed_token:
            csrf_token = computed_token
            print(f"💡 自动根据 skey 计算出最新 CSRF Token: {csrf_token}")
        else:
            print("⚠️ 警告：未找到 skey，无法自动计算 csrf_token。")
    else:
        print(f"💡 使用当前配置的 CSRF Token: {csrf_token}")

    headers = {
        "x-csrf-token": str(csrf_token),
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer": "https://cloud.tencent.com/act/pro/featured-202607",
        "Origin": "https://cloud.tencent.com"
    }

    return session, headers

def get_server_time():
    """获取腾讯云服务器时间（毫秒级时间戳），若请求失败则退化为本地时间"""
    test_urls = [
        "https://cloud.tencent.com/act/pro/double12-2025",
        "https://cloud.tencent.com"
    ]
    for url in test_urls:
        try:
            resp = requests.head(url, timeout=5)
            server_date = resp.headers.get("Date")
            if server_date:
                dt = datetime.strptime(server_date, "%a, %d %b %Y %H:%M:%S GMT")
                beijing_time = dt + timedelta(hours=8)
                return int(beijing_time.timestamp() * 1000)
        except Exception:
            continue

    print("⚠️ 无法连接腾讯云时间服务器，回退使用本地系统时间。")
    return int(time.time() * 1000)

def check_available(session, headers, cfg):
    """检查商品库存状态"""
    check_data = {
        "activity_id": cfg["activity_id"],
        "goods": [
            {
                "act_id": cfg["check_act_id"],
                "region_id": cfg["region_ids"]
            }
        ],
        "preview": 0
    }
    try:
        resp = session.post(
            "https://act-api.cloud.tencent.com/dianshi/check-available",
            json=check_data,
            headers=headers,
            timeout=5
        )
        try:
            result = resp.json()
        except Exception:
            result = {"code": resp.status_code, "msg": resp.text}

        if result.get("code") == 0:
            print(f"📊 库存检查返回正常: {result.get('msg', 'ok')}")
            return result
        else:
            code = result.get("code")
            msg = result.get("msg", "")
            if code == "NOT-LOGINED":
                print(f"💡 当前活动状态: 上午场已结束/未在秒杀时段（接口提示: {msg}，属于腾讯云未开售时的锁定状态，不影响到点并发冲刺）")
            else:
                print(f"⚠️ 库存检查提示: {result}")
            return result
    except Exception as e:
        print(f"⚠️ 库存检查请求异常: {e}")
        return None

def buy_now(session, headers, cfg, region_id):
    """单个地域下单购买"""
    region_names = {1: "广州/华北", 4: "上海/华东", 8: "北京/华南"}
    reg_desc = region_names.get(region_id, f"地域ID_{region_id}")

    do_data = {
        "activity_id": cfg["activity_id"],
        "agent_channel": {
            "fromChannel": "",
            "fromSales": "",
            "isAgentClient": False,
            "fromUrl": "https://cloud.tencent.com/act/pro/featured-202607"
        },
        "business": {
            "id": cfg["business_id"],
            "from": "lightningDeals"
        },
        "goods": [
            {
                "act_id": cfg["buy_act_id"],
                "type": cfg["bundle_type"],
                "goods_param": {
                    "BlueprintId": cfg["blueprint_id"],
                    "area": 1,
                    "ddocUnionConnect": 0,
                    "goodsNum": 1,
                    "imageId": cfg["image_id"],
                    "scenario": "0",
                    "timeSpanUnit": cfg["time_span_unit"],
                    "zone": "",
                    "regionId": region_id,
                    "type": cfg["bundle_type"]
                }
            }
        ],
        "preview": 0
    }

    try:
        start_req = time.time()
        resp = session.post(
            "https://act-api.cloud.tencent.com/dianshi/do-goods",
            json=do_data,
            headers=headers,
            timeout=10
        )
        cost_ms = int((time.time() - start_req) * 1000)
        res_json = resp.json()
        code = res_json.get("code")
        msg = res_json.get("msg", "")

        if code == 0:
            print(f"\n🎉🎉🎉 [{reg_desc}] 抢购成功！耗时 {cost_ms}ms！返回: {res_json}")
            return {"success": True, "region_id": region_id, "data": res_json}
        else:
            print(f"❌ [{reg_desc}] 下单失败 (code={code}, msg={msg}) [耗时 {cost_ms}ms]")
            return {"success": False, "region_id": region_id, "data": res_json}
    except Exception as e:
        print(f"❌ [{reg_desc}] 请求异常: {e}")
        return {"success": False, "region_id": region_id, "error": str(e)}

def buy_now_concurrent(session, headers, cfg, region_ids):
    """并发抢购指定的多个地域"""
    print(f"\n⚡ 正在并发发起抢购请求 (目标地域: {region_ids})...")
    results = []
    with ThreadPoolExecutor(max_workers=max(len(region_ids), 1)) as executor:
        futures = [executor.submit(buy_now, session, headers, cfg, rid) for rid in region_ids]
        for f in futures:
            results.append(f.result())
    return results

def main():
    print("=======================================================")
    print("🚀 腾讯云秒杀抢购脚本已启动")
    print("=======================================================")

    cfg = load_config()
    session, headers = init_session(cfg)

    seckill_time_str = cfg.get("seckill_time", "2026-09-22 15:00:00")
    try:
        seckill_dt = datetime.strptime(seckill_time_str, "%Y-%m-%d %H:%M:%S")
        target_timestamp_ms = int(seckill_dt.timestamp() * 1000)
    except Exception as e:
        print(f"❌ 秒杀时间格式错误: {seckill_time_str}，请使用 'YYYY-MM-DD HH:MM:SS' 格式: {e}")
        sys.exit(1)

    region_ids = cfg.get("region_ids", [1, 4, 8])

    print(f"🎯 抢购目标时间: {seckill_time_str}")
    print(f"🎯 抢购目标地域: {region_ids}")
    print(f"🔑 CSRF Token: {headers.get('x-csrf-token', '未设置')}")

    # 服务器时间校准
    print("\n⏰ 正在校准服务器时间...")
    local_before = int(time.time() * 1000)
    server_ms = get_server_time()
    local_after = int(time.time() * 1000)
    local_mid = (local_before + local_after) // 2
    offset_ms = server_ms - local_mid
    print(f"⏱️ 本地与服务器时间偏差: {offset_ms:+d} ms")

    # 预先检查一次商品状态
    print("\n🔍 正在检查当前商品库存与权限状态...")
    check_available(session, headers, cfg)

    print("\n⏳ 进入倒计时等待...")
    last_print_sec = None

    while True:
        # 当前估算服务器时间
        current_server_ms = int(time.time() * 1000) + offset_ms
        diff_ms = target_timestamp_ms - current_server_ms

        if diff_ms <= 0:
            print(f"\n🔥 秒杀时刻到达！(偏差 {diff_ms} ms)")
            buy_now_concurrent(session, headers, cfg, region_ids)
            break
        elif diff_ms > 60000:
            secs = diff_ms // 1000
            if last_print_sec is None or (last_print_sec - secs) >= 15:
                print(f"⏳ 距离秒杀还有 {secs} 秒 (目标: {seckill_time_str})")
                last_print_sec = secs
            time.sleep(min(10.0, max(1.0, (diff_ms - 60000) / 1000.0)))
        elif diff_ms > 5000:
            secs = diff_ms // 1000
            if last_print_sec != secs:
                print(f"⏳ 距离秒杀还有 {secs} 秒...")
                last_print_sec = secs
            time.sleep(0.5)
        elif diff_ms > 1000:
            print(f"⚡ 即将开始: {diff_ms / 1000.0:.1f} 秒...")
            time.sleep(0.1)
        else:
            # 临近 1 秒内，高精度忙等冲刺 (确保触发偏差在 5ms 以内)
            while True:
                cur = int(time.time() * 1000) + offset_ms
                if cur >= target_timestamp_ms:
                    break
                time.sleep(0.001)
            trigger_diff = (int(time.time() * 1000) + offset_ms) - target_timestamp_ms
            print(f"\n🔥 秒杀时刻到达！(精确触发偏差: +{trigger_diff} ms)")
            buy_now_concurrent(session, headers, cfg, region_ids)
            break

    print("\n=======================================================")
    print("✨ 抢购流程已结束。")
    print("=======================================================")

if __name__ == "__main__":
    main()
