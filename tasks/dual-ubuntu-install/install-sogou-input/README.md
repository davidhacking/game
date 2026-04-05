# 安装搜狗输入法 - Ubuntu 22.04

## 环境
- Ubuntu 22.04 LTS (jammy), x86_64
- 当前使用 ibus 输入框架

## 方案
搜狗输入法依赖 fcitx 框架，需要：
1. 安装 fcitx 框架及相关依赖
2. 下载搜狗输入法 deb 包
3. 安装搜狗输入法
4. 配置 fcitx 为默认输入法框架
5. 重启生效
6. 重启后启用搜狗拼音并配置为活跃输入法

## 使用

### 第一步：安装（重启前）
```bash
bash install_sogou.sh
```
安装完成后需要**注销或重启**系统。

### 第二步：重启后配置
```bash
bash post_reboot_setup.sh
```
重启后运行此脚本，会自动启用搜狗拼音输入法。

## 切换输入法
- **Ctrl+Space**：切换中/英文输入法
- 右上角键盘图标也可点击切换

---

## 踩坑记录

### 问题：安装后 Ctrl+Space 无法切换搜狗输入法

**现象**：安装重启后，Ctrl+Space 无响应，搜狗无法唤起。

**根本原因（三个问题叠加）**：
1. `~/.config/fcitx/config` 里 `TriggerKey=CTRL_SPACE` 被注释掉（`#` 开头）
2. `~/.config/fcitx/profile` 里 `sogoupinyin:False`，搜狗在 fcitx 中被禁用
3. ibus 与 fcitx 同时运行，ibus 的 trigger 热键列表含 `Control+space`，抢先拦截按键

**修复步骤**：
```bash
# 1. 从 ibus 移除 Ctrl+Space，停止 ibus
gsettings set org.freedesktop.ibus.general.hotkey trigger "['Zenkaku_Hankaku', 'Alt+Kanji', 'Alt+grave', 'Hangul', 'Alt+Release+Alt_R']"
pkill ibus-daemon

# 2. 启用搜狗
sed -i 's/sogoupinyin:False/sogoupinyin:True/' ~/.config/fcitx/profile

# 3. 重启 fcitx 后设置 TriggerKey
# 注意：fcitx 启动时会重置 config，必须启动后再改再 reload
pkill fcitx; /usr/bin/fcitx -d &
sleep 2
sed -i 's/^#TriggerKey=CTRL_SPACE/TriggerKey=CTRL_SPACE/' ~/.config/fcitx/config
fcitx-remote -r
```

**持久化（防止重启后失效）**：
在 `~/.xprofile` 末尾添加：
```bash
(sleep 3 && sed -i 's/^#TriggerKey=CTRL_SPACE/TriggerKey=CTRL_SPACE/' ~/.config/fcitx/config && fcitx-remote -r) &
```
同时创建 `~/.config/autostart/fix-fcitx-triggerkey.desktop`：
```ini
[Desktop Entry]
Name=Fix Fcitx TriggerKey
Exec=bash -c "sleep 4 && sed -i 's/^#TriggerKey=CTRL_SPACE/TriggerKey=CTRL_SPACE/' ~/.config/fcitx/config && fcitx-remote -r"
Terminal=false
Type=Application
NoDisplay=true
X-GNOME-Autostart-Delay=4
```

**诊断工具**：
```bash
fcitx-diagnose                                              # 全面诊断
fcitx-remote -t                                             # 测试切换是否工作
gsettings get org.freedesktop.ibus.general.hotkey trigger   # 查看 ibus 是否抢占快捷键
grep "sogoupinyin" ~/.config/fcitx/profile                  # 确认搜狗是否启用
grep -v "^#" ~/.config/fcitx/config | grep -v "^$"          # 查看 fcitx 生效配置
```

---

### 问题：搜狗 CDN 直链 403 Forbidden

**现象**：所有脚本内预置的下载地址（`ime-sec.gtimg.com`）均返回 403，包括从官网页面抓取的最新链接，加 Referer/User-Agent 也无效。

**原因**：搜狗 CDN 使用了带时效性 token 的签名链接，直接访问静态路径会被拒绝，必须通过浏览器页面触发下载。

**解决方案（手动下载）**：
1. 在 Ubuntu2 **桌面浏览器**中打开：https://shurufa.sogou.com/linux
2. 点击「立即下载」→ 选 x86_64 版本
3. 下载完成后，在终端执行：
```bash
cp ~/Downloads/sogoupinyin_*.deb /tmp/sogoupinyin.deb
bash ~/MF/github/game/tasks/dual-ubuntu-install/install-sogou-input/install_sogou.sh
```
脚本会检测到 `/tmp/sogoupinyin.deb` 已存在并跳过下载，直接安装。
