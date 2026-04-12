"""直接在 Windows 上查询同花顺账户信息（不依赖 Flask 服务）"""
import sys
import json

sys.path.insert(0, r"C:\Users\windows\Desktop\Shared\stock_models\brokerage")
import easytrader

try:
    user = easytrader.use('ths')
    user.connect(r"C:\同花顺软件\同花顺\xiadan.exe")

    print("=== Balance ===")
    balance = user.balance
    print(json.dumps(balance, ensure_ascii=False, indent=2))

    print("\n=== Position ===")
    position = user.position
    print(json.dumps(position, ensure_ascii=False, indent=2))

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
