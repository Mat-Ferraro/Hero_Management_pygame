def lerp(start, end, t):
    t = max(0.0, min(1.0, t))
    return start + (end - start) * t


def lerp_color(start, end, t):
    return tuple(int(lerp(a, b, t)) for a, b in zip(start, end))


class Timer:
    def __init__(self, duration):
        self.duration = max(0.001, duration)
        self.elapsed = 0.0

    def reset(self):
        self.elapsed = 0.0

    def update(self, dt):
        self.elapsed = min(self.duration, self.elapsed + dt)

    def progress(self):
        return max(0.0, min(1.0, self.elapsed / self.duration))

    def done(self):
        return self.elapsed >= self.duration