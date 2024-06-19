
class StateTransitionException(Exception):
    def __init__(self, state, event):
        self.message = f"Cannot transition from {state} due to {event}"
        super(StateTransitionException, self).__init__(self.message)
