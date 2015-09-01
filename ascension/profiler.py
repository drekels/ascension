from util import Singleton
import datetime as dt
import logging
import pyglet


LOG = logging.getLogger(__name__)


SLOW_FRAME_MESSAGE = (
    "Last execution of '{profiler_label}' lasted {time_passed}, which is over the target "
    "{target_time} by {time_over}!"
)
REPORT_MESSAGES = [
    "PROFILER REPORT: {name}",
    "  {time_passed} passed since last report",
    "  {run_count} times ran",
    "  {max_time} max",
    "  {min_time} min",
    "  {average_time} average",
]
TIME_FORMAT = "{}s {:>3}ms {:>3}\xces"


def get_time_string(t):
    if not t:
        return "NO_VALUE"
    return TIME_FORMAT.format(t.seconds, t.microseconds / 1000, t.microseconds % 1000)


class ProfilerBlock(object):

    def __init__(self, name, targets=None, report_every=5):
        self.name = name
        self.targets = targets
        self.report_every = report_every
        self.start_time = None
        self.schedule_report()

    def reset_metrics(self):
        self.report_start = dt.datetime.now()
        self.count = 0
        self.average = None
        self.maximum = None
        self.minimum = None

    def schedule_report(self):
        self.reset_metrics()
        pyglet.clock.schedule_interval(self.report, self.report_every)


    def report(self, *args):
        report_end = dt.datetime.now()
        time_passed = get_time_string(report_end - self.report_start)
        max_time = get_time_string(self.maximum)
        min_time = get_time_string(self.minimum)
        average_time = get_time_string(self.average)
        for message in REPORT_MESSAGES:
            LOG.info(message.format(
                name=self.name, time_passed=time_passed, run_count=self.count,
                max_time=max_time, min_time=min_time, average_time=average_time
            ))
        self.report_start = dt.datetime.now()
        self.reset_metrics()

    def start(self):
        if self.start_time:
            raise KeyError(
                "Cannot start profiler '{}', it was not stopped since last call".format(self.name)
            )
        self.start_time = dt.datetime.now()

    def stop(self):
        if not self.start_time:
            raise KeyError(
                "Cannot start profiler '{}', it was not stopped since last call".format(self.name)
            )
        stop_time = dt.datetime.now()
        time_passed = stop_time - self.start_time
        self.start_time = None
        self.count += 1
        if self.count == 1:
            self.maximum = time_passed
            self.minimum = time_passed
            self.average = time_passed
        else:
            self.maximum = time_passed > self.maximum and time_passed or self.maximum
            self.minimum = time_passed < self.minimum and time_passed or self.minimum
            self.average += (time_passed - self.average) / self.count
        for log_level, target_time in self.targets:
            if time_passed > target_time:
                time_over = time_passed - target_time
                getattr(LOG, log_level.lower())(SLOW_FRAME_MESSAGE.format(
                    profiler_label=self.name, time_passed=get_time_string(time_passed),
                    time_over=get_time_string(time_over), target_time=get_time_string(target_time),
                ))
                break


class ProfilerManager(object):
    __metaclass__ = Singleton

    def __init__(self):
        self.profilers = {}

    def start_draw(self):
        loopend = dt.datetime.now()
        if hasattr(self, "loopstart"):
            self.record_loop()
        self.loopstart = loopend

    def add_profiler(self, profiler):
        if profiler.name in self.profilers:
            raise KeyError(
                "ProfilerManager already has a prfiler named '{}'".format(profiler.name)
            )

    def start(self, name, targets=None, report_every=5):
        if name not in self.profilers:
            self.profilers[name] = ProfilerBlock(name, targets=targets, report_every=report_every)
        self.profilers[name].start()

    def stop(self, name):
        if name not in self.profilers:
            raise KeyError("No such profiler '{}' to stop".format(name))
        self.profilers[name].stop()
