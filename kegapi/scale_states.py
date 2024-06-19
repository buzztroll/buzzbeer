import enum
import logging
import threading

import kegapi.models as kegmodels
from kegapi import sm
import scale.scale as scale


_g_logger = logging.getLogger(__name__)


EVENT_REQUEST_ZERO = 1
EVENT_REQUEST_CALIBRATE = 2
EVENT_REQUEST_START = 3
EVENT_REQUEST_STOP = 4
EVENT_REQUEST_NEW_KEG = 5


class ScaleState(object):
    def __init__(self, scale_manager):
        self._scale_manager = scale_manager
        self._sm = sm.StateMachine()
        self._setup_states()

    def zero(self, db_scale):
        self._sm.event_occurred(EVENT_REQUEST_ZERO, db_obj=db_scale)
        return db_scale

    def calibrate(self, db_scale, known_weight):
        self._sm.event_occurred(EVENT_REQUEST_CALIBRATE, db_obj=db_scale, known_weight=known_weight)
        return db_scale

    def _sm_set_zero(self, db_scale_obj=None, **kwargs):
        err = self._scale_manager.zero()
        if err:
            raise Exception("Failed to zero the scale")
        zero_value = self._scale_manager.get_zero_offset()
        db_scale_obj.zero_offset = zero_value

    def _sm_calibrate(self, db_scale_obj=None, known_weight=None, **kwargs):
        db_scale_obj.known_weight_reading = self._scale_manager.known_weight(known_weight)
        db_scale_obj.known_weight = known_weight
        _g_logger.info(f"Known weight is {known_weight} and {db_scale_obj.known_weight_reading}")

    def _setup_states(self):
        self._sm.add_transition(kegmodels.SCALE_STATE_NONE, EVENT_REQUEST_ZERO,
                                kegmodels.SCALE_STATE_ZEROED, self._sm_set_zero)

        self._sm.add_transition(kegmodels.SCALE_STATE_ZEROED, EVENT_REQUEST_ZERO,
                                kegmodels.SCALE_STATE_ZEROED, self._sm_set_zero)
        self._sm.add_transition(kegmodels.SCALE_STATE_ZEROED, EVENT_REQUEST_CALIBRATE,
                                kegmodels.SCALE_STATE_CALIBRATED, self._sm_calibrate)

        self._sm.add_transition(kegmodels.SCALE_STATE_CALIBRATED, EVENT_REQUEST_CALIBRATE,
                                kegmodels.SCALE_STATE_CALIBRATED, self._sm_calibrate)
        self._sm.add_transition(kegmodels.SCALE_STATE_CALIBRATED, EVENT_REQUEST_ZERO,
                                kegmodels.SCALE_STATE_CALIBRATED, self._sm_set_zero)


_g_singleton_mutex = threading.RLock()
_g_scale_reader = None
_g_scale_manager = None
_g_scale_state_machine = None


def _weight_read(w, **kwarg):
    _g_logger.info(f"incoming weight {w}")


def get_scale_reader_singleton():
    global  _g_scale_reader

    _g_singleton_mutex.acquire()
    try:
        if _g_scale_reader is None:
            _g_scale_reader = scale.TestScale()

        return _g_scale_reader
    finally:
        _g_singleton_mutex.release()


def get_scale_manager_singleton():
    global _g_scale_manager

    _g_singleton_mutex.acquire()
    try:
        if _g_scale_manager is None:
            scale_reader = get_scale_reader_singleton()
            _g_scale_manager = scale.ScaleManager(
                scale_reader, _weight_read, {})
        return _g_scale_manager
    finally:
        _g_singleton_mutex.release()


def get_scale_sm_singleton():
    global _g_scale_state_machine

    _g_singleton_mutex.acquire()
    try:
        if _g_scale_state_machine is None:
            scale_mgr = get_scale_manager_singleton()
            _g_scale_state_machine = ScaleState(scale_mgr)
        return _g_scale_state_machine
    finally:
        _g_singleton_mutex.release()


