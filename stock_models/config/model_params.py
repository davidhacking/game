"""
强化学习模型默认参数配置
包含A2C, PPO, DDPG, TD3, SAC等模型的默认超参数
"""

# A2C模型默认参数
A2C_PARAMS = {
    "n_steps": 5, 
    "ent_coef": 0.01, 
    "learning_rate": 0.0007
}

# PPO模型默认参数
PPO_PARAMS = {
    "n_steps": 256,
    "ent_coef": 0.01,
    "learning_rate": 0.00005,
    "batch_size": 256
}

# DDPG模型默认参数
DDPG_PARAMS = {
    "batch_size": 128, 
    "buffer_size": 50000, 
    "learning_rate": 0.001
}

# TD3模型默认参数
TD3_PARAMS = {
    "batch_size": 100, 
    "buffer_size": 1000000, 
    "learning_rate": 0.001
}

# SAC模型默认参数
SAC_PARAMS = {
    "batch_size": 64,
    "buffer_size": 100000,
    "learning_rate": 0.0001,
    "learning_starts": 2000,
    "ent_coef": "auto_0.1"
}

# 所有模型参数的字典映射
MODEL_PARAMS = {
    "a2c": A2C_PARAMS,
    "ppo": PPO_PARAMS,
    "ddpg": DDPG_PARAMS,
    "td3": TD3_PARAMS,
    "sac": SAC_PARAMS
}


def get_model_params(model_name: str) -> dict:
    """
    获取指定模型的默认参数
    
    Args:
        model_name: 模型名称（不区分大小写）
        
    Returns:
        dict: 模型的默认参数字典
        
    Raises:
        ValueError: 如果模型名称不支持
    """
    model_name_lower = model_name.lower()
    if model_name_lower not in MODEL_PARAMS:
        raise ValueError(
            f"不支持的模型类型: {model_name}. "
            f"支持的类型: {list(MODEL_PARAMS.keys())}"
        )
    return MODEL_PARAMS[model_name_lower].copy()
