import os
import yaml

from swarm_prompt.robot_api_prompt import GLOBAL_ROBOT_API, LOCAL_ROBOT_API
from swarm_prompt.user_requirements import get_user_commands
from swarm_prompt.env_description_prompt import ENV_DES
from swarm_prompt.task_description import TASK_DES

script_dir = os.path.dirname(os.path.abspath(__file__))
yaml_file_path = os.path.join(script_dir, "../config/", "experiment_config.yaml")

with open(yaml_file_path, "r", encoding="utf-8") as file:
    data = yaml.safe_load(file)
task_name = data["arguments"]["--run_experiment_name"]["default"][0]

UserRequirement = get_user_commands(task_name)[0]

swarm_system_prompt = f"""
Now, your team are required to implement a swarm robot system.So your team need to design a software system for the swarm robot system.
## These are the task description:
{TASK_DES}

## These are the environment description:
{ENV_DES}

## These APIs can be directly called by you.
from api import ...
{GLOBAL_ROBOT_API}
{LOCAL_ROBOT_API}

## These are the user provided commands:
These user-provided instructions must be fulfilled.
- The interface should be a 'main()' in the main.py file,user can only 'from main import main' to call the interface to run the experiment.
- The software is designed for the swarm robot system,so the UI and interaction with the user is forbidden.
- The software should automatically achieve the user's instructions by assigning different tasks based on each robot's ID, thereby achieving the final goal.
- The provided basic Robot APIs have already been implemented. You cannot modify these functions; you can only call them directly by name.
- The software is not allowed to use Thread or Process or ROS or other similar libraries to implement the control logic.
"""
