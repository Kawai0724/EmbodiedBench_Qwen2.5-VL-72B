import os
import hydra
from omegaconf import DictConfig, OmegaConf
import logging
import yaml

logger = logging.getLogger("EB_logger")
if not logger.hasHandlers():
    formatter = logging.Formatter("[%(asctime)s][%(levelname)s] - %(message)s")
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

link_path = os.path.join(os.path.dirname(__file__), 'envs/eb_habitat/data')
try:
    os.symlink(link_path, 'data')
except FileExistsError:
    pass 
#新加的
import sys
from types import ModuleType

# 伪造一个 pyairports 模块
mock_pyairports = ModuleType("pyairports")
mock_airports_sub = ModuleType("pyairports.airports")

# 给它一个空的 AIRPORT_LIST，让 outlines 满意
mock_airports_sub.AIRPORT_LIST = []

# 注入到系统路径
mock_pyairports.airports = mock_airports_sub
sys.modules["pyairports"] = mock_pyairports
sys.modules["pyairports.airports"] = mock_airports_sub



# the corresponding evaluator class
class_names = {
    "eb-alf": "EB_AlfredEvaluator",
    "eb-hab": "EB_HabitatEvaluator",
    "eb-nav": "EB_NavigationEvaluator",
    "eb-man": "EB_ManipulationEvaluator"
}

# the evaluator file you want to use
module_names = {
    "eb-alf": "eb_alfred_evaluator",
    "eb-hab": "eb_habitat_evaluator",
    "eb-nav": "eb_navigation_evaluator",
    "eb-man": "eb_manipulation_evaluator"
}

def get_evaluator(env_name: str):

    if env_name not in module_names:
        raise ValueError(f"Unknown environment: {env_name}")
    
    module_name = f"embodiedbench.evaluator.{module_names[env_name]}"
    evaluator_name = class_names[env_name]
    #fromlist告诉python要一直导入到这个类，所以会递归地搜索直到from_list[]
    module = __import__(module_name, fromlist=[evaluator_name])
    #getattr是返回这个类，而不是整个文件
    return getattr(module, evaluator_name)

@hydra.main(config_path="./configs", config_name="config", version_base=None)
def main(cfg: DictConfig) -> None:
    # Hydra 装饰器会将命令行参数和配置文件合并为 cfg 对象传入
    # config_path: 配置文件所在目录（相对于当前脚本）
    # config_name: 基础配置文件名（不含 .yaml 后缀）
    #Hydra 通过以下步骤将命令行参数转化为代码中可直接使用的 cfg 对象：
    '''
    Hydra 通过以下步骤将命令行参数转化为代码中可直接使用的 cfg 对象：

加载基础配置：@hydra.main 装饰器读取指定路径下的基础配置文件（如 configs/config.yaml），将其内容解析为一个字典结构。

解析命令行覆盖：运行脚本时附加的 key=value 参数（如 env=eb-man、model_name=gpt-4o）被 Hydra 捕获，并与基础配置递归合并。

生成 cfg 对象：合并后的完整配置被封装成 DictConfig 对象，作为参数传递给 main 函数。

代码中直接使用：在 main 函数内部，你可以通过 cfg.env、cfg.model_name 等方式访问这些参数，就像操作普通字典一样。

这种机制使得代码中的参数（如 env、model_name、tp 等）不再硬编码，而是完全由外部配置和命令行控制，实现了灵活的实验管理。
    '''

    logging.getLogger().handlers.clear()
    
    if 'log_level' not in cfg or cfg.log_level == "INFO":
        logger.setLevel(logging.INFO)
    if 'log_level' in cfg and cfg.log_level == "DEBUG":
        logger.setLevel(logging.DEBUG)

    env_name = cfg.env
    logger.info(f"Evaluating environment: {env_name}")
    
    with open(f"embodiedbench/configs/{env_name}.yaml", 'r') as f:
        base_config = yaml.safe_load(f)

    override_config = {
        k: v for k, v in OmegaConf.to_container(cfg).items() 
        if k != 'env' and v is not None
    }
    
    config = OmegaConf.merge(
        OmegaConf.create(base_config),
        override_config
    )

    print(config)
    logger.info("Starting evaluation")
    evaluator_class = get_evaluator(env_name)
    evaluator = evaluator_class(config)
    evaluator.check_config_valid()
    evaluator.evaluate_main()
    logger.info("Evaluation completed")

if __name__ == "__main__":
    main()