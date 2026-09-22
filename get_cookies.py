"""
获取腾讯云登录后的 Cookies 与 CSRF Token，供后续抢购调用
"""
import json
import os
import sys
import time

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

def update_config_csrf(csrf_token: str):
    """更新 config.json 中的 csrf_token"""
    if not os.path.exists(CONFIG_FILE):
        return
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        cfg["csrf_token"] = csrf_token
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        print(f"✅ 已自动将 x-csrf-token 写入 {CONFIG_FILE}")
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

        # 监听网络请求，自动抓取 x-csrf-token 请求头
        def on_request(request):
            nonlocal csrf_token_captured
            token = request.headers.get("x-csrf-token")
            if token and not csrf_token_captured:
                csrf_token_captured = token
                print(f"🎯 成功自动捕获到 x-csrf-token: {csrf_token_captured}")

        page.on("request", on_request)

        login_url = "https://cloud.tencent.com/login?s_url=https%3A%2F%2Fcloud.tencent.com%2Fact%2Fpro%2Fdouble12-2025"
        print(f"👉 正在打开腾讯云登录页面: {login_url}")
        page.goto(login_url)

        print("\n" + "=" * 60)
        print("📌 请在弹出的浏览器窗口中使用【微信】或【腾讯云App】扫码登录！")
        print("💡 提示：")
        print("   1. 手机扫码并点击【确认登录】后，脚本会自动检测跳转并保存凭据。")
        print("   2. 若网页已登录完成，你也可以直接在当前控制台按【回车键 (Enter)】手动触发保存。")
        print("=" * 60 + "\n")

        logged_in = False
        start_time = time.time()
        timeout_seconds = 600  # 10分钟等待超时

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

                # 方式 2: 检查页面 URL 与真实登录态 Cookie
                cur_url = page.url
                cookies = context.cookies()
                cookie_names = {c.get("name") for c in cookies}

                # 只有真正的用户鉴权 Cookie（排查掉游客追踪用的 qcloud_uid / qcmainCSRFToken / login_intent_id）
                has_real_auth = any(k in cookie_names for k in ["uin", "skey", "ownerUin", "subUin", "pt4_token", "p_skey", "main_uin"])
                # 页面已经跳转离开登录页，且已在 cloud.tencent.com 站内
                left_login = ("login" not in cur_url) and ("cloud.tencent.com" in cur_url)

                if has_real_auth or (left_login and len(cookie_names) > 15):
                    print(f"🎉 自动检测到登录成功！(已离开登录页: {cur_url})")
                    logged_in = True
                    break
            except Exception:
                pass
            time.sleep(1)

        if not logged_in:
            print("❌ 等待登录超时（10分钟）或未完成登录，已退出。")
            browser.close()
            return

        print("⏳ 正在提取登录凭据与安全 Token，请稍候...")
        # 等待页面加载完成，促发接口请求以便捕获 csrf-token
        time.sleep(3)

        cookies = context.cookies()
        # 如果未在请求头抓到 x-csrf-token，尝试从 cookies 中提取 qcmainCSRFToken
        if not csrf_token_captured:
            for c in cookies:
                if c.get("name") == "qcmainCSRFToken" and c.get("value"):
                    csrf_token_captured = c.get("value")
                    print(f"💡 从 Cookie (qcmainCSRFToken) 提取到 CSRF Token: {csrf_token_captured}")
                    break

        # 保存 Cookies
        with open(COOKIES_FILE, "w", encoding="utf-8") as f:
            json.dump(cookies, f, ensure_ascii=False, indent=2)
        print(f"✅ Cookies 已保存至: {COOKIES_FILE} (共 {len(cookies)} 项)")

        # 保存 CSRF Token
        if csrf_token_captured:
            update_config_csrf(csrf_token_captured)
        else:
            print("💡 未自动捕获到 x-csrf-token，如抢购提示鉴权失败，可按 F12 在 Network 标头中确认。")

        print("\n✨ 凭据已成功保存！浏览器将在 2 秒后自动关闭。")
        time.sleep(2)
        browser.close()

if __name__ == "__main__":
    get_cookies()
