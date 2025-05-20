# from robot import MockRobot

from controller_examples.Navigate import Navigate
from controller_examples.RandomWalk import RandomWalk
import time
from robot import Robot

robot = Robot()

while 1:
    rw = RandomWalk(robot, 0.5)
    rw.step()
    time.sleep(0.1)
