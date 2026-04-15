"""
Demo file — прогоняет ВСЕ фичи Call Graph одним файлом.

Checklist what to test in the webview toolbar:
  1. Открытие графа:         Ctrl+Shift+P → "IDE Navigator: Show Call Graph"
  2. Click-to-navigate:      Ctrl/Shift/Alt+Click или Double-Click по узлу
  3. Search:                 введи "fib" / "ping" / "state" — подсветка
  4. Reverse:                галка — стрелки call-рёбер перевернутся
  5. Group by class:         методы свернутся в свои классы, подпись "(N)"
  6. Calls / Contains:       раздельно скрываешь серые и красные пунктирные рёбра
  7. Unused (Phase 4):       галка — unused_helper / debug_print серые, opacity 0.4
  8. Cycles (Phase 4):       галка — fib (self-loop) и ping↔pong красные и толстые
  9. Depth:                  кликни узел + выбери 1..5 — N-hop neighborhood
 10. Cyclomatic (Phase 4):   наведи на transition() — tooltip "... · cyclomatic=8"
 11. Export (Phase 5):       dropdown → PNG/SVG (диалог сохранения), Mermaid/DOT (в буфер)
 12. History (Phase 5):      кликай узлы, жми ← → или Alt+←/Alt+→
 13. @property fix:          current_state попадает в граф и контейн-ребром к StateMachine
"""


# ── 1. Рекурсия (self-loop — Cycles должны покрасить красным) ───────────────
def fib(n):
    if n < 2:
        return n
    return fib(n - 1) + fib(n - 2)


# ── 2. Взаимная рекурсия (SCC из двух узлов — тоже красные рёбра) ───────────
def ping(n):
    if n <= 0:
        return 0
    return 1 + pong(n - 1)


def pong(n):
    if n <= 0:
        return 0
    return 1 + ping(n - 1)


# ── 3. Мёртвый код (Unused должен пометить серым) ──────────────────────────
def unused_helper():
    """Никто не зовёт — после включения Unused должна стать серой."""
    return 42


def debug_print(msg):
    """Тоже никем не вызывается."""
    print(f"[DEBUG] {msg}")


# ── 4. Класс с высокой цикломатической сложностью + @property ──────────────
class StateMachine:
    """Большой transition — тест cyclomatic + decorated_definition."""

    def __init__(self):
        self._state = "idle"
        self._counter = 0

    @property
    def current_state(self):
        """@property — должен попасть в граф после фикса decorated_definition."""
        return self._state

    @staticmethod
    def factory():
        """@staticmethod тоже должен попасть в граф."""
        return StateMachine()

    def transition(self, event, payload):
        """
        Цикломатическая сложность ~8: 1 + if + elif + elif + for + if + except + ternary.
        Наведи курсор на узел — tooltip покажет cyclomatic=8.
        """
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


# ── 5. Класс с внутренними вызовами (contains + call рёбра) ────────────────
class Calculator:

    def __init__(self):
        self.history = []

    def add(self, a, b):
        return a + b

    def sub(self, a, b):
        return a - b

    def run(self, x, y):
        """Вызывает add и sub — два call-ребра внутри класса."""
        total = self.add(x, y)
        delta = self.sub(x, y)
        self.history.append((total, delta))
        return total, delta


# ── 6. Трivial функция — cyclomatic=1, для контраста с transition ──────────
def trivial():
    return 1


# ── 7. Связующий main — call-рёбра к fib/ping/Calculator/StateMachine ──────
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
