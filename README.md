# 腾讯云服务器秒杀工具

使用 Python 编写的自动化抢购脚本，支持并发抢购腾讯云轻量应用服务器。

![Tencent Cloud](image.png)

## 功能特点

- **快速部署与免下载**：自动适配系统自带 Microsoft Edge / Google Chrome，免去在受限网络下额外下载百兆浏览器的麻烦。
- **自动获取 Cookie 与 Token**：使用 Playwright 扫码登录，自动嗅探提取 `x-csrf-token` 并保存至 `cookies.json` 与 `config.json`。
- **多地域并发抢购**：支持华北（广州）、华东（上海）、华南（北京）等多地域并发冲刺。
- **精准时间校准**：自动读取腾讯云服务器 Date 时间，计算网络往返与本地时钟偏差。
- **自适应倒计时**：远期长周期休眠防封 IP，近秒级高精度忙等冲刺。
- **独立配置文件**：抢购时间、目标地域、商品 ID 等抽离在 `config.json`，无需反复修改代码。
- **Windows 一键运行**：提供 `.bat` 启动脚本，双击即用。

---

## 快速使用说明（推荐 Windows 用户）

### 第一步：获取登录凭据（扫码登录）
双击运行：
👉 **`1_获取登录Cookie.bat`**

1. 程序会自动启动浏览器并跳转到腾讯云登录页。
2. 使用微信或腾讯云 App 扫码登录。
3. 登录成功后，脚本会自动保存 `cookies.json`，并尝试自动抓取 `x-csrf-token` 保存到 `config.json`。
4. 看到提示成功后，浏览器会自动关闭。

---

### 第二步：配置秒杀参数
用记事本或编辑器打开 **`config.json`**：

```json
{
  "seckill_time": "2026-09-22 15:00:00",
  "region_ids": [1, 4, 8],
  "csrf_token": "...",
  "activity_id": 162634773874417,
  "check_act_id": 1784747698901873,
  "buy_act_id": 1897632168296710,
  "bundle_type": "bundle_budget_mc_lg4_01",
  "business_id": 22755,
  "image_id": "lhbp-eqora508",
  "blueprint_id": "LINUX_UNIX",
  "time_span_unit": "12m"
}
```

- **`seckill_time`**：秒杀开始时间（格式：`YYYY-MM-DD HH:MM:SS`）。
- **`region_ids`**：需要抢购的地域代码（`1`=华北/广州，`4`=华东/上海，`8`=华南/北京）。
- **`csrf_token`**：如果第一步已自动嗅探到则无需改动；若为空或抢购提示鉴权错误，可在浏览器 F12 网络请求的 Request Headers 中找到 `x-csrf-token` 并填入此处。

---

### 第三步：启动秒杀
双击运行：
👉 **`2_启动秒杀抢购.bat`**

脚本将：
1. 校验凭据与配置。
2. 校准腾讯云服务器时间并计算时钟差。
3. 检查当前目标服务器的库存与购买权限。
4. 智能倒计时，到点并发秒杀下单！

---

## 命令行运行方式

如果你习惯使用命令行终端：

```powershell
# 激活虚拟环境
.venv\Scripts\activate

# 1. 扫码获取 Cookie 与 Token
python get_cookies.py

# 2. 启动秒杀
python snap_up_server.py
```

---

## 文件结构说明

```
tencentyun-snake-up/
├── 1_获取登录Cookie.bat    # Windows 一键扫码登录脚本
├── 2_启动秒杀抢购.bat      # Windows 一键秒杀主程序
├── config.json             # 抢购参数配置文件
├── get_cookies.py          # 登录与 Cookie/Token 提取核心代码
├── snap_up_server.py       # 秒杀并发与倒计时核心代码
├── requirements.txt        # 依赖库清单
├── .venv/                  # 独立 Python 运行环境
├── cookies.json            # 登录成功后生成的凭据文件（忽略提交）
├── image.png               # 说明图片
└── README.md               # 项目文档
```

---

## 免责声明

本项目仅供个人学习交流使用，请勿用于商业用途。使用本工具产生的任何后果由使用者自行承担。
