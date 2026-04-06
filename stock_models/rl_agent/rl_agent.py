from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import gym


class RLAgentParam:
    """RL Agent初始化参数类"""

    def __init__(
        self,
        model_name: str,
        policy: str = "MlpPolicy",
        policy_kwargs: Optional[Dict] = None,
        model_kwargs: Optional[Dict] = None,
        verbose: int = 1,
        total_timesteps: int = 10000,
        tb_log_name: Optional[str] = None,
        eval_freq: int = 500,
        log_interval: int = 1,
        n_eval_episodes: int = 1,
        model_path: Optional[str] = None
    ):
        """
        初始化RL Agent参数
        
        Args:
            model_name: 模型名称，如'PPO', 'A2C', 'SAC'等
            policy: 策略类型，默认'MlpPolicy'
            policy_kwargs: 策略的额外参数字典
            model_kwargs: 模型的额外参数字典
            verbose: 日志详细程度，默认1
            total_timesteps: 训练总步数，默认10000
            tb_log_name: TensorBoard日志名称
            eval_freq: 评估频率，默认500
            log_interval: 日志记录间隔，默认1
            n_eval_episodes: 评估回合数，默认1
            model_path: 模型保存/加载路径，默认None
        """
        self.model_name = model_name
        self.policy = policy
        self.policy_kwargs = policy_kwargs if policy_kwargs is not None else {}
        self.model_kwargs = model_kwargs if model_kwargs is not None else {}
        self.verbose = verbose
        self.total_timesteps = total_timesteps
        self.tb_log_name = tb_log_name if tb_log_name is not None else model_name
        self.eval_freq = eval_freq
        self.log_interval = log_interval
        self.n_eval_episodes = n_eval_episodes
        self.model_path = model_path


class RLAgent(ABC):
    """RL Agent接口类，定义强化学习代理的标准接口"""

    def __init__(self, env: gym.Env, param: RLAgentParam):
        """
        初始化RL Agent
        
        Args:
            env: gym环境对象
            param: RLAgentParam对象，包含RL Agent初始化所需的所有参数
        """
        self.env = env
        self.param = param
        self.model = None

    @abstractmethod
    def train(self):
        """训练模型"""
        pass

    @abstractmethod
    def predict(self, observation, deterministic: bool = True):
        """
        预测动作
        
        Args:
            observation: 观察值
            deterministic: 是否使用确定性策略
            
        Returns:
            action: 预测的动作
        """
        pass

    @abstractmethod
    def save(self, path: Optional[str] = None):
        """
        保存模型
        
        Args:
            path: 保存路径，如果为None则使用param.model_path
        """
        pass

    @abstractmethod
    def load(self, path: Optional[str] = None):
        """
        加载模型
        
        Args:
            path: 模型路径，如果为None则使用param.model_path
        """
        pass

    def debug(self):
        """调试方法，可选实现"""
        print(f"模型名称: {self.param.model_name}")
        print(f"策略类型: {self.param.policy}")
        print(f"训练步数: {self.param.total_timesteps}")
        print(f"日志名称: {self.param.tb_log_name}")
        print(f"策略参数: {self.param.policy_kwargs}")
        print(f"模型参数: {self.param.model_kwargs}")