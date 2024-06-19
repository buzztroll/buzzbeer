import logging
import random
import threading

from kegapi import sm

# import hx711

_g_logger = logging.getLogger(__name__)


class ScaleSourceBase(object):
    def zero(self):
        raise Exception("Not implemented")

    def set_known_weight(self, w):
        raise Exception("Not implemented")

    def get_weight(self):
        raise Exception("Not implemented")

    def get_zero_offset(self):
        raise Exception("Not implemented")


class TestScale(object):
    def zero(self):
        pass

    def set_known_weight(self, w):
        return 51015.9

    def get_weight(self):
        return random.uniform(5000.5, 5100.9)

    def get_zero_offset(self):
        return 5015.9

#
#
# class GandolfScale(ScaleSourceBase):
#     def __init__(self, data_pin, clock_pin, read_iterations=7):
#         self._data_pin = data_pin
#         self._clock_pin = clock_pin
#         self._read_iterations = read_iterations
#         self.hx = hx711.HX711(dout_pin=self._data_pin,
#                               pd_sck_pin=self._clock_pin)
#
#     def zero(self):
#         err = self.hx.zero()
#         if err:
#             raise ValueError('Tare is unsuccessful.')
#
#     def set_known_weight(self, w):
#         reading = self.hx.get_data_mean()
#         ratio = reading / w
#         self.hx.set_scale_ratio(ratio)
#         return reading
#
#     def get_weight(self):
#         return self.hx.get_weight_mean(self._read_iterations)


class ScaleManager(object):
    def __init__(self, scale_src,
                 ready_callback, ready_callback_args,
                 read_interval=1.0,
                 reads_per_interval=3):
        self._scale_src = scale_src
        self._reads_per_interval = reads_per_interval
        self._ready_callback = ready_callback
        self._ready_callback_args = ready_callback_args
        self._read_interval = read_interval
        self._thread = None
        self._lock = threading.Lock()
        self._cond = threading.Condition()
        self._running = False
        self.full_weight = None
        self.sm = sm.StateMachine()

        # zero the scale
    def zero(self):
        self._lock.acquire()
        try:
            self._scale_src.zero()
        finally:
            self._lock.release()

    # figure out the calibration factor
    def known_weight(self, value):
        self._lock.acquire()
        try:
            return self._scale_src.set_known_weight(value)
        finally:
            self._lock.release()

    # starting a new full keg. get the weight and start subtracting
    def new_full(self):
        self._lock.acquire()
        try:
            # TODO: what do i do with this value?
            self.full_weight = self._scale_src.get_weight()
        finally:
            self._lock.release()

    # start sending in new values
    def start(self):
        self._lock.acquire()
        try:
            if self._running:
                raise Exception("it is already running")
            self._thread = threading.Thread(self._run, name="scaler_reader")
            self._running = True
            self._thread.start()
        finally:
            self._lock.release()

    def get_zero_offset(self):
        return self._scale_src.get_zero_offset()

    def stop(self):
        self._lock.acquire()
        try:
            if not self._running:
                raise Exception("it is not running")
            self._running = False
            self._cond.notify()
        finally:
            self._lock.release()
        self._thread.join()

    def _run(self):
        self._lock.acquire()
        try:
            while self._running:
                weight = self._scale_src.get_weight()

                self._lock.release()
                try:
                    self._ready_callback(weight, **self._ready_callback_args)
                except Exception as ex:
                    _g_logger.exception(f"Runner failed: {str(ex)}")
                finally:
                    self._lock.acquire()
                self._cond.wait(timeout=self._read_interval)
        except Exception as ex:
            _g_logger.exception(f"Runner failed: {str(ex)}")
        finally:
            self._lock.release()
