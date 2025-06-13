#!/usr/bin/env python3
import random, math
import time
import logging
from aux import Vector2D

class Navigate(object):
    """ Set up a Navigation loop on a background thread
    The __navigating() method will be started and it will run in the background
    until the application exits.
    """

    def __init__(self, robot, MAX_SPEED):
        """ Constructor
        :type range: int
        :param enode: Random-Walk speed (tip: 500)
        """
        self.robot = robot
        self._id = str(int(robot.variables.get_id()[2:]))

        # Internal variables
        self.__stop = False
        self.__walk = True
        self.__distance_to_target = 0
        self.__window = []
        self.__distance_traveled = 0
        self.__old_vec = 0
        self.__old_time = 0
        self.__accumulator_I = 0
        self.__accumulator_stuck = 0

        # Fixed Parameters
        self.MAX_SPEED = MAX_SPEED  # Maximum robot speed

        # Navigation parameters
        self.window_size = 10  # Avoid vector filtering

        # Obstacle avoidance parameters
        self.thresh_ir = 0

        # Vectorial obstacle avoidance parameters
        self.Ki = 0.1

    def update_state(self, target=[0, 0]):

        self.position = Vector2D(self.robot.position.get_position()[0:2])
        self.target = Vector2D(target)

    def navigate(self, target=[0, 0]):

        # Update the current position, orientation and target of the robot
        self.update_state(target=target)
        # Calculate the local frame vector to the desired target
        vec_target = self.target - self.position

        T = vec_target.normalize()

        # The desired vector (we only care about direction)
        D = T


        vx = D.x * self.MAX_SPEED
        vy = D.y * self.MAX_SPEED

        self.robot.omni_wheels.set_velocity(vx, vy)

        # Store the distance to arrive at target
        self.__distance_to_target = abs(vec_target)

    def navigate_with_obstacle_avoidance(self, target=[0, 0]):

        # Update the current position, orientation and target of the robot
        self.update_state(target=target)

        # Calculate the local frame vector to the desired target
        vec_target = self.target - self.position

        # Calculate the local frame vector to the avoid objects
        acc = Vector2D()
        prox_readings = self.robot.omni_proximity.get_readings()

        for reading in prox_readings:
            acc += Vector2D(reading.value, reading.angle.value(), polar=True)

        # Generate a time window to have smoother variations on the avoid vector
        self.__window.append(acc)
        if len(self.__window) > self.window_size:
            self.__window.pop(0)

        vec_avoid = (1 / self.window_size) * sum(self.__window, start=Vector2D())

        if abs(vec_avoid) < 0.01:
            self.__window = []

        # Normalize and weight to obtain desired control behavior
        T = 0.2 * vec_target.normalize()
        A = 0.5 * -vec_avoid  # .normalize()

        # # Saturate the avoid angle
        # if abs(A.angle) > math.radians(90):
        #     A = Vector2D(A.length, math.copysign(math.radians(90), A.angle), polar=True)

        # # Integral action on the avoid could make sense
        # def trapz(new_time, new_vec):
        #     trap = 0.5 * (new_vec + self.__old_vec)
        #     self.__accumulator_I += self.Ki * trap
        #     self.__old_vec = new_vec
        #     self.__old_time = new_time

        # trapz(time.time(), A.length)

        # if abs(A) < 0.01:
        #     self.__accumulator_I = 0

        # elif self.__accumulator_I > 1:
        #     self.__accumulator_I = 1

        # # Calculate the local frame vector to the desired motion (target + avoid)
        # A = A + self.__accumulator_I*A

        # The desired vector (we only care about direction)
        D = (T + A)

        # self.update_rays(T, A, D)

        vx = D.x * self.MAX_SPEED
        vy = D.y * self.MAX_SPEED

        self.robot.omni_wheels.set_velocity(vx, vy)

        # Store the distance to arrive at target
        self.__distance_to_target = abs(vec_target)

    def update_rays(self, T, A, D):
        # Change to global coordinates for the plotting

        self.robot.variables.set_attribute("rays", self._id
                                           + ', ' + repr(self.position)

                                           + '\n')

    def avoid(self, left=0, right=0, move=False):
        obstacle = False
        acc = Vector2D()

        # Obstacle avoidance
        readings = self.robot.omni_proximity.get_readings()
        self.ir = [reading.value for reading in readings]

        # Find Wheel Speed for Obstacle Avoidance
        for i, reading in enumerate(self.ir):
            if reading.value > self.thresh_ir:
                obstacle = True
                acc += Vector2D(
                    reading.value,
                    reading.angle.value(),
                    polar=True
                )
        if obstacle:
            avoid_vec = (-acc).normalize()
            vx = avoid_vec.x * self.MAX_SPEED
            vy = avoid_vec.y * self.MAX_SPEED

        if move:
            self.robot.omni_wheels.set_velocity(vx, vy)

        return vx, vy

    def avoid_static(self, vx=0, vy=0, move=False):
        # Update robot state (position, etc.), though not used here
        self.update_state()

        # Calculate global avoid vector from proximity sensor readings
        acc = Vector2D()
        prox_readings = self.robot.omni_proximity.get_readings()

        for reading in prox_readings:
            acc += Vector2D(reading.value, reading.angle.value(), polar=True)

        A = -acc.normalize()

        vx = A.x * self.MAX_SPEED
        vy = A.y * self.MAX_SPEED


        if move:
            self.robot.omni_wheels.set_velocity(vx, vy)

        return vx, vy

    def stop(self):
        robot.omni_wheels.set_velocity(0, 0)

    def set_wheels(self, vx, vy):
        robot.omni_wheels.set_velocity(vx, vy)

    def get_distance_to(self, to):

        # Update the current position, orientation and target of the robot
        self.update_state(target=to)

        # Return the distance to
        return abs(self.target - self.position )

    def saturate_velocity(self, vx, vy, style=1):
        speed = math.sqrt(vx ** 2 + vy ** 2)

        if style == 1:
            if vx > self.MAX_SPEED:
                vx = self.MAX_SPEED
            elif vx < -self.MAX_SPEED:
                vx = -self.MAX_SPEED

            if vy > self.MAX_SPEED:
                vy = self.MAX_SPEED
            elif vy < -self.MAX_SPEED:
                vy = -self.MAX_SPEED

        else:
            if speed > self.MAX_SPEED:
                scale = self.MAX_SPEED / speed
                vx *= scale
                vy *= scale

        return vx, vy
