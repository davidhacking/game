#!/usr/bin/env python3
"""
同花顺交易命令脚本（运行在 Windows 内）
通过 easytrader 操作同花顺 GUI，结果以 JSON 输出到 stdout。

V2: 在连接后主动检测并处理验证码窗口，避免 ElementNotVisible
"""

import sys
import json
import argparse
import traceback
import time
import re
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

XIADAN_PATH = r"C:\同花顺软件\同花顺\xiadan.exe"


def _handle_captcha(user, max_retries=5):
    """
    主动检测并处理验证码窗口

    在执行任何业务操作前调用，确保验证码已处理完毕。
    """
    from easytrader.utils.captcha import captcha_recognize

    app = user.app
    main = app.top_window()

    # 先检查是否有验证码窗口
    try:
        has_captcha = main.window(class_name="Static", title_re="验证码").exists(timeout=3)
    except Exception:
        has_captcha = False

    if not has_captcha:
        logger.info("无验证码窗口")
        return True

    logger.info("检测到验证码窗口，开始自动处理")

    for attempt in range(1, max_retries + 1):
        logger.info("第 %d 次验证码识别尝试" % attempt)
        try:
            # 截取验证码图片
            img = main.window(control_id=0x965, class_name="Static").capture_as_image()
            file_path = r"C:\Windows\Temp\captcha_%d.png" % attempt
            img.save(file_path)
            logger.info("验证码图片: %s" % file_path)

            # OCR 识别
            raw = captcha_recognize(file_path).strip()
            digits = re.sub(r'\D', '', raw)
            logger.info("OCR 原始: %s -> 数字: %s" % (raw, digits))

            if len(digits) < 4:
                logger.warning("识别不足4位 (%s)，刷新验证码重试" % digits)
                # 点击验证码图片刷新
                try:
                    main.window(control_id=0x965, class_name="Static").click_input()
                    time.sleep(0.5)
                except Exception:
                    pass
                continue

            code = digits[:4]
            logger.info("使用验证码: %s" % code)

            # 点击输入框
            edit = main.window(control_id=0x964, class_name="Edit")
            edit.click_input()
            time.sleep(0.2)

            # 清空并输入
            edit.set_edit_text("")
            time.sleep(0.1)
            edit.type_keys(code)
            time.sleep(0.2)

            # 点确认
            try:
                btn = main.window(control_id=0x1, class_name="Button")
                btn.click()
                logger.info("确认按钮已点击")
            except Exception:
                import pywinauto.keyboard
                pywinauto.keyboard.send_keys("{ENTER}")
                logger.info("已发送回车键")

            time.sleep(1.0)

            # 检查验证码窗口是否消失
            try:
                still = main.window(class_name="Static", title_re="验证码").exists(timeout=1)
                if not still:
                    logger.info("验证码验证成功")
                    return True
                else:
                    logger.warning("验证码窗口仍在，识别可能错误")
            except Exception:
                logger.info("验证码窗口已消失（成功）")
                return True

        except Exception as e:
            logger.warning("第 %d 次尝试异常: %s" % (attempt, e))

    logger.error("验证码处理失败（%d次尝试）" % max_retries)
    return False


def get_user():
    """连接同花顺客户端，处理验证码，确保窗口可用"""
    import easytrader
    user = easytrader.use('ths')
    user.connect(XIADAN_PATH)
    _ensure_window_visible(user)

    # 切换到资金股票页面（可能触发验证码）
    try:
        user._switch_left_menus(["查询[F4]", "资金股票"])
        time.sleep(0.5)
    except Exception:
        pass

    # 主动处理验证码
    if not _handle_captcha(user):
        raise RuntimeError("验证码处理失败，请手动在 Windows 上输入验证码")

    return user


def _ensure_window_visible(user):
    """确保同花顺主窗口可见"""
    try:
        main_win = user.app.top_window()
        if main_win.is_minimized():
            main_win.restore()
            time.sleep(0.5)
        main_win.set_focus()
        time.sleep(0.3)
    except Exception as e:
        try:
            import ctypes
            hwnd = user.app.top_window().handle
            ctypes.windll.user32.ShowWindow(hwnd, 9)
            time.sleep(0.3)
            ctypes.windll.user32.SetForegroundWindow(hwnd)
            time.sleep(0.3)
        except Exception:
            pass


def output_json(data):
    print(json.dumps(data, ensure_ascii=False))

def output_error(msg):
    print(json.dumps({"error": str(msg)}, ensure_ascii=False))


def cmd_balance(args):
    user = get_user()
    result = user.balance
    output_json(result)

def cmd_position(args):
    user = get_user()
    result = user.position
    output_json(result)

def cmd_today_trades(args):
    user = get_user()
    result = user.today_trades
    output_json(result)

def cmd_today_entrusts(args):
    user = get_user()
    result = user.today_entrusts
    output_json(result)

def cmd_buy(args):
    user = get_user()
    result = user.buy(args.code, price=args.price, amount=args.qty)
    output_json(result)

def cmd_sell(args):
    user = get_user()
    result = user.sell(args.code, price=args.price, amount=args.qty)
    output_json(result)


def main():
    parser = argparse.ArgumentParser(description="同花顺交易命令")
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    subparsers.add_parser("balance", help="查询资金余额")
    subparsers.add_parser("position", help="查询持仓信息")
    subparsers.add_parser("today_trades", help="查询今日成交")
    subparsers.add_parser("today_entrusts", help="查询今日委托")

    buy_parser = subparsers.add_parser("buy", help="买入股票")
    buy_parser.add_argument("--code", required=True)
    buy_parser.add_argument("--price", type=float, required=True)
    buy_parser.add_argument("--qty", type=int, required=True)

    sell_parser = subparsers.add_parser("sell", help="卖出股票")
    sell_parser.add_argument("--code", required=True)
    sell_parser.add_argument("--price", type=float, required=True)
    sell_parser.add_argument("--qty", type=int, required=True)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "balance": cmd_balance,
        "position": cmd_position,
        "today_trades": cmd_today_trades,
        "today_entrusts": cmd_today_entrusts,
        "buy": cmd_buy,
        "sell": cmd_sell,
    }

    try:
        commands[args.command](args)
    except Exception as e:
        output_error("%s: %s\n%s" % (type(e).__name__, e, traceback.format_exc()))
        sys.exit(1)


if __name__ == "__main__":
    main()
