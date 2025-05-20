import numpy as np
import logging
from aux import Vector2D

class Robot:
    def __init__(self, id=0):
        self._id = id
        self.position = self.Position()
        self.epuck_wheels = self.EpuckWheels()
        self.epuck_proximity = self.ProximitySensor()
        self.variables = self.Variables(self._id)
        self.log = self.setup_logger()

    class Position:
        def __init__(self):
            self._pos = np.array([0.0, 0.0])
            self._orientation = 0.0  # In radians

        def get_position(self):
            return self._pos

        def get_orientation(self):
            return self._orientation

        def set_position(self, pos):
            self._pos = np.array(pos)

        def set_orientation(self, angle):
            self._orientation = angle

    class EpuckWheels:
        def set_speed(self, right, left):

    class ProximitySensor:
        def get_readings(self):
            # Returns a list of mocked proximity readings
            class Reading:
                def __init__(self, value, angle_deg):
                    self.value = value
                    self.angle = self.Angle(angle_deg)

                class Angle:
                    def __init__(self, value):
                        self._value = value
                    def value(self):
                        return self._value

            # Example: 8 sensors with dummy values
            return [
                Reading(value=np.random.uniform(0, 1), angle_deg=i * 45)
                for i in range(8)
            ]

    class Variables:
        def __init__(self, robot_id):
            self._vars = {"id": f"fb{robot_id}"}
        def get_id(self):
            return self._vars.get("id")
        def set_attribute(self, key, value):
            self._vars[key] = value
        def get_attribute(self, key):
            return self._vars.get(key)

    def setup_logger(self):
        logger = logging.getLogger(f"Robot{self._id}")
        if not logger.handlers:
            logger.setLevel(logging.DEBUG)
            handler = logging.StreamHandler()
            formatter = logging.Formatter('[%(levelname)s %(name)s] %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger
