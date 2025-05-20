"""
Copyright (c) 2024 WindyLab of Westlake University, China
All rights reserved.

This software is provided "as is" without warranty of any kind, either
express or implied, including but not limited to the warranties of
merchantability, fitness for a particular purpose, or non-infringement.
In no event shall the authors or copyright holders be liable for any
claim, damages, or other liability, whether in an action of contract,
tort, or otherwise, arising from, out of, or in connection with the
software or the use or other dealings in the software.
"""

ENV_DES = """
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
""".strip()
