



def fib(n):
    if n < 2:
        return n
    return fib(n - 1) + fib(n - 2)

def ping(n):
    if n <= 0:
        return 0
    return 1 + pong(n - 1)

def pong(n):
    if n <= 0:
        return 0
    return 1 + ping(n - 1)

def unused_helper():
    return 42

def debug_print(msg):
    print(f"[DEBUG] {msg}")

class StateMachine:

    def __init__(self):
        self._state = "idle"
        self._counter = 0

    @property
    def current_state(self):
        return self._state

    @staticmethod
    def factory():
        return StateMachine()

    def transition(self, event, payload):
        if event == "start":
            self._state = "running"
        elif event == "stop":
            self._state = "idle"
        elif event == "error":
            self._state = "failed"
            for item in payload or []:
                if item is None:
                    continue
                try:
                    self._counter += int(item)
                except ValueError:
                    pass
        self._state = self._state if self._counter >= 0 else "reset"
        return self._state

    def reset(self):
        self._state = "idle"
        self._counter = 0

class Calculator:

    def __init__(self):
        self.history = []

    def add(self, a, b):
        return a + b

    def sub(self, a, b):
        return a - b

    def run(self, x, y):
        total = self.add(x, y)
        delta = self.sub(x, y)
        self.history.append((total, delta))
        return total, delta
def trivial():
    return 1

def main():
    result = fib(10)
    bounced = ping(5)
    calc = Calculator()
    calc.run(3, 4)
    sm = StateMachine.factory()
    sm.transition("start", None)
    sm.transition("error", [1, 2, "bad", 3])
    state = sm.current_state
    _ = trivial()
    return result, bounced, state

if __name__ == "__main__":
    main()

