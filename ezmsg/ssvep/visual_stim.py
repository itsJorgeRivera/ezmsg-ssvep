from typing import AsyncGenerator, Optional, Sequence, List, Any
import ezmsg.core as ez

import numpy as np
import logging
import time
import math
import random
import os
import enum

from dataclasses import dataclass, field

from asyncio import Event

WHITE = np.array([1, 1, 1])
BLACK = np.array([-1, -1, -1])

class DartboardSections(enum.Enum):
    FULL = [(0, 360)]
    QUADRANTS = [(0,91),(90,181),(180,270),(270,360)]
    LEFTRIGHT = [(0,181), (180, 360)]
    TOPBOTTOM = [(90, 270), (90, -90)]

def make_dartboard(visual, win, color, degrees, ori=0):
    db = visual.RadialStim(win, tex='sqrXsqr', color=color, size=1,
            radialCycles=8, angularCycles=16, interpolate=False,
            visibleWedge=degrees, ori=ori)
    return db


def square(visual, win, color):
    rect = visual.Rect(win=win, width=0.1, height=0.1,
            pos=(-0.85, -0.5), fillColor=color, lineColor=None)
    return rect


def fixation_cross(visual, win):
    cross = visual.ShapeStim(win=win, size=(0.05, 0.05),
            vertices='cross', fillColor=WHITE, lineColor=WHITE)
    return cross


def wait(core, duration):
    clock = core.Clock()
    while True:
        if clock.getTime() > duration:
            break
    return


def generate_pseudorandom_order(pattern, amount):

    # Patterns should be presented pseudorandomly.
    # Each option should appear before the others are repeated so
    # that the distribution is even.

    angles = DartboardSections[pattern].value
    num_sequences = math.ceil(amount/len(angles))

    order = []
    for _ in range(num_sequences):
        order.extend(random.sample(angles, len(angles)))
    order = order[:amount]
    return order


def generate_pseudorandom_dartboards(visual, win, order):

    dartboards = []
    for angles in order:
        if angles == (90, -90):   # Corner case crosses the origin
            dartboards.append({
                "white": make_dartboard(visual, win, WHITE, (90, 270), ori=180),
                "black": make_dartboard(visual, win, BLACK, (90, 270), ori=180),
            })
        else:
            dartboards.append({
                "white": make_dartboard(visual, win, WHITE, angles),
                "black": make_dartboard(visual, win, BLACK, angles),
            })
    return dartboards


def generate_pseudorandom_intervals(isi_mean, isi_jitter, amount):
    intervals = []
    for _ in range(amount):
        variance = np.random.random() * isi_jitter * 2 - isi_jitter
        intervals.append(isi_mean + variance)
    return intervals

class ControlCommand(enum.Enum):
    START = enum.auto()
    STOP = enum.auto()
    CONFIG = enum.auto()
    REQUEST = enum.auto()
    RESPONSE = enum.auto()
    RESET = enum.auto()
    ENABLE = enum.auto()
    DISABLE = enum.auto()
    DIALOG = enum.auto()


@dataclass
class VisualStimMessage:
    command: ControlCommand
    flash_hz: Optional[int] = None
    num_flash_periods: Optional[int] = None
    num_reversals_per_flash_period: Optional[int] = None
    isi_mean: Optional[float] = None
    isi_jitter: Optional[float] = None
    pattern: Optional[str] = None



class VisualStimSettings(ez.Settings):
    flash_hz: int
    num_flash_periods: int
    num_reversals_per_flash_period: int
    isi_mean: float
    isi_jitter: float
    pattern: str
    XRES: int = 1920
    YRES: int = 1080

@dataclass
class VisualStimControl:
    command: ControlCommand
    patterns: Optional[list] = None

@dataclass
class StimTimestampsMessage:
    timestamps: List[float]
    metadata: Optional[any] = None


class VisualStimState(ez.State):
    flash_hz: int
    num_flash_periods: int
    num_reversals_per_flash_period: int
    isi_mean: float
    isi_jitter: float
    pattern: str
    run_experiment_ev: Event
    region_order: list


