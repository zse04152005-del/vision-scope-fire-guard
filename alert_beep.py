class AlertBeepState:
    def __init__(self, beeps: int):
        self.remaining = max(0, int(beeps))

    def next_beep(self):
        if self.remaining <= 0:
            return None
        self.remaining -= 1
        return True
