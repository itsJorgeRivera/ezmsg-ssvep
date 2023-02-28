from dataclasses import dataclass

import panel
import ezmsg.core as ez

from ezmsg.sigproc.sampler import SampleTriggerMessage

from param.parameterized import Event

from .stimulus import RadialCheckerboard, Fixation

from typing import Optional

@dataclass(frozen = True)
class SSVEPStimSettingsMessage:
    size: int = 600

class SSVEPStimSettings(ez.Settings, SSVEPStimSettingsMessage):
    ...

class SSVEPStimState(ez.State):
    fixation: Fixation
    stim: Optional[RadialCheckerboard]
    stim_pane: panel.pane.HTML
    period: panel.widgets.FloatSlider
    radial_freq: panel.widgets.FloatSlider
    radial_exp: panel.widgets.FloatSlider
    angular_freq: panel.widgets.FloatSlider
    design_btn: panel.widgets.Button

class SSVEPStim(ez.Unit):
    STATE: SSVEPStimState

    OUTPUT_TRIGGER = ez.OutputStream(SampleTriggerMessage)

    def initialize(self) -> None:

        self.STATE.period = panel.widgets.FloatSlider(
            name = 'Reversal Period',
            value = 0.1,
            start = 0.01, 
            end = 0.2, 
            step = 0.01
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

        self.STATE.stim = None
        self.STATE.fixation = Fixation()
        self.STATE.stim_pane = panel.pane.HTML(self.STATE.fixation)

        self.STATE.design_btn = panel.widgets.Button(
            name = 'Design Stimulus'
        )

        def design_stimulus(*events: Event) -> None:

            self.STATE.stim = RadialCheckerboard(
                duration = self.STATE.period.value,
                radial_freq = self.STATE.radial_freq.value,
                radial_exp = self.STATE.radial_exp.value,
                angular_freq = self.STATE.angular_freq.value, 
                size = 600
            )

            self.STATE.stim_pane.object = self.STATE.stim

        self.STATE.design_btn.param.watch(design_stimulus, 'value')

    def panel(self) -> panel.viewable.Viewable:
        return panel.Row(
            panel.Column(
                self.STATE.period,
                self.STATE.radial_freq,
                self.STATE.radial_exp,
                self.STATE.angular_freq,
                self.STATE.design_btn,
            ),
            self.STATE.stim_pane,
        )





    