#!/usr/bin/env python3
import random, math
import time
import logging
from aux import Vector2D


class Vector2D:
    """A two-dimensional vector with Cartesian coordinates."""

    def __init__(self, x=0, y=0, polar=False, degrees=False):

        self.x = x
        self.y = y

        if isinstance(x, (Vector2D, list, tuple)) and not y:
            self.x = x[0]
            self.y = x[1]

        if degrees:
            y = math.radians(y)

        if polar:
            self.x = x * math.cos(y)
            self.y = x * math.sin(y)

        self.length = self.__abs__()
        self.angle = math.atan2(self.y, self.x)

    def __str__(self):
        """Human-readable string representation of the vector."""
        return '{:g}i + {:g}j'.format(self.x, self.y)

    def __repr__(self):
        """Unambiguous string representation of the vector."""
        return repr((self.x, self.y))

    def dot(self, other):
        """The scalar (dot) product of self and other. Both must be vectors."""

        if not isinstance(other, Vector2D):
            raise TypeError('Can only take dot product of two Vector2D objects')
        return self.x * other.x + self.y * other.y

    # Alias the __matmul__ method to dot so we can use a @ b as well as a.dot(b).
    __matmul__ = dot

    def cross(self, other):
        """The vector (cross) product of self and other. Both must be vectors."""

        if not isinstance(other, Vector2D):
            raise TypeError('Can only take cross product of two Vector2D objects')
        return abs(self) * abs(other) * math.sin(self - other)

    # Alias the __matmul__ method to dot so we can use a @ b as well as a.dot(b).
    __matmul__ = cross

    def __sub__(self, other):
        """Vector subtraction."""
        return Vector2D(self.x - other.x, self.y - other.y)

    def __add__(self, other):
        """Vector addition."""
        return Vector2D(self.x + other.x, self.y + other.y)

    def __radd__(self, other):
        """Recursive vector addition."""
        return Vector2D(self.x + other.x, self.y + other.y)

    def __mul__(self, scalar):
        """Multiplication of a vector by a scalar."""

        if isinstance(scalar, int) or isinstance(scalar, float):
            return Vector2D(self.x * scalar, self.y * scalar)
        raise NotImplementedError('Can only multiply Vector2D by a scalar')

    def __rmul__(self, scalar):
        """Reflected multiplication so vector * scalar also works."""
        return self.__mul__(scalar)

    def __neg__(self):
        """Negation of the vector (invert through origin.)"""
        return Vector2D(-self.x, -self.y)

    def __truediv__(self, scalar):
        """True division of the vector by a scalar."""
        return Vector2D(self.x / scalar, self.y / scalar)

    def __mod__(self, scalar):
        """One way to implement modulus operation: for each component."""
        return Vector2D(self.x % scalar, self.y % scalar)

    def __abs__(self):
        """Absolute value (magnitude) of the vector."""
        return math.sqrt(self.x ** 2 + self.y ** 2)

    def __round__(self, decimals):
        """Round the vector2D x and y"""
        return Vector2D(round(self.x, decimals), round(self.y, decimals))

    def __iter__(self):
        """Return the iterable object"""
        for i in [self.x, self.y]:
            yield i

    def __getitem__(self, index):
        """Return the iterable object"""
        if index == 0 or index == 'x':
            return self.x
        elif index == 1 or index == 'y':
            return self.y
        raise NotImplementedError('Vector2D is two-dimensional array (x,y)')

    def rotate(self, angle, degrees=False):
        if degrees:
            angle = math.radians(angle)

        return Vector2D(self.length, self.angle + angle, polar=True)

    def normalize(self):
        """Normalized vector"""
        if self.x == 0 and self.y == 0:
            return self
        else:
            return Vector2D(self.x / abs(self), self.y / abs(self))

    def distance_to(self, other):
        """The distance between vectors self and other."""
        return abs(self - other)

    def to_polar(self):
        """Return the vector's components in polar coordinates."""
        return self.length, self.angle


class RandomWalk(object):
    """ Set up a Flocking loop on a background thread
    The __flocking() method will be started and it will run in the background
    until the application exits.
    """

    def __init__(self, robot, MAX_SPEED):
        """ Constructor
        :type range: int
        :param enode: Flocking speed (tip: 500)
        """
        self.__stop = 1
        self.__flock = True
        self._id = str(int(robot.variables.get_id()[2:]))
        self.__distance_to_target = None
        self.__distance_traveled = 0

        # General Parameters
        self.robot = robot
        self.MAX_SPEED = MAX_SPEED

        # Navigation parameters
        self.Kp = 5  # Proportional gain

        # Obstacle avoidance parameters
        self.thresh_ir = 0

        # Flocking parameters
        self.flock_range = 1  # Communication range for flocking
        self.alpha = 10.0  # Attraction force
        self.beta = 5.0  # Repulsion force
        self.gamma = 1.0  # Alignment force

    def step(self):
        """ This method runs in the background until program is closed """

        if self.__flock:
            # Compute Flocking
            vx, vy = self.flock()

            # Avoid Obstacles
            vx, vy = self.avoid_argos3_example(vx, vy)

            # Saturate wheel actuators
            vx, vy = self.saturate(vx, vy)

            # Set wheel speeds
            self.robot.omni_wheels.set_speed(vx, vy)

    def flock(self):
        # We will use vectors to accumulate the forces for flocking
        cohesion_force = Vector2D(0, 0)
        separation_force = Vector2D(0, 0)
        alignment_force = Vector2D(0, 0)
        strength = 0

        readings = self.robot.omni_proximity.get_readings()

        neighbors = []  # List to hold the positions of neighbors

        for reading in readings:
            angle = reading.angle  # Correctly access the angle
            distance = reading.value  # Correctly access the distance
            # Check if the other robot is within flocking range
            if distance < self.flock_range:
                vec = Vector2D(
                    math.cos(angle) * distance, math.sin(angle) * distance)
                neighbors.append(vec)

                # Compute cohesion force (move towards the average position)
                cohesion_force += vec

                # Compute separation force (move away from very close neighbors)
                if distance < 0.35:  # Consider neighbors that are very close
                    separation_force -= vec / (distance + 1e-5)

                # Compute alignment force (align velocity with neighbors)
                alignment_force += Vector2D(
                    math.cos(angle), math.sin(angle))
                strength += 1

        if strength > 0:
            cohesion_force /= strength
            alignment_force /= strength

            # Combine all forces
            resultant_force = self.alpha * cohesion_force + \
                              self.beta * separation_force + self.gamma * alignment_force

            D = resultant_force.normalize()
            return D.x * self.MAX_SPEED, D.y * self.MAX_SPEED

        # If no neighbors, move straight ahead
        return 0, self.MAX_SPEED / 2

    def avoid_argos3_example(self, vx, vy):
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

        return vx, vy

    def saturate(self, vx, vy, style=1):
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

    def setFlock(self, state):
        """ This method is called set the flocking behavior to on without disabling I2C"""
        self.__flock = state

    def setLEDs(self, state):
        """ This method is called set the outer LEDs to an 8-bit state """
        if self.__LEDState != state:
            self.__isLEDset = False
            self.__LEDState = state

    def getIr(self):
        """ This method returns the IR readings """
        return self.ir

    def start(self):
        pass

    def stop(self):
        pass
