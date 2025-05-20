#!/usr/bin/env python3
import random, math
import time
import logging
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
        self._id = str(int(robot.variables.get_id()[2:]) + 1)

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
        self.L = 0.053  # Distance between wheels
        self.R = 0.0205  # Wheel radius

        # Navigation parameters
        self.Kp = 50  # Angular velocity proportional gain
        self.window_size = 10  # Avoid vector filtering
        self.thresh = math.radians(70)  # Wait before moving
        self.thresh_front_collision = math.radians(15)  # Aggressive avoidance

        # Obstacle avoidance parameters
        self.thresh_ir = 0
        self.weights = 25 * [-10, -10, 0, 0, 0, 0, 10, 10]

        # Vectorial obstacle avoidance parameters
        self.Ki = 0.1

    def update_state(self, target=[0, 0]):

        self.position = Vector2D(self.robot.position.get_position()[0:2])
        self.orientation = self.robot.position.get_orientation()
        self.target = Vector2D(target)

    def navigate(self, target=[0, 0]):

        # Update the current position, orientation and target of the robot
        self.update_state(target=target)
        # Calculate the local frame vector to the desired target
        vec_target = (self.target - self.position).rotate(-self.orientation)

        T = vec_target.normalize()

        # The desired vector (we only care about direction)
        D = T

        self.update_rays(Vector2D(0, 0), Vector2D(0, 0), D)

        dotProduct = 0
        # The target angle is behind the robot, we just rotate, no forward motion
        if D.angle > self.thresh or D.angle < -self.thresh:
            dotProduct = 0

        # Else, we project the forward motion vector to the desired angle
        else:
            dotProduct = Vector2D(1, 0).dot(D.normalize())

        # The angular velocity component is the desired angle scaled linearly
        angularVelocity = self.Kp * D.angle

        # The final wheel speeds are computed combining the forward and angular velocities
        right = dotProduct * self.MAX_SPEED / 2 - angularVelocity * self.L
        left = dotProduct * self.MAX_SPEED / 2 + angularVelocity * self.L

        # Set wheel speeds
        self.robot.epuck_wheels.set_speed(right, left)

        # Store the distance to arrive at target
        self.__distance_to_target = abs(vec_target)

    def navigate_with_obstacle_avoidance(self, target=[0, 0]):

        # Update the current position, orientation and target of the robot
        self.update_state(target=target)

        # Calculate the local frame vector to the desired target
        vec_target = (self.target - self.position).rotate(-self.orientation)

        # Calculate the local frame vector to the avoid objects
        acc = Vector2D()
        prox_readings = self.robot.epuck_proximity.get_readings()

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

        # Saturate the avoid angle
        if abs(A.angle) > math.radians(90):
            A = Vector2D(A.length, math.copysign(math.radians(90), A.angle), polar=True)

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

        self.update_rays(T, A, D)

        dotProduct = 0
        # The target angle is behind the robot, we just rotate, no forward motion
        if D.angle > self.thresh or D.angle < -self.thresh:
            dotProduct = 0

        # Else, we project the forward motion vector to the desired angle
        else:
            dotProduct = Vector2D(1, 0).dot(D.normalize())

        # The angular velocity component is the desired angle scaled linearly
        angularVelocity = self.Kp * D.angle

        # The final wheel speeds are computed combining the forward and angular velocities
        right = dotProduct * self.MAX_SPEED / 2 - angularVelocity * self.L
        left = dotProduct * self.MAX_SPEED / 2 + angularVelocity * self.L

        # # Saturate wheel speeds
        # left, right = self.saturate(left, right)

        # # Aggressive avoidance for frontal collisions
        # if  vec_avoid.length > 0.01 and abs(vec_avoid.angle) < self.thresh_front_collision:
        #     print(math.degrees(vec_avoid.angle), "Front Collision")
        #     # left, right = self.avoid(left, right)

        # Set wheel speeds
        self.robot.epuck_wheels.set_speed(right, left)

        # Store the distance to arrive at target
        self.__distance_to_target = abs(vec_target)

    def update_rays(self, T, A, D):
        # Change to global coordinates for the plotting

        self.robot.variables.set_attribute("rays", self._id
                                           + ', ' + repr(self.position)
                                           + ', ' + repr(T.rotate(self.orientation))
                                           + ', ' + repr(A.rotate(self.orientation))
                                           + ', ' + repr(D.rotate(self.orientation))
                                           + '\n')

    def avoid(self, left=0, right=0, move=False):
        obstacle = False
        avoid_left = avoid_right = 0

        # Obstacle avoidance
        readings = self.robot.epuck_proximity.get_readings()
        self.ir = [reading.value for reading in readings]

        # Find Wheel Speed for Obstacle Avoidance
        for i, reading in enumerate(self.ir):
            if reading > self.thresh_ir:
                obstacle = True
                avoid_left += self.weights[i] * reading
                avoid_right -= self.weights[i] * reading

        if obstacle:
            left = self.MAX_SPEED / 2 + avoid_left
            right = self.MAX_SPEED / 2 + avoid_right

        if move:
            self.robot.epuck_wheels.set_speed(right, left)

        return left, right

    def avoid_static(self, left=0, right=0, move=False):

        # Update the current position, orientation and target of the robot
        self.update_state()

        # Calculate the local frame vector to the avoid objects
        acc = Vector2D()
        prox_readings = self.robot.epuck_proximity.get_readings()

        for reading in prox_readings:
            acc += Vector2D(reading.value, reading.angle.value(), polar=True)

        # Project the forward motion vector to the desired angle
        dotProduct = Vector2D(1, 0).dot(acc.normalize())

        # The angular velocity component is the desired angle scaled linearly
        angVelocity = self.Kp * acc.angle

        # The final wheel speeds are computed combining the forward and angular velocities
        right = dotProduct * self.MAX_SPEED / 2 - angVelocity * self.L
        left = dotProduct * self.MAX_SPEED / 2 + angVelocity * self.L

        if move:
            self.robot.epuck_wheels.set_speed(right, left)

        return left, right

    def stop(self):
        robot.epuck_wheels.set_speed(0, 0)

    def set_wheels(self, right, left):
        robot.epuck_wheels.set_speed(right, left)

    def get_distance_to(self, to):

        # Update the current position, orientation and target of the robot
        self.update_state(target=to)

        # Return the distance to
        return abs(self.target - self.position)

    def saturate(self, left, right, style=1):
        # Saturate Speeds greater than MAX_SPEED

        if style == 1:

            if left > self.MAX_SPEED:
                left = self.MAX_SPEED
            elif left < -self.MAX_SPEED:
                left = -self.MAX_SPEED

            if right > self.MAX_SPEED:
                right = self.MAX_SPEED
            elif right < -self.MAX_SPEED:
                right = -self.MAX_SPEED

        else:

            if abs(left) > self.MAX_SPEED or abs(right) > self.MAX_SPEED:
                left = left / max(abs(left), abs(right)) * self.MAX_SPEED
                right = right / max(abs(left), abs(right)) * self.MAX_SPEED

        return left, right
