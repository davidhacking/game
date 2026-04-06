from .user_stock_account import UserStockAccount, create_dataframes
from .local_account import LocalUserStockAccount
from .futu_account import FutuUserStockAccount
from .ths_account import ThsUserStockAccount

# 账户工厂字典，用于根据类型创建不同的账户实例
UserStockAccountFactory = {
    "LocalUserStockAccount": LocalUserStockAccount,
    "FutuUserStockAccount": FutuUserStockAccount,
    "ThsUserStockAccount": ThsUserStockAccount,
}

__all__ = [
    'UserStockAccount',
    'LocalUserStockAccount',
    'FutuUserStockAccount',
    'ThsUserStockAccount',
    'UserStockAccountFactory',
    'create_dataframes'
]
