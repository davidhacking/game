# FutuOpenD 安装任务

## 任务概述
在 Ubuntu 系统上下载并安装富途 OpenD 行情服务（FutuOpenD）。

## 结果（已完成）

**FutuOpenD 已经安装完毕**（由用户于 2026-03-25 提前完成）。

### 安装位置
```
/home/david/Futu_OpenD_10.2.6208_Ubuntu18.04/
├── README.txt
├── Futu_OpenD_10.2.6208_Ubuntu18.04/       ← 命令行版本
│   ├── FutuOpenD                            ← 主可执行文件 (30MB, ELF 64-bit)
│   ├── FTUpdate
│   ├── FTWebSocket
│   ├── AppData.dat
│   ├── FutuOpenD.xml
│   └── lib*.so (各种动态库)
└── Futu_OpenD-GUI_10.2.6208_Ubuntu18.04/   ← GUI 版本
```

安装包：`/home/david/Futu_OpenD_10.2.6208_Ubuntu18.04.tar.gz`（406MB）

### 版本信息
- **版本**：10.2.6208（比用户指定的 8.6.4608 更新）
- **平台**：Ubuntu 18.04（兼容当前系统）
- **类型**：ELF 64-bit x86-64 可执行文件

### 启动命令
```bash
# 命令行版本（推荐服务器使用）
cd /home/david/Futu_OpenD_10.2.6208_Ubuntu18.04/Futu_OpenD_10.2.6208_Ubuntu18.04
./FutuOpenD -login_account=账号 -login_pwd=交易密码 -lang=chs -api_port=11111

# GUI 版本（需要桌面环境，Ubuntu 18.04+）
cd /home/david/Futu_OpenD_10.2.6208_Ubuntu18.04/Futu_OpenD-GUI_10.2.6208_Ubuntu18.04
./FutuOpenD
```

---

## 下载方法（经验记录）

### 官方动态下载 API
富途提供官方 API 获取最新版本下载链接：
```bash
# 获取 Ubuntu 版本的最新下载链接（会重定向到实际 CDN 地址）
wget --spider -S "https://www.futunn.com/download/fetch-lasted-link?name=opend-ubuntu" 2>&1 | grep Location
# 输出示例：Location: https://softwaredownload.futunn.com/Futu_OpenD_10.2.6208_Ubuntu18.04.tar.gz

# 其他平台
# opend-windows: Windows 版
# opend-macos: macOS 版
# opend-centos: CentOS 版
```

### 直接下载
```bash
# 方式1：通过动态 API（自动获取最新版）
wget -O /home/david/Futu_OpenD_Ubuntu.tar.gz \
  "https://www.futunn.com/download/fetch-lasted-link?name=opend-ubuntu"

# 方式2：直接 CDN 链接（版本号可能变化）
wget "https://softwaredownload.futunn.com/Futu_OpenD_10.2.6208_Ubuntu18.04.tar.gz"
```

### 解压安装
```bash
cd /home/david
tar -zxvf Futu_OpenD_10.2.6208_Ubuntu18.04.tar.gz
# 解压后目录：/home/david/Futu_OpenD_10.2.6208_Ubuntu18.04/
```

---

## 注意事项
- Linux **命令行版**支持 CentOS 7+ 或 Ubuntu（任意版本）
- Linux **GUI 版**支持 Ubuntu 18.04 或更新版本
- 首次登录需要手机验证码验证
- 需要富途/Moomoo 账号才能连接行情

## 踩坑记录

### curl 被搜狗输入法污染
系统 curl 被 `/opt/sogoupinyin/files/lib/libcurl.so.4` 覆盖，导致运行报错：
```
curl: /opt/sogoupinyin/files/lib/libcurl.so.4: no version information available
```
**解决方案**：改用 `wget` 替代 curl 进行下载。

### 官方页面是 Vue SPA
`https://openapi.futunn.com/futu-api-doc/en/quick/opend-base.html` 是前端渲染页面，
直接 wget 无法获取下载链接内容。  
**解决方案**：下载并解析 JS bundle 文件（如 `34.3b229f6f.js`），从中提取到动态 API 地址。
