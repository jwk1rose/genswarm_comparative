import os
import yaml

from swarm_prompt.robot_api_prompt_for_llm2swarm import GLOBAL_ROBOT_API, LOCAL_ROBOT_API
from swarm_prompt.user_requirements import get_user_commands
from swarm_prompt.env_description_prompt import ENV_DES

script_dir = os.path.dirname(os.path.abspath(__file__))
yaml_file_path = os.path.join(script_dir, "../config/", "experiment_config.yaml")

with open(yaml_file_path, "r", encoding="utf-8") as file:
    data = yaml.safe_load(file)
task_name = data["arguments"]["--run_experiment_name"]["default"][0]


UserRequirement = get_user_commands(task_name)[0]

api_prompt = f"""
In addition to the methods demonstrated in the example, the following APIs are also available and can be called directly using the format:
robot.[API_NAME]()

For example:
robot.get_prey_position()
robot.get_all_robots_initial_position()

----
{GLOBAL_ROBOT_API}
{LOCAL_ROBOT_API}
"""

