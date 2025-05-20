import sys
import yaml

with open('../config/config2.yaml', 'r') as file:
    config = yaml.safe_load(file)
    openai_base = config['llm']['base_url']
    openai_api_key = config['llm']['api_key']
    model_name = config['llm']['model']

import os
import numpy as np
import copy
import openai
import re
# imports for LMPs
import ast
import astunparse
from time import sleep
from openai.error import RateLimitError, APIConnectionError
from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import TerminalFormatter

from prompt_swarm_robot import swarm_system_prompt, task_name
from swarm_prompt.robot_api_prompt import robot_api, GLOBAL_ROBOT_API, LOCAL_ROBOT_API

openai.api_key = openai_api_key
openai.api_base = openai_base


class LMP:

    def __init__(self, name, cfg, lmp_fgen, fixed_vars, variable_vars):
        self._name = name
        self._cfg = cfg

        self._base_prompt = self._cfg['prompt_text']

        self._stop_tokens = list(self._cfg['stop'])

        self._lmp_fgen = lmp_fgen

        self._fixed_vars = fixed_vars
        self._variable_vars = variable_vars
        self.exec_hist = ''

    def clear_exec_hist(self):
        self.exec_hist = ''

    def build_prompt(self, query, context=''):
        if len(self._variable_vars) > 0:
            variable_vars_imports_str = f"from api import (\n    " + ',\n    '.join(self._variable_vars.keys()) + '\n)'
        else:
            variable_vars_imports_str = ''

        #  system prompt
        prompt = self._base_prompt.format(
            api=GLOBAL_ROBOT_API + LOCAL_ROBOT_API,
            instruction=query,
        )

        # chat history
        if self._cfg['maintain_session']:
            prompt += f'\n{self.exec_hist}'

        if context != '':
            prompt += f'\n{context}'

        # use_query = f'{self._cfg["query_prefix"]}{query}{self._cfg["query_suffix"]}'
        # prompt += f'\n{use_query}'

        return prompt

    def __call__(self, query, context='', **kwargs):
        prompt = self.build_prompt(query, context=context)

        while True:
            try:
                # code_str = openai.Completion.create(
                #     prompt=prompt,
                #     stop=self._stop_tokens,
                #     temperature=self._cfg['temperature'],
                #     engine=self._cfg['engine'],
                #     max_tokens=self._cfg['max_tokens']
                # )['choices'][0]['text'].strip()
                print(prompt)
                response = openai.ChatCompletion.create(
                    model=self._cfg['engine'],
                    messages=[{"role": "user", "content": prompt}],
                    # max_tokens=self._cfg['max_tokens'],
                    temperature=self._cfg['temperature'],  # o1 mini model: Only the default (1) value is supported..
                ).choices[0].message.content.strip()
                print(response)
                code_str = ''
                match = re.search(r'```python\n(.*?)\n```', response, re.DOTALL)
                if match:
                    code_str = match.group(1)
                    # print(code_str)
                break
            except (RateLimitError, APIConnectionError) as e:
                print(f'OpenAI API got err {e}')
                print('Retrying after 10s.')
                sleep(10)

        if self._cfg['include_context'] and context != '':
            to_exec = f'{context}\n{code_str}'
        else:
            to_exec = code_str

        new_fs, src = self._lmp_fgen.create_new_fs_from_code(code_str)
        self._variable_vars.update(new_fs)

        gvars = merge_dicts([self._fixed_vars, self._variable_vars])
        lvars = kwargs

        self.exec_hist += f'\n{to_exec}'
        #
        if self._cfg['maintain_session']:
            self._variable_vars.update(lvars)

        if self._cfg['has_return']:
            return lvars[self._cfg['return_val_name']]
        code_str = code_str + '\n' + '\n'.join([v for k, v in src.items()])
        from datetime import datetime
        import random
        workspace_dir = f"../workspace/CaP/{task_name}/{task_name}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]}_{random.randint(1000000, 9999999)}"
        file_path = os.path.join(workspace_dir, f"main.py")
        os.makedirs(workspace_dir, exist_ok=True)
        with open(file_path, 'w') as file:
            file.write(code_str)


class LMPFGen:

    def __init__(self, cfg, fixed_vars, variable_vars):
        self._cfg = cfg

        self._stop_tokens = list(self._cfg['stop'])
        self._fixed_vars = fixed_vars
        self._variable_vars = variable_vars

        self._base_prompt = self._cfg['prompt_text']

    def create_f_from_sig(self, f_name, f_sig, other_vars=None, fix_bugs=False, return_src=False):
        print(f'Creating function: {f_sig}')

        prompt = self._base_prompt.format(
            api=GLOBAL_ROBOT_API + LOCAL_ROBOT_API,
            function_signature=f_sig
        )

        while True:
            try:
                # f_src = openai.Completion.create(
                #     prompt=prompt,
                #     stop=self._stop_tokens,
                #     temperature=self._cfg['temperature'],
                #     engine=self._cfg['engine'],
                #     max_tokens=self._cfg['max_tokens']
                # ).choices[0].message.content.strip()
                f_src = openai.ChatCompletion.create(
                    model=self._cfg['engine'],
                    messages=[{"role": "user", "content": prompt}],
                    # max_tokens=self._cfg['max_tokens'],
                    temperature=self._cfg['temperature'],  # o1 mini model: Only the default (1) value is supported..
                ).choices[0].message.content.strip()
                match = re.search(r'```python\n(.*?)\n```', f_src, re.DOTALL)
                if match:
                    f_src = match.group(1)
                break
            except (RateLimitError, APIConnectionError) as e:
                print(f'OpenAI API got err {e}')
                print('Retrying after 10s.')
                sleep(10)
        # if fix_bugs:
        #     f_src = openai.Edit.create(
        #         model='code-davinci-edit-001',
        #         input='# ' + f_src,
        #         temperature=0,
        #         instruction='Fix the bug if there is one. Improve readability. Keep same inputs and outputs. Only small changes. No comments.',
        #     )['choices'][0]['text'].strip()

        if other_vars is None:
            other_vars = {}
        gvars = merge_dicts([self._fixed_vars, self._variable_vars, other_vars])
        lvars = {}

        exec_safe(f_src, gvars, lvars)

        f = lvars[f_name]

        to_print = highlight(f'\n{f_src}', PythonLexer(), TerminalFormatter())
        print(f'LMP FGEN created:\n\n{to_print}\n')

        if return_src:
            return f, f_src
        return f

    def create_new_fs_from_code(self, code_str, other_vars=None, fix_bugs=False, return_src=True):
        fs, f_assigns = {}, {}
        f_parser = FunctionParser(fs, f_assigns)
        f_parser.visit(ast.parse(code_str))
        for f_name, f_assign in f_assigns.items():
            if f_name in fs:
                fs[f_name] = f_assign

        if other_vars is None:
            other_vars = {}

        new_fs = {}
        srcs = {}
        for f_name, f_sig in fs.items():
            all_vars = merge_dicts([self._fixed_vars, self._variable_vars, new_fs, other_vars])
            if not var_exists(f_name, all_vars):
                f, f_src = self.create_f_from_sig(f_name, f_sig, new_fs, fix_bugs=fix_bugs, return_src=True)

                # recursively define child_fs in the function body if needed
                f_def_body = astunparse.unparse(ast.parse(f_src).body[0].body)
                child_fs, child_f_srcs = self.create_new_fs_from_code(
                    f_def_body, other_vars=all_vars, fix_bugs=fix_bugs, return_src=True
                )

                if len(child_fs) > 0:
                    new_fs.update(child_fs)
                    srcs.update(child_f_srcs)

                    # redefine parent f so newly created child_fs are in scope
                    gvars = merge_dicts([self._fixed_vars, self._variable_vars, new_fs, other_vars])
                    lvars = {}

                    f = lvars[f_name]

                new_fs[f_name], srcs[f_name] = f, f_src

        if return_src:
            return new_fs, srcs
        return new_fs


class FunctionParser(ast.NodeTransformer):

    def __init__(self, fs, f_assigns):
        super().__init__()
        self._fs = fs
        self._f_assigns = f_assigns

    def visit_Call(self, node):
        self.generic_visit(node)
        if isinstance(node.func, ast.Name):
            f_sig = astunparse.unparse(node).strip()
            f_name = astunparse.unparse(node.func).strip()
            self._fs[f_name] = f_sig
        return node

    def visit_Assign(self, node):
        self.generic_visit(node)
        if isinstance(node.value, ast.Call):
            assign_str = astunparse.unparse(node).strip()
            f_name = astunparse.unparse(node.value.func).strip()
            self._f_assigns[f_name] = assign_str
        return node


def var_exists(name, all_vars):
    try:
        eval(name, all_vars)
    except:
        exists = False
    else:
        exists = True
    return exists


def merge_dicts(dicts):
    return {
        k: v
        for d in dicts
        for k, v in d.items()
    }


def exec_safe(code_str, gvars=None, lvars=None):
    # banned_phrases = ['import', '__']
    # print(code_str)
    # for phrase in banned_phrases:
    #     assert phrase not in code_str

    if gvars is None:
        gvars = {}
    if lvars is None:
        lvars = {}
    empty_fn = lambda *args, **kwargs: None
    custom_gvars = merge_dicts([
        gvars,
        {'exec': empty_fn, 'eval': empty_fn}
    ])
    exec(code_str, custom_gvars, lvars)


class LMP_wrapper():

    def __init__(self):
        pass

    def get_all_robots_id(self):
        """
        Description: Get the unique IDs of all robots in the environment.(Including the robot itself)
        Returns:
        - list: A list of integers, each representing the unique ID of a robot in the environment.
        """
        pass

    def get_all_robots_initial_position(self):
        """
        Description: Get the initial position of all robots in the environment.
        Returns:
        -dict: A dictionary where the keys are robot IDs and values are the initial positions of the robots.
            - key: int, the robot id.
            - value: numpy.ndarray, the initial position of the robot.
        """
        pass

    def get_target_formation_points(self):
        """
        Description: Get the target formation points for the robot to reach.
        Returns:
        - list: A list of numpy.ndarray, all representing target points for robots.
        """
        pass

    def get_self_id(self):
        """
        Description: Get the unique ID of the robot itself.
        Returns:
        - int: The unique ID of the robot itself.ID is a unique identifier for each robot in the environment.
        """
        pass

    def get_self_position(self):
        """
        Description: Get the current position of the robot itself in real-time.
        Returns:
        - numpy.ndarray: The current, real-time position of the robot.
        """
        pass

    def set_self_velocity(self, velocity):
        """
        Description: Set the velocity of the robot itself in real-time.
        Input:
        - velocity (numpy.ndarray): The new velocity to be set immediately.
        """
        pass

    def get_self_radius(self):
        """
        Description: Get the radius of the robot itself.
        Returns:
        - float: The radius of the robot itself.
        """
        pass

    def get_surrounding_environment_info(self):
        """
        Get real-time information of the surrounding robots and obstacles within the perception range.
        Returns:
        - list: A list of dictionaries, each containing the type, position, and other relevant information of surrounding objects (robots or obstacles).
            - "Type": A string indicating whether the object is a 'robot' or 'obstacle'.
            - "position": The current position of the object.
            - "velocity": The current velocity of the object. If the object is an obstacle, the velocity is [0, 0].
            - "radius": The radius of the object.
        """
        pass

    def get_environment_range(self):
        """
        Description: Get the x and y range of the environment.
        Returns:
        - dict: A dictionary containing the x and y range of the environment.Robot should keep within the range.
            - x_min (float): The minimum x value of the environment.
            - x_max (float): The maximum x value of the environment.
            - y_min (float): The minimum y value of the environment.
            - y_max (float): The maximum y value of the environment.
        """

    def get_prey_position(self):
        """
        Description: Prey will keep moving in the environment.Get the real-time position of the prey in the environment.
        Returns:
        - numpy.ndarray: The position of the prey.
        """
        pass

    def get_prey_initial_position(self):
        """
        Description: Get the initial position of the prey.Prey will move in the environment.
        Note: The prey will move in the environment, and the position will be updated in real-time.So your policy should consider the dynamic position of the prey.
        Returns:
        - list: A list of float, representing the initial position of the prey.
        """
        pass

    def stop_self(self):
        """
        Description: Stop the robot itself.
        """
        pass

    def get_self_velocity(self):
        """
        Get the current velocity of the robot itself in real-time.
        Returns:
        - numpy.ndarray: The current, real-time velocity of the robot.
        """
        pass
    def get_initial_unexplored_areas(self):
        """
        Description: Get the initial unexplored areas in the environment.
        Returns:
        - list: A list of numpy.ndarray, all representing the initial unexplored areas.
        """
        pass

    def get_quadrant_target_position(self):
        """
        Description: Get the target position of the robot in the designated quadrant.
        Returns:
        - numpy.ndarray: The target position of the robot in the designated quadrant.
        """
        pass
    def get_lead_position(self):
        """
        Description: Get the current position of the lead robot.
        Returns:
        - numpy.ndarray: The current position of the lead robot.
        """
        pass


prompt_multi_robots = '''
# Python 2D multi-robots control
## These are the environment description:
Environment:
    Environment is composed of a 2D plane with obstacles and robots.
    The robots and obstacles in the space are circular, and the avoidance algorithm is the same for both.
    There are only static obstacles and other robots in the environment.
Robot:
    max_speed: 0.2m/s (constant)
    Control Method: Omnidirectional speed control(The output after velocity-weighted superposition of different objectives.)
    Control frequency: 100Hz (the robot's velocity should be updated at least every 0.01s)
    Initial position: random position in the environment
    Initial speed: np.array([0, 0])
    Min distance to other object: > self.radius +obj.radius + distance_threshold (Depending on the specific task, prioritize completing the task correctly before minimizing the collision probability.)
    position_resolution: 0.05m (The threshold for considering the robot as having reached a designated position is greater than position_resolution.)
## These APIs can be directly called by you.
from api import ...
{api}

## Robot needs to complete the user provided task.
## Notes: 
- In order to improve the quality of the generated code, only the main function is generated. This function contains several specific functions, each responsible for implementing a particular task. However, please note that you are not allowed to generate these specific function implementations at this stage, as they will be generated by other agents separately.
- Directly complete the following content based on the given task requirements and provided APIs.
- The main function should be concise, obtaining information through API calls. However, all information processing and logic should be implemented in specific functions. The main function should only contain calls to these functions and no other logic.

Here is some example code:
instruction:The robots need to explore all the unknown areas. You are required to assign an optimal sequence of exploration areas to each robot based on the number of robots and the unexplored regions, and then the robots will gradually explore these areas.
code:
```python
def main():
    # Get the necessary information using provided APIs
    robot_id = get_self_id()
    all_robot_ids = get_all_robots_id()
    unexplored_areas = get_initial_unexplored_areas()
    environment_range = get_environment_range()
    initial_positions = get_all_robots_initial_position()
    
    # Assign exploration tasks to this robot
    assigned_areas = assign_exploration_tasks(robot_id, all_robot_ids, unexplored_areas)

    for area in assigned_areas:
        while not has_reached_exploration_area(area):
            current_position = get_self_position()
            surrounding_info = get_surrounding_environment_info()
            next_velocity = calculate_velocity_to_explore(current_position, area, surrounding_info)

            # Set the calculated velocity
            set_self_velocity(next_velocity)
            
    # Once all assigned areas are explored, stop the robot
    stop_self()
```
    
instruction:Robots with initial positions in the same quadrant need to cluster in the designated area of that corresponding quadrant.
code:
```python
def main():
    # Get the robot's ID and initial position
    robot_id = get_self_id()
    self_position = get_self_position()

    # Get all robot positions
    all_robot_positions = get_all_robots_initial_position()

    # Get the quadrant target positions
    quadrant_targets = get_quadrant_target_position()

    # Identify which quadrant the robot belongs to based on its initial position
    quadrant_index = get_quadrant_index(self_position)
    
    # Get the target position for the robot's corresponding quadrant
    target_position = quadrant_targets[quadrant_index]
    
    # Get surrounding environment info (robots and obstacles)
    surrounding_info = get_surrounding_environment_info()
    
    # Cluster robots in the designated area of the corresponding quadrant
    cluster_robots_in_quadrant(all_robot_positions, surrounding_info, target_position)
    

instruction:{instruction}
code:
'''.strip()


prompt_fgen = '''
# Python 2D multi-robots control
# Python 2D multi-robots control
## These are the environment description:
Environment:
    Environment is composed of a 2D plane with obstacles and robots.
    The robots and obstacles in the space are circular, and the avoidance algorithm is the same for both.
    There are only static obstacles and other robots in the environment.
Robot:
    max_speed: 0.2m/s (constant)
    Control Method: Omnidirectional speed control(The output after velocity-weighted superposition of different objectives.)
    Control frequency: 100Hz (the robot's velocity should be updated at least every 0.01s)
    Initial position: random position in the environment
    Initial speed: np.array([0, 0])
    Min distance to other object: > self.radius +obj.radius + distance_threshold (Depending on the specific task, prioritize completing the task correctly before minimizing the collision probability.)
    position_resolution: 0.05m (The threshold for considering the robot as having reached a designated position is greater than position_resolution.)
## These APIs can be directly called by you.
from api import ...
{api}
Generate the function bodies for the specified functions based on the given function signatures.
function signatures: {function_signature}
Note: 
- only generate the desired function,not allowed to generate other functions.
 
output format:
```python
def function_name(input1, input2, ...):
    """
    Description: Brief description of the function.
    Input:
    - input1 (input1_type): Description of input1.
    - input2 (input2_type): Description of input2.
    ...
    Returns:
    - output (output_type): Description of the output.
    """
    (Put your code here)
'''

# 各个agent的配置
cfg_multi_robot = {
    'lmps': {
        'multi_robot_ui': {
            'prompt_text': prompt_multi_robots,
            'engine': model_name,
            'max_tokens': 10000,
            'temperature': 1,
            'query_prefix': '# ',
            'query_suffix': '.',
            'stop': ['#', 'objects = ['],
            'maintain_session': True,
            'debug_mode': False,
            'include_context': True,
            'has_return': False,
            'return_val_name': 'ret_val',
        },

        'fgen': {
            'prompt_text': prompt_fgen,
            'engine': model_name,
            'max_tokens': 5120,
            'temperature': 0,
            'query_prefix': '# define function: ',
            'query_suffix': '.',
            'stop': ['# define', '# example'],
            'maintain_session': False,
            'debug_mode': False,
            'include_context': True,
        }
    }
}


def setup_LMP(cfg_multi_robot, task_name):
    # LMP env wrapper
    cfg_multi_robot = copy.deepcopy(cfg_multi_robot)
    LMP_env = LMP_wrapper()
    # creating APIs that the LMPs can interact with
    fixed_vars = {
        'np': np
    }

    api_list = robot_api.get_api_prompt(task_name, only_names=True)
    variable_vars = {
        k: getattr(LMP_env, k)
        for k in api_list
    }

    lmp_fgen = LMPFGen(cfg_multi_robot['lmps']['fgen'], fixed_vars, variable_vars)

    lmp_multi_robot_ui = LMP(
        'multi_robot_ui', cfg_multi_robot['lmps']['multi_robot_ui'], lmp_fgen, fixed_vars, variable_vars
    )

    return lmp_multi_robot_ui


from swarm_prompt.prompt_swarm_robot import UserRequirement, task_name

lmp_multi_robot_ui = setup_LMP(cfg_multi_robot=cfg_multi_robot, task_name=task_name)

user_input = UserRequirement

lmp_multi_robot_ui(user_input)
