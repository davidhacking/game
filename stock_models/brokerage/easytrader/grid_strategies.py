# -*- coding: utf-8 -*-
import abc
import io
import tempfile
from io import StringIO
from typing import TYPE_CHECKING, Dict, List, Optional

import pandas as pd
import pywinauto.keyboard
import pywinauto
import pywinauto.clipboard

from easytrader.log import logger
from easytrader.utils.captcha import captcha_recognize
from easytrader.utils.win_gui import SetForegroundWindow, ShowWindow, win32defines

if TYPE_CHECKING:
    # pylint: disable=unused-import
    from easytrader import clienttrader


class IGridStrategy(abc.ABC):
    @abc.abstractmethod
    def get(self, control_id: int) -> List[Dict]:
        """
        获取 gird 数据并格式化返回

        :param control_id: grid 的 control id
        :return: grid 数据
        """
        pass

    @abc.abstractmethod
    def set_trader(self, trader: "clienttrader.IClientTrader"):
        pass


class BaseStrategy(IGridStrategy):
    def __init__(self):
        self._trader = None

    def set_trader(self, trader: "clienttrader.IClientTrader"):
        self._trader = trader

    @abc.abstractmethod
    def get(self, control_id: int) -> List[Dict]:
        """
        :param control_id: grid 的 control id
        :return: grid 数据
        """
        pass

    def _get_grid(self, control_id: int):
        grid = self._trader.main.child_window(
            control_id=control_id, class_name="CVirtualGridCtrl"
        )
        return grid

    def _set_foreground(self, grid=None):
        try:
            if grid is None:
                grid = self._trader.main
            if grid.has_style(win32defines.WS_MINIMIZE):  # if minimized
                ShowWindow(grid.wrapper_object(), 9)  # restore window state
            else:
                SetForegroundWindow(grid.wrapper_object())  # bring to front
        except:
            pass


class Copy(BaseStrategy):
    """
    通过复制 grid 内容到剪切板再读取来获取 grid 内容
    """

    _need_captcha_reg = True

    def get(self, control_id: int) -> List[Dict]:
        grid = self._get_grid(control_id)
        self._set_foreground(grid)
        grid.type_keys("^A^C", set_foreground=False)
        content = self._get_clipboard_data()
        return self._format_grid_data(content)

    def _format_grid_data(self, data: str) -> List[Dict]:
        try:
            df = pd.read_csv(
                io.StringIO(data),
                delimiter="\t",
                dtype=self._trader.config.GRID_DTYPE,
                na_filter=False,
            )
            return df.to_dict("records")
        except:
            Copy._need_captcha_reg = True

    def _get_clipboard_data(self) -> str:
        if Copy._need_captcha_reg:
            logger.info("检查是否存在验证码窗口（等待5秒）")
            if (
                    self._trader.app.top_window().window(class_name="Static", title_re="验证码").exists(timeout=5)
            ):
                logger.info("检测到验证码窗口，开始处理验证码")
                file_path = "tmp.png"
                count = 5
                found = False
                while count > 0:
                    logger.info(f"开始第 {6-count} 次验证码识别尝试")
                    
                    # 保存验证码图片
                    self._trader.app.top_window().window(
                        control_id=0x965, class_name="Static"
                    ).capture_as_image().save(
                        file_path
                    )
                    logger.info(f"验证码图片已保存到: {file_path}")

                    # 识别验证码
                    captcha_num = captcha_recognize(file_path).strip()
                    logger.info(f"原始识别结果: {captcha_num}")
                    
                    # 提取纯数字
                    import re
                    captcha_num = re.sub(r'\D', '', captcha_num)
                    logger.info(f"提取数字后的验证码: {captcha_num}")
                    
                    if len(captcha_num) >= 4:
                        # 只取前4位数字
                        captcha_num = captcha_num[:4]
                        logger.info(f"最终使用的验证码: {captcha_num}")
                        
                        # 先点击输入框获取焦点
                        edit_control = self._trader.app.top_window().window(
                            control_id=0x964, class_name="Edit"
                        )
                        logger.info("点击验证码输入框")
                        edit_control.click_input()
                        self._trader.wait(0.2)
                        
                        # 清空输入框并输入验证码
                        logger.info(f"开始输入验证码: {captcha_num}")
                        edit_control.set_edit_text("")
                        self._trader.wait(0.1)
                        edit_control.type_keys(captcha_num)
                        self._trader.wait(0.2)
                        logger.info("验证码输入完成")
                        
                        # 点击确认按钮
                        try:
                            logger.info("查找并点击确认按钮")
                            confirm_btn = self._trader.app.top_window().window(
                                control_id=0x1, class_name="Button"
                            )
                            confirm_btn.click()
                            logger.info("确认按钮已点击")
                        except Exception as ex:
                            logger.warning(f"点击确认按钮失败，尝试使用回车键: {ex}")
                            self._trader.app.top_window().set_focus()
                            pywinauto.keyboard.SendKeys("{ENTER}")
                            logger.info("已发送回车键")
                        
                        self._trader.wait(0.5)  # 等待验证码验证
                        
                        try:
                            # 检查验证码窗口是否还存在
                            if not self._trader.app.top_window().window(class_name="Static", title_re="验证码").exists(timeout=0.5):
                                logger.info("验证码验证成功，窗口已关闭")
                                found = True
                                break
                            else:
                                logger.warning("验证码窗口仍然存在，验证可能失败")
                        except Exception as ex:  # 窗体消失
                            logger.info(f"验证码窗口已消失（异常方式）: {ex}")
                            found = True
                            break
                    else:
                        logger.warning(f"识别的验证码长度不足4位: {captcha_num}")
                    
                    count -= 1
                    self._trader.wait(0.1)
                    
                    # 刷新验证码
                    if count > 0:
                        try:
                            logger.info("刷新验证码图片")
                            self._trader.app.top_window().window(
                                control_id=0x965, class_name="Static"
                            ).click()
                        except Exception as ex:
                            logger.warning(f"刷新验证码失败: {ex}")
                if not found:
                    logger.warning("验证码识别失败，尝试点击取消按钮")
                    try:
                        self._trader.app.top_window().Button2.click()  # 点击取消
                        logger.info("已点击取消按钮")
                    except Exception as ex:
                        logger.warning(f"点击取消按钮失败: {ex}")
            else:
                logger.info("未检测到验证码窗口")
                Copy._need_captcha_reg = False
        count = 5
        logger.info("开始从剪贴板获取数据")
        while count > 0:
            try:
                data = pywinauto.clipboard.GetData()
                logger.info(f"成功从剪贴板获取数据，数据长度: {len(data) if data else 0}")
                return data
            # pylint: disable=broad-except
            except Exception as e:
                count -= 1
                logger.warning(f"获取剪贴板数据失败: {e}, 剩余重试次数: {count}")
                logger.exception("%s, retry ......", e)


class WMCopy(Copy):
    """
    通过复制 grid 内容到剪切板再读取来获取 grid 内容
    """

    def get(self, control_id: int) -> List[Dict]:
        grid = self._get_grid(control_id)
        grid.post_message(win32defines.WM_COMMAND, 0xE122, 0)
        self._trader.wait(0.1)
        content = self._get_clipboard_data()
        return self._format_grid_data(content)


class Xls(BaseStrategy):
    """
    通过将 Grid 另存为 xls 文件再读取的方式获取 grid 内容
    """

    def __init__(self, tmp_folder: Optional[str] = None):
        """
        :param tmp_folder: 用于保持临时文件的文件夹
        """
        super().__init__()
        self.tmp_folder = tmp_folder

    def get(self, control_id: int) -> List[Dict]:
        grid = self._get_grid(control_id)

        # ctrl+s 保存 grid 内容为 xls 文件
        self._set_foreground(grid)  # setFocus buggy, instead of SetForegroundWindow
        grid.type_keys("^s", set_foreground=False)
        count = 10
        while count > 0:
            if self._trader.is_exist_pop_dialog():
                break
            self._trader.wait(0.2)
            count -= 1

        temp_path = tempfile.mktemp(suffix=".xls", dir=self.tmp_folder)
        self._set_foreground(self._trader.app.top_window())

        # alt+s保存，alt+y替换已存在的文件
        self._trader.app.top_window().Edit1.set_edit_text(temp_path)
        self._trader.wait(0.1)
        self._trader.app.top_window().type_keys("%{s}%{y}", set_foreground=False)
        # Wait until file save complete otherwise pandas can not find file
        self._trader.wait(0.2)
        if self._trader.is_exist_pop_dialog():
            self._trader.app.top_window().Button2.click()
            self._trader.wait(0.2)

        return self._format_grid_data(temp_path)

    def _format_grid_data(self, data: str) -> List[Dict]:
        with open(data, encoding="gbk", errors="replace") as f:
            content = f.read()

        df = pd.read_csv(
            StringIO(content),
            delimiter="\t",
            dtype=self._trader.config.GRID_DTYPE,
            na_filter=False,
        )
        return df.to_dict("records")
