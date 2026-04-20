class AlertFlashState:
    def __init__(self, cycles: int):
        self.remaining = max(0, int(cycles))
        self.on = False

    def next_color(self):
        if self.remaining <= 0:
            return None
        self.on = not self.on
        self.remaining -= 1
        return "#ff3b30" if self.on else "transparent"
