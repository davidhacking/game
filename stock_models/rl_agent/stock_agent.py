from typing import Optional
import gym
import numpy as np
from stable_baselines3 import A2C, DDPG, TD3, SAC, PPO
from stable_baselines3.common.noise import NormalActionNoise, OrnsteinUhlenbeckActionNoise
from stable_baselines3.common.evaluation import evaluate_policy

from .rl_agent import RLAgent, RLAgentParam
from config.model_params import get_model_params


class StockAgent(RLAgent):
    """基于stable_baselines3的股票交易强化学习代理实现"""
    
    # 支持的模型类映射
    MODEL_CLASSES = {
        "a2c": A2C,
        "ddpg": DDPG,
        "td3": TD3,
        "sac": SAC,
        "ppo": PPO
    }
    
    # 噪声类映射
    NOISE_CLASSES = {
        "normal": NormalActionNoise,
        "ornstein_uhlenbeck": OrnsteinUhlenbeckActionNoise
    }
    
    def __init__(self, env: gym.Env, param: RLAgentParam):
        """
        初始化StockAgent
        
        Args:
            env: gym环境对象
            param: RLAgentParam对象，包含RL Agent初始化所需的所有参数
        """
        super().__init__(env, param)
        self._init_model()
    
    def _init_model(self):
        """初始化stable_baselines3模型"""
        model_name_lower = self.param.model_name.lower()
        
        if model_name_lower not in self.MODEL_CLASSES:
            raise ValueError(f"不支持的模型类型: {self.param.model_name}. 支持的类型: {list(self.MODEL_CLASSES.keys())}")
        
        # 获取默认参数并与用户提供的参数合并
        default_params = get_model_params(model_name_lower)
        # 用户提供的参数会覆盖默认参数
        default_params.update(self.param.model_kwargs)
        model_kwargs = default_params
        if "action_noise" in model_kwargs:
            noise_type = model_kwargs["action_noise"]
            if isinstance(noise_type, str) and noise_type in self.NOISE_CLASSES:
                n_actions = self.env.action_space.shape[-1]
                model_kwargs["action_noise"] = self.NOISE_CLASSES[noise_type](
                    mean=np.zeros(n_actions), 
                    sigma=0.1 * np.ones(n_actions)
                )
        
        # 创建模型
        model_class = self.MODEL_CLASSES[model_name_lower]
        
        # 设置tensorboard日志路径（如果需要）
        tensorboard_log = None
        if hasattr(self.param, 'tensorboard_log_dir') and self.param.tensorboard_log_dir:
            tensorboard_log = f"{self.param.tensorboard_log_dir}/{self.param.model_name}"
        
        self.model = model_class(
            policy=self.param.policy,
            env=self.env,
            verbose=self.param.verbose,
            policy_kwargs=self.param.policy_kwargs if self.param.policy_kwargs else None,
            tensorboard_log=tensorboard_log,
            **model_kwargs
        )
    
    def train(self, eval_env: Optional[gym.Env] = None):
        """
        训练模型
        
        Args:
            eval_env: 评估环境，如果为None则不进行评估
        
        Returns:
            训练后的模型
        """
        if self.model is None:
            raise ValueError("模型未初始化，请先调用_init_model()")
        
        print(f"开始训练 {self.param.model_name} 模型，总步数: {self.param.total_timesteps}")
        self.model.learn(
            total_timesteps=self.param.total_timesteps,
            eval_env=eval_env,
            eval_freq=self.param.eval_freq,
            log_interval=self.param.log_interval,
            tb_log_name=self.param.tb_log_name,
            n_eval_episodes=self.param.n_eval_episodes
        )
        print(f"训练完成！")
        
        # 训练完成后自动保存模型
        if self.param.model_path:
            self.save()
            print(f"模型已自动保存到: {self.param.model_path}")
        
        return self.model
    
    def predict(self, observation, deterministic: bool = True):
        """
        预测动作
        
        Args:
            observation: 观察值
            deterministic: 是否使用确定性策略
            
        Returns:
            action: 预测的动作
            state: 模型状态（如果有）
        """
        if self.model is None:
            raise ValueError("模型未初始化或未加载")
        
        action, state = self.model.predict(observation, deterministic=deterministic)
        return action, state
    
    def save(self, path: Optional[str] = None):
        """
        保存模型
        
        Args:
            path: 保存路径，如果为None则使用param.model_path
        """
        if self.model is None:
            raise ValueError("模型未初始化，无法保存")
        
        save_path = path if path is not None else self.param.model_path
        if save_path is None:
            raise ValueError("未指定保存路径，请提供path参数或在初始化时设置param.model_path")
        
        self.model.save(save_path)
        print(f"模型已保存到: {save_path}")
    
    def load(self, path: Optional[str] = None):
        """
        加载模型
        
        Args:
            path: 模型路径，如果为None则使用param.model_path
        """
        model_name_lower = self.param.model_name.lower()
        
        if model_name_lower not in self.MODEL_CLASSES:
            raise ValueError(f"不支持的模型类型: {self.param.model_name}")
        
        load_path = path if path is not None else self.param.model_path
        if load_path is None:
            raise ValueError("未指定加载路径，请提供path参数或在初始化时设置param.model_path")
        
        model_class = self.MODEL_CLASSES[model_name_lower]
        self.model = model_class.load(load_path, env=self.env)
        print(f"模型已从 {load_path} 加载")
    
    def evaluate(self, env=None, n_eval_episodes: int = 10, deterministic: bool = True):
        """
        评估模型性能（简单评估）
        
        Args:
            env: 评估环境，如果为None则使用训练环境
            n_eval_episodes: 评估回合数
            deterministic: 是否使用确定性策略
            
        Returns:
            mean_reward: 平均奖励
            std_reward: 奖励标准差
        """
        if self.model is None:
            raise ValueError("模型未初始化或未加载")
        
        eval_env = env if env is not None else self.env
        mean_reward, std_reward = evaluate_policy(
            self.model, 
            eval_env, 
            n_eval_episodes=n_eval_episodes,
            deterministic=deterministic
        )
        
        print(f"评估结果 ({n_eval_episodes} 回合): 平均奖励={mean_reward:.2f} +/- {std_reward:.2f}")
        return mean_reward, std_reward
    
    def backtest(self, deterministic: bool = True):
        """
        回测模型性能（详细回测，逐步执行并记录）
        
        Args:
            deterministic: 是否使用确定性策略
            
        Returns:
            df_account_value: 账户价值记录DataFrame
            df_actions: 动作记录DataFrame
        """
        if self.model is None:
            raise ValueError("模型未初始化或未加载")
        
        # 获取stable_baselines3兼容的环境
        test_env = self.env
        
        # 重置环境
        test_obs = test_env.reset()
        
        # 获取环境的时间步数
        # 通过访问原始环境来获取df属性
        if hasattr(self.env, 'envs') and len(self.env.envs) > 0:
            len_environment = len(self.env.envs[0].df.index.unique())
        else:
            # 如果无法通过envs访问，尝试直接访问df
            len_environment = len(self.env.df.index.unique())
        
        print(f"开始回测，总时间步数: {len_environment}")
        
        # 逐步执行回测
        for i in range(len_environment):
            # 预测动作
            predict_action, _states = self.model.predict(test_obs, deterministic=deterministic)
            
            # 执行动作
            test_obs, rewards, dones, info = test_env.step(predict_action)
            
            # 在倒数第二步保存记录（因为最后一步会触发done）
            if i == (len_environment - 2):
                account_memory = test_env.env_method(method_name="save_asset_memory")
                actions_memory = test_env.env_method(method_name="save_action_memory")
            
            # 如果回合结束，退出循环
            if dones[0]:
                print("回测完成!")
                break
        
        # 返回账户价值和动作记录
        df_account_value = account_memory[0] if account_memory and account_memory[0] is not None else None
        df_actions = actions_memory[0] if actions_memory and actions_memory[0] is not None else None
        
        if df_account_value is not None:
            final_value = df_account_value['total_assets'].iloc[-1]
            initial_value = df_account_value['total_assets'].iloc[0]
            total_return = (final_value - initial_value) / initial_value * 100
            print(f"回测结果: 初始资产={initial_value:.2f}, 最终资产={final_value:.2f}, 总收益率={total_return:.2f}%")
        
        return df_account_value, df_actions
