import time


class Clock:
    init_game_time = 0
    init_real_time = 0

    def init_time(self, current_game_time):
        self.init_game_time = current_game_time
        self.init_real_time = int(time.time())

    def get_current_game_time(self):
        return self.init_game_time + (int(time.time()) - self.init_real_time)


clock = Clock()
