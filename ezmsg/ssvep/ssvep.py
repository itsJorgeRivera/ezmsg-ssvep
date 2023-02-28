import random
import asyncio
from dataclasses import dataclass

import panel
import ezmsg.core as ez

from ezmsg.sigproc.sampler import SampleTriggerMessage
from bokeh.models.formatters import FuncTickFormatter

from param.parameterized import Event

from .stimulus import RadialCheckerboard, Fixation

from typing import Optional, AsyncGenerator, List, Tuple

@dataclass(frozen = True)
class SSVEPStimSettingsMessage:
    size: int = 600 # px

class SSVEPStimSettings(ez.Settings, SSVEPStimSettingsMessage):
    ...

class SSVEPStimState(ez.State):
    fixation: Fixation
    stim: Optional[RadialCheckerboard]
    stim_pane: panel.pane.HTML

    # Stim Design
    period: panel.widgets.FloatSlider
    radial_freq: panel.widgets.FloatSlider
    radial_exp: panel.widgets.FloatSlider
    angular_freq: panel.widgets.FloatSlider
    design_btn: panel.widgets.Button

    # Stimulus Presentation
    num_trials: panel.widgets.IntInput
    trial_dur: panel.widgets.FloatInput
    isi_range: panel.widgets.RangeSlider
    start_btn: panel.widgets.Button
    progress: panel.indicators.Progress

    start_ev: asyncio.Event


class SSVEPStim(ez.Unit):
    SETTINGS: SSVEPStimSettings
    STATE: SSVEPStimState

    OUTPUT_TRIGGER = ez.OutputStream(SampleTriggerMessage)

    def initialize(self) -> None:

        self.STATE.period = panel.widgets.FloatSlider(
            name = 'Reversal Frequency',
            value = 0.1,
            start = 0.01, 
            end = 0.2, 
            step = 0.01,
            format = FuncTickFormatter(
                code = "return (1.0 / tick).toFixed(2) + ' Hz';"
            )
        )

        self.STATE.radial_freq = panel.widgets.FloatSlider(
            name = 'Radial Checkers',
            value = 10.0,
            start = 2.0, 
            end = 40.0, 
            step = 1.0
        )

        self.STATE.radial_exp = panel.widgets.FloatSlider(
            name = 'Radial Exponent',
            value = 0.5,
            start = 0.0,
            end = 2.0,
            step = 0.1
        )

        self.STATE.angular_freq = panel.widgets.FloatSlider(
            name = 'Angular Checkers',
            value = 40.0,
            start = 2.0,
            end = 80.0,
            step = 2.0
        )

        self.design_stimulus()
        self.STATE.fixation = Fixation()
        self.STATE.stim_pane = panel.pane.HTML(
            self.STATE.fixation, 
            width = self.SETTINGS.size, 
            height = self.SETTINGS.size
        )

        self.STATE.design_btn = panel.widgets.Button(
            name = 'Design Stimulus'
        )

        def on_design_stimulus(*events: Event) -> None:
            self.design_stimulus()
            self.STATE.stim_pane.object = self.STATE.stim

        self.STATE.design_btn.param.watch(on_design_stimulus, 'value')

        self.STATE.num_trials = panel.widgets.IntInput(
            name = 'Number of Trials',
            value = 5,
            start = 0,
            step = 1
        )

        self.STATE.trial_dur = panel.widgets.FloatInput(
            name = 'Trial Duration (sec)',
            value = 2.0,
            step = 0.1,
            start = 0.0,
            end = 10.0
        )

        self.STATE.isi_range = panel.widgets.RangeSlider(
            value = (0.5, 1.5),
            name = 'Inter-stimulus Interval (sec)',
            start = 0.0,
            end = 4.0,
            step = 0.1,
        )

        self.STATE.start_btn = panel.widgets.Button(
            name = 'Start Experiment'
        )

        self.STATE.progress = panel.indicators.Progress(
            value = 0,
            sizing_mode = 'stretch_width'
        )

        self.STATE.start_ev = asyncio.Event()
        self.STATE.start_ev.clear()

        def on_start(*events: Event) -> None:
            self.STATE.start_ev.set()

        self.STATE.start_btn.param.watch(on_start, 'value')

    @property
    def controls(self) -> List[panel.widgets.Widget]:
        return [
            self.STATE.period,
            self.STATE.radial_freq,
            self.STATE.radial_exp,
            self.STATE.angular_freq,
            self.STATE.design_btn,
            self.STATE.num_trials,
            self.STATE.trial_dur,
            self.STATE.isi_range,
            self.STATE.start_btn,
        ]

    @ez.publisher(OUTPUT_TRIGGER)
    async def run_experiment(self) -> AsyncGenerator:
        while True:
            await self.STATE.start_ev.wait()
            self.STATE.start_ev.clear()

            try:
                for control in self.controls:
                    control.disabled = True
                
                n_trials: int = self.STATE.num_trials.value # type: ignore
                trial_dur: float = self.STATE.trial_dur.value # type: ignore
                isi_range: Tuple[float, float] = self.STATE.isi_range.value # type: ignore
                stim_freq = 1.0 / self.STATE.period.value # type: ignore

                # Pre-Trial Period
                self.STATE.stim_pane.object = self.STATE.fixation
                self.STATE.progress.max = n_trials
                self.STATE.progress.value = 0
                await asyncio.sleep(5.0)

                # Start Task

                for trial in range(n_trials):
                    # Baseline
                    await asyncio.sleep(trial_dur)

                    # Stim
                    self.STATE.stim_pane.object = self.STATE.stim
                    yield self.OUTPUT_TRIGGER, SampleTriggerMessage(
                        period = (-trial_dur, trial_dur),
                        value = stim_freq
                    )

                    await asyncio.sleep(trial_dur)

                    # ISI
                    self.STATE.stim_pane.object = self.STATE.fixation
                    self.STATE.progress.value = trial + 1
                    isi_per = random.uniform(*isi_range)
                    await asyncio.sleep(isi_per)

            finally:
                for control in self.controls:
                    control.disabled = False


    def design_stimulus(self) -> None:

        self.STATE.stim = RadialCheckerboard(
            duration = self.STATE.period.value, # type: ignore
            radial_freq = self.STATE.radial_freq.value, # type: ignore
            radial_exp = self.STATE.radial_exp.value, # type: ignore
            angular_freq = self.STATE.angular_freq.value, # type: ignore
            size = self.SETTINGS.size
        )

    def panel(self) -> panel.viewable.Viewable:
        return panel.Row(
            panel.Column(
                '__Design Stimulus__',
                self.STATE.period,
                self.STATE.radial_freq,
                self.STATE.radial_exp,
                self.STATE.angular_freq,
                self.STATE.design_btn,
                '__Stimulus Presentation__',
                self.STATE.num_trials,
                self.STATE.trial_dur,
                self.STATE.isi_range,
                self.STATE.start_btn,
                self.STATE.progress,
            ),
            self.STATE.stim_pane,
        )





    