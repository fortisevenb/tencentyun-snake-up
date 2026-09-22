"""
获取腾讯云登录后的 Cookies 与 CSRF Token，供后续抢购调用
"""
import json
import os
import sys
import time
import urllib.parse

if sys.platform == "win32":
    try:
        import msvcrt
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from playwright.sync_api import sync_playwright

CONFIG_FILE = "config.json"
COOKIES_FILE = "cookies.json"
TARGET_ACTIVITY_URL = "https://cloud.tencent.com/act/pro/featured-202607"

def calculate_csrf_token(skey: str) -> str:
    """腾讯云前端 DJB2 哈希算法计算 x-csrf-token"""
    if not skey:
        return ""
    h = 5381
    for c in skey:
        h += (h << 5) + ord(c)
    return str(h & 0x7fffffff)

def update_config_csrf(csrf_token: str):
    """更新 config.json 中的 csrf_token"""
    if not os.path.exists(CONFIG_FILE):
        return
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        cfg["csrf_token"] = str(csrf_token)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        print(f"✅ 已自动将 x-csrf-token ({csrf_token}) 写入 {CONFIG_FILE}")
    except Exception as e:
        print(f"⚠️ 更新 config.json 失败: {e}")

def launch_browser(p):
    """优先调用系统自带 Edge 或 Chrome 浏览器，免去额外下载 Chromium 的网络依赖"""
    for ch in ["msedge", "chrome"]:
        try:
            return p.chromium.launch(channel=ch, headless=False)
        except Exception:
            pass
    return p.chromium.launch(headless=False)

def get_cookies():
    csrf_token_captured = None

    with sync_playwright() as p:
        print("🌐 正在启动浏览器 (使用系统 Edge/Chrome)...")
        browser = launch_browser(p)
        context = browser.new_context()
        page = context.new_page()

        # 监听网络请求，自动抓取真实发出的 x-csrf-token 请求头
        def on_request(request):
            nonlocal csrf_token_captured
            token = request.headers.get("x-csrf-token")
            if token and not csrf_token_captured:
                csrf_token_captured = token
                print(f"🎯 成功从网络请求中捕获到 x-csrf-token: {csrf_token_captured}")

        page.on("request", on_request)

        # 设置登录成功后的回跳地址为当前真实的 2026 采购季秒杀活动页
        s_url_encoded = urllib.parse.quote(TARGET_ACTIVITY_URL, safe="")
        login_url = f"https://cloud.tencent.com/login?s_url={s_url_encoded}"
        print(f"👉 正在打开腾讯云登录页面: {login_url}")
        page.goto(login_url)

        print("\n" + "=" * 65)
        print("📌 请在弹出的浏览器窗口中使用【微信】或【腾讯云App】扫码登录！")
        print("💡 重要提示：")
        print("   1. 手机扫码确认后，请等待浏览器自动跳转到【2026 采购季秒杀活动页】！")
        print("   2. 页面右上角显示已登录（如头像/账号ID），说明云账号会话已完整置换。")
        print("   3. 脚本检测到离开登录页并进入活动页后会自动保存凭据；")
        print("      你也可以在看到登录成功后，在当前控制台按【回车键 (Enter)】手动触发保存。")
        print("=" * 65 + "\n")

        logged_in = False
        start_time = time.time()
        timeout_seconds = 600  # 10分钟等待超时
        last_url = ""

        while time.time() - start_time < timeout_seconds:
            try:
                # 方式 1: 检查控制台是否有用户按回车手动确认
                if sys.platform == "win32":
                    try:
                        if msvcrt.kbhit():
                            ch = msvcrt.getch()
                            if ch in (b'\r', b'\n', b' '):
                                print("⌨️ 检测到用户按键确认登录完成！")
                                logged_in = True
                                break
                    except Exception:
                        pass

                cur_url = page.url
                if cur_url != last_url:
                    last_url = cur_url

                # 判断当前页面是否还在登录/OAuth流程中
                is_on_login = any(k in cur_url.lower() for k in ["/login", "open.weixin.qq.com", "graph.qq.com"])

                cookies = context.cookies()
                cookie_names = {c.get("name") for c in cookies}

                # 检查是否存在基础认证凭据
                has_auth = "skey" in cookie_names or "uin" in cookie_names

                # 关键修复：必须彻底离开登录页，且已在 cloud.tencent.com 站内（如活动页或控制台）
                arrived_main_site = (not is_on_login) and ("cloud.tencent.com" in cur_url)

                if has_auth and arrived_main_site:
                    print(f"\n🎉 检测到已完成扫码并成功跳转至活动站内: {cur_url}")
                    print("⏳ 正在等待 3 秒以确保所有 Session 会话票据完整置换与写入...")
                    time.sleep(3)
                    logged_in = True
                    break

            except Exception:
                pass
            time.sleep(1)

        if not logged_in:
            print("❌ 等待登录超时（10分钟）或未完成登录，已退出。")
            browser.close()
            return

        print("\n⏳ 正在提取完整登录凭据与安全 Token，请稍候...")

        # 尝试等待页面网络稳定
        try:
            page.wait_for_load_state("domcontentloaded", timeout=5000)
        except Exception:
            pass

        cookies = context.cookies()
        cookie_map = {c.get("name"): c.get("value") for c in cookies}

        # 优先使用根据登录 skey 精确计算出的 DJB2 CSRF Token（与当前 session 严格对齐）
        final_csrf_token = ""
        if "skey" in cookie_map and cookie_map["skey"]:
            final_csrf_token = calculate_csrf_token(cookie_map["skey"])
            print(f"💡 根据登录会话 skey 自动计算出精准 CSRF Token: {final_csrf_token}")
        elif csrf_token_captured:
            final_csrf_token = csrf_token_captured
        elif "qcmainCSRFToken" in cookie_map:
            final_csrf_token = cookie_map["qcmainCSRFToken"]

        # 保存 Cookies
        with open(COOKIES_FILE, "w", encoding="utf-8") as f:
            json.dump(cookies, f, ensure_ascii=False, indent=2)
        print(f"✅ 完整 Cookies 已保存至: {COOKIES_FILE} (共 {len(cookies)} 项)")

        # 打印关键凭据排查信息（安全展示）
        uin = cookie_map.get("uin", "未找到")
        owner_uin = cookie_map.get("ownerUin", cookie_map.get("main_uin", "无独立主账号ID"))
        print(f"📋 账号识别信息: uin={uin}, ownerUin={owner_uin}")

        # 保存 CSRF Token
        if final_csrf_token:
            update_config_csrf(final_csrf_token)
        else:
            print("⚠️ 未能提取到 CSRF Token，若抢购提示鉴权错误请确认登录状态。")

        print("\n✨ 登录凭据获取并校验完成！浏览器将在 2 秒后自动关闭。")
        time.sleep(2)
        browser.close()

if __name__ == "__main__":
    get_cookies()
