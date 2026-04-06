#!/bin/bash
# 安装 stock_models 依赖脚本
# 跳过：atari-py（Linux编译问题）、pywinauto/comtypes（Windows-only）、easytrader（可能失败）

UV=/home/david/.local/bin/uv
PYTHON=/home/david/MF/github/game/stock_models/.venv/bin/python
LOGFILE=/home/david/MF/github/game/stock_models/install_log.txt

echo "======== 开始安装 $(date) ========" | tee $LOGFILE

# 跳过的包
SKIP_PKGS="atari-py pywinauto comtypes easytrader"

# 生成过滤后的 requirements
FILTERED_REQ=$(mktemp /tmp/requirements_filtered_XXXX.txt)
while IFS= read -r line; do
    pkg_name=$(echo "$line" | cut -d'=' -f1 | tr '[:upper:]' '[:lower:]')
    skip=false
    for skip_pkg in $SKIP_PKGS; do
        if [[ "$pkg_name" == "$skip_pkg" ]]; then
            skip=true
            break
        fi
    done
    if [ "$skip" = true ]; then
        echo "跳过: $line" | tee -a $LOGFILE
    else
        echo "$line" >> $FILTERED_REQ
    fi
done < /home/david/MF/github/game/stock_models/requirements.txt

echo "" | tee -a $LOGFILE
echo "开始安装过滤后的依赖..." | tee -a $LOGFILE
echo "过滤后的包数量: $(wc -l < $FILTERED_REQ)" | tee -a $LOGFILE
echo "" | tee -a $LOGFILE

# 一次性安装
$UV pip install -r $FILTERED_REQ --python $PYTHON 2>&1 | tee -a $LOGFILE
INSTALL_STATUS=$?

rm -f $FILTERED_REQ

echo "" | tee -a $LOGFILE
if [ $INSTALL_STATUS -eq 0 ]; then
    echo "======== 批量安装成功 ========" | tee -a $LOGFILE
else
    echo "======== 批量安装失败(exit $INSTALL_STATUS)，尝试逐个安装核心依赖 ========" | tee -a $LOGFILE

    CORE_PKGS=(
        "torch==2.5.1"
        "stable-baselines3==1.2.0"
        "gym==0.26.2"
        "numpy==1.26.4"
        "pandas==2.2.3"
        "tushare==1.4.13"
        "stockstats==0.6.2"
        "matplotlib==3.9.2"
        "scikit-learn==1.5.2"
        "futu-api==8.7.4708"
        "tensorboard==2.18.0"
        "requests==2.32.3"
        "opencv-python==4.10.0.84"
        "scipy==1.14.1"
        "Flask==3.1.0"
        "pyfolio==0.9.2"
        "empyrical==0.5.5"
        "pandas-datareader==0.10.0"
        "seaborn==0.13.2"
        "beautifulsoup4==4.12.3"
        "lxml==5.3.0"
    )

    for pkg in "${CORE_PKGS[@]}"; do
        echo "--- 安装 $pkg ---" | tee -a $LOGFILE
        $UV pip install "$pkg" --python $PYTHON 2>&1 | tee -a $LOGFILE
        if [ $? -eq 0 ]; then
            echo "✓ $pkg 安装成功" | tee -a $LOGFILE
        else
            echo "✗ $pkg 安装失败" | tee -a $LOGFILE
        fi
    done
fi

echo "" | tee -a $LOGFILE
echo "======== 验证核心包 ========" | tee -a $LOGFILE
$PYTHON -c "
import sys
packages = ['torch', 'stable_baselines3', 'gym', 'numpy', 'pandas', 'tushare', 'matplotlib', 'sklearn', 'tensorboard']
ok = []
fail = []
for p in packages:
    try:
        mod = __import__(p)
        ver = getattr(mod, '__version__', 'unknown')
        ok.append(f'  ✓ {p} {ver}')
    except ImportError as e:
        fail.append(f'  ✗ {p}: {e}')

print('成功:')
for x in ok: print(x)
print('失败:')
for x in fail: print(x)
" 2>&1 | tee -a $LOGFILE

echo "" | tee -a $LOGFILE
echo "======== 安装完成 $(date) ========" | tee -a $LOGFILE