class VisualStim(ez.Unit):

    SETTINGS: VisualStimSettings
    STATE: VisualStimState

    CMD_INPUT = ez.InputStream(VisualStimMessage)
    CMD_OUTPUT = ez.OutputStream(VisualStimControl)
    TIMESTAMPS_OUTPUT = ez.OutputStream(StimTimestampsMessage)

    def initialize(self) -> None:

        os.environ["DISPLAY"] = ":0"
        self.STATE.flash_hz = self.SETTINGS.flash_hz
        self.STATE.num_flash_periods = self.SETTINGS.num_flash_periods
        self.STATE.num_reversals_per_flash_period = self.SETTINGS.num_reversals_per_flash_period
        self.STATE.isi_mean = self.SETTINGS.isi_mean
        self.STATE.isi_jitter = self.SETTINGS.isi_jitter
        self.STATE.pattern = self.SETTINGS.pattern
        self.STATE.run_experiment_ev = Event()
        self.STATE.region_order = generate_pseudorandom_order(self.STATE.pattern, self.STATE.num_flash_periods)

    @ez.subscriber(CMD_INPUT)
    @ez.publisher(CMD_OUTPUT)
    async def on_visual_stim_message(self, message: VisualStimMessage) -> AsyncGenerator:
        if isinstance(message, VisualStimMessage):
            if message.command == ControlCommand.START:
                self.STATE.run_experiment_ev.set()
            
            if message.command == ControlCommand.CONFIG:
                self.STATE.flash_hz = message.flash_hz
                self.STATE.num_flash_periods = message.num_flash_periods
                self.STATE.num_reversals_per_flash_period = message.num_reversals_per_flash_period
                self.STATE.isi_mean = message.isi_mean
                self.STATE.isi_jitter = message.isi_jitter
                self.STATE.pattern = message.pattern
                self.STATE.run_experiment_ev.clear()
                self.STATE.region_order = generate_pseudorandom_order(self.STATE.pattern, self.STATE.num_flash_periods)            
                yield self.CMD_OUTPUT, VisualStimControl(
                    command=ControlCommand.CONFIG, 
                    patterns=[val for val in self.STATE.region_order for _ in range(self.STATE.num_reversals_per_flash_period)]
                )

            elif message.command == ControlCommand.STOP:
                self.STATE.run_experiment_ev.clear()

    @ez.publisher(TIMESTAMPS_OUTPUT)
    @ez.publisher(CMD_OUTPUT)
    async def run_experiment(self) -> AsyncGenerator:

        from psychopy import core, visual

        # Psychopy return to the top each time it is stopped and wait for the asyncio.event to be set 
        # before beginning again
        yield self.CMD_OUTPUT, VisualStimControl(
            command=ControlCommand.CONFIG, 
            patterns=[val for val in self.STATE.region_order for _ in range(self.STATE.num_reversals_per_flash_period)]
        )

        while True:
            await self.STATE.run_experiment_ev.wait()


            # Pre-calculate all elements before experiment begins
            win = visual.Window(fullscr=True, units="height", winType = 'pyglet')
            win.clearBuffer()
            pd_black = square(visual, win, BLACK)
            pd_white = square(visual, win, WHITE)
            cross = fixation_cross(visual, win)
            dartboards = generate_pseudorandom_dartboards(visual, win, self.STATE.region_order)
            intervals = generate_pseudorandom_intervals(self.STATE.isi_mean, self.STATE.isi_jitter, len(dartboards))

            # Draw initial state
            pd_black.draw()
            cross.draw()
            win.flip()
            stim = dartboards[0]["black"]
            FLASH_DURATION = 1 / self.STATE.flash_hz * 2 # In seconds. Multiply by 2 to represent 2 reversals

            # Draw each dartboard as calculated by generate_pseudorandom_dartboards() above. 
            for i, dartboard in enumerate(dartboards):
                globalClock = core.Clock()
                num_reversals = 0
                send_timestamp = False

                # This `while True:` will last through each flash period. A timestamp is sent when the
                # dartboard reverses color.
                while True:
                    t = globalClock.getTime()

                    if t % FLASH_DURATION < FLASH_DURATION / 2.0:
                        if np.array_equal(stim.color, BLACK):
                            num_reversals = num_reversals + 1
                            send_timestamp = True
                            if num_reversals > self.STATE.num_reversals_per_flash_period:
                                break
                        stim = dartboard["white"]
                        pd = pd_white
                    else:
                        if np.array_equal(stim.color, WHITE):
                            num_reversals = num_reversals + 1
                            send_timestamp = True
                            if num_reversals > self.STATE.num_reversals_per_flash_period:
                                break
                        stim = dartboard["black"]
                        pd = pd_black

                    stim.draw()
                    pd.draw()
                    cross.draw()
                    if send_timestamp:
                        now = time.time()
                        message = StimTimestampsMessage(
                            timestamps=[now],
                            metadata={
                                "angles": self.STATE.region_order[i], 
                                "color": "white" if np.array_equal(stim.color, WHITE) else "black"
                            }
                        )
                        yield self.TIMESTAMPS_OUTPUT, message
                        send_timestamp = False
                    win.flip()

                # At the end of each flash period, draw the initial state onto the screen and
                # check the asyncio.Event in case the stop button was pressed. If not, wait a
                # precalculated amount of time before beginning again
                pd.draw()
                cross.draw()
                win.flip()
                if not self.STATE.run_experiment_ev.is_set():
                    break
                core.wait(intervals[i])


            yield self.CMD_OUTPUT, VisualStimControl(command=ControlCommand.STOP)
            self.STATE.run_experiment_ev.clear()
    

if __name__ == '__main__':
    settings = VisualStimSettings(
        flash_hz = 10,
        num_flash_periods = 10,
        num_reversals_per_flash_period = 10,
        isi_mean = 5.0,
        isi_jitter = 1.0,
        pattern = 'LEFTRIGHT',
    )
    unit = VisualStim(settings)
    ez.run(unit)
