import logging
import os
import sys

import kegapi.exceptions as exceptions


_g_logger = logging.getLogger(__name__)


class StateMachine(object):

    def __init__(self):
        self._state_map = {}
        self._user_callbacks_list = []
        self._event_list = []

    def add_transition(self, state_event, event, new_state, func):
        if state_event not in self._state_map:
            self._state_map[state_event] = {}
        self._state_map[state_event][event] = (new_state, func)

    def mapping_to_digraph(self, outf=None):
        if outf is None:
            outf = sys.stdout
        outf.write('digraph {' + os.linesep)
        outf.write('node [shape=circle, style=filled, fillcolor=gray, '
                   'fixedsize=true, fontsize=11, width=1.5];')
        for start_state in self._state_map:
            for event in self._state_map[start_state]:
                ent = self._state_map[start_state][event]
                if ent is not None:
                    outf.write('%s  -> %s [label=" %s ", fontsize=11];'
                               % (start_state, ent[0], event) + os.linesep)
        outf.write('}' + os.linesep)
        outf.flush()

    def event_occurred(self, event, db_obj, **kwargs):
        try:
            old_state = db_obj.state
            _g_logger.info(f"Event {event} occurred in state {old_state}")
            _g_logger.info(f"keys  {self._state_map.keys()}")

            new_state, func = self._state_map[old_state][event]
            # a logging adapter is added so that me can configure more of the
            # log line in a conf file
            log_msg = ("Event %(event)s occurred.  Moving from state "
                       "%(old_state)s to %(new_state)s") % locals()
            _g_logger.info(log_msg)
            self._event_list.append((event, old_state, new_state))
            try:
                if func is not None:
                    _g_logger.debug("Calling %s | %s" % (func.__name__, func.__doc__))
                    func(db_obj, **kwargs)
                db_obj.state = new_state
                db_obj.save()
                _g_logger.info("Moved to new state %s." % new_state)
            except Exception as ex:
                _g_logger.exception(f"An exception occurred {str(ex)}")
                raise
        except KeyError as keyEx:
            raise exceptions.StateTransitionException(old_state, event)
