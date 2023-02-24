import asyncio
from dataclasses import dataclass, replace

import panel
import scipy.stats

import numpy as np
import ezmsg.core as ez

from ezmsg.util.messages.axisarray import AxisArray

from ezmsg.sigproc.sampler import SampleMessage
from ezmsg.sigproc.spectral import Spectrum, SpectrumSettings
from ezmsg.panel.lineplot import LinePlot, LinePlotSettings, AxisScale

from param.parameterized import Event

from typing import AsyncGenerator, List


@dataclass(frozen = True)
class SpectralStatsSettingsMessage:
    time_axis: str
    integration_time: float

class SpectralStatsSettings(ez.Settings, SpectralStatsSettingsMessage):
    ...

class SpectralStatsState(ez.State):
    cur_settings: SpectralStatsSettingsMessage
    spect_null_queue: "asyncio.Queue[AxisArray]"
    spect_ssvep_queue: "asyncio.Queue[AxisArray]"
    spectra_null: List[AxisArray]
    spectra_ssvep: List[AxisArray]
    refresh_stats: asyncio.Event

class SpectralStatsCalc(ez.Unit):
    SETTINGS: SpectralStatsSettings
    STATE: SpectralStatsState

    INPUT_SETTINGS = ez.InputStream(SpectralStatsSettingsMessage)
    INPUT_SAMPLE = ez.InputStream(SampleMessage)

    OUTPUT_NULL_SIGNAL = ez.OutputStream(AxisArray)
    OUTPUT_SSVEP_SIGNAL = ez.OutputStream(AxisArray)

    INPUT_NULL_SPECTRUM = ez.InputStream(AxisArray)
    INPUT_SSVEP_SPECTRUM = ez.InputStream(AxisArray)

    OUTPUT_STATS = ez.OutputStream(AxisArray)

    INPUT_REFRESH = ez.InputStream(ez.Flag)
    INPUT_RESET = ez.InputStream(ez.Flag)

    def initialize(self) -> None:
        self.STATE.cur_settings = self.SETTINGS
        self.STATE.spect_null_queue = asyncio.Queue()
        self.STATE.spect_ssvep_queue = asyncio.Queue()
        self.STATE.refresh_stats = asyncio.Event()
        self.STATE.refresh_stats.clear()
        self.STATE.spectra_null = list()
        self.STATE.spectra_ssvep = list()

    @ez.subscriber(INPUT_SETTINGS)
    async def on_settings(self, msg: SpectralStatsSettingsMessage) -> None:
        self.cur_settings = msg

    @ez.subscriber(INPUT_SAMPLE)
    @ez.publisher(OUTPUT_NULL_SIGNAL)
    @ez.publisher(OUTPUT_SSVEP_SIGNAL)
    async def split_sample(self, msg: SampleMessage) -> AsyncGenerator:
        """ Each sample that comes into this unit is 
        expected to be zero-centered with respect to the 
        onset of a strobing period.  This coroutine splits
        the AxisArray into two periods; the pre-zero "null"
        period that corresponds to no strobing stimulus and 
        the post-zero strobing period; yielding these outputs on
        two separate outputs for spectral extraction and later 
        synchronization for statistics. 
        """

        if msg.trigger.period is None:
            ez.logger.info('Incoming sample has no period; discarding')
            return

        axis = msg.sample.get_axis(self.STATE.cur_settings.time_axis)
        axis_idx = msg.sample.get_axis_idx(self.STATE.cur_settings.time_axis)
        t = (np.arange(msg.sample.shape[axis_idx]) * axis.gain) + msg.trigger.period[0]
        t0_idx = np.argmin(np.abs(t)).item()
        n_samp = int( self.STATE.cur_settings.integration_time / axis.gain )
        null_data = msg.sample.data[(slice(None),) * axis_idx + (slice(t0_idx - n_samp, t0_idx),)]
        ssvep_data = msg.sample.data[(slice(None),) * axis_idx + (slice(t0_idx, t0_idx + n_samp),)]
        yield self.OUTPUT_NULL_SIGNAL, replace(msg.sample, data = null_data)
        yield self.OUTPUT_SSVEP_SIGNAL, replace(msg.sample, data = ssvep_data)

    @ez.subscriber(INPUT_NULL_SPECTRUM)
    async def on_null_spectrum(self, msg: AxisArray) -> None:
        """ Enqueue a new null spectrum """
        self.STATE.spect_null_queue.put_nowait(msg)

    @ez.subscriber(INPUT_SSVEP_SPECTRUM)
    async def on_ssvep_spectrum(self, msg: AxisArray) -> None:
        """ Enqueue a new SSVEP spectrum """
        self.STATE.spect_ssvep_queue.put_nowait(msg)

    @ez.subscriber(INPUT_RESET)
    async def on_reset(self, msg: ez.Flag) -> None:
        ez.logger.info( 'Resetting Spectral Statistics' )
        self.STATE.spectra_null.clear()
        self.STATE.spectra_ssvep.clear()
        self.STATE.refresh_stats.set()

    @ez.subscriber(INPUT_REFRESH)
    async def on_refresh(self, msg: ez.Flag) -> None:
        ez.logger.info('Forcing refresh of stats')
        self.STATE.refresh_stats.set()

    @ez.task
    async def synchronize_spectra(self) -> AsyncGenerator:
        """ Get incoming null and SSVEP spectra and update statistics """
        while True:
            self.STATE.spectra_null.append(await self.STATE.spect_null_queue.get())
            ez.logger.info( 'Got a null spectrum' )
            self.STATE.spectra_ssvep.append(await self.STATE.spect_ssvep_queue.get())
            ez.logger.info( 'Synchronized with ssvep spectrum' )
            self.STATE.refresh_stats.set()

    @ez.publisher(OUTPUT_STATS)
    async def update_stats(self) -> AsyncGenerator:
        while True:
            await self.STATE.refresh_stats.wait()
            ez.logger.info('Refreshing Statistics')
            self.STATE.refresh_stats.clear()
            diff = self.STATE.spectra_ssvep[-1].data - self.STATE.spectra_null[-1].data
            yield self.OUTPUT_STATS, replace(self.STATE.spectra_ssvep[-1], data = diff)


@dataclass(frozen = True)
class SpectralStatsControlsSettingsMessage:
    ...

class SpectralStatsControlsSettings(ez.Settings, SpectralStatsControlsSettingsMessage):
    ...

class SpectralStatsControlsState(ez.State):
    reset_btn: panel.widgets.Button
    reset_queue: "asyncio.Queue[ez.Flag]"
    refresh_btn: panel.widgets.Button
    refresh_queue: "asyncio.Queue[ez.Flag]"

class SpectralStatsControls(ez.Unit):
    SETTINGS: SpectralStatsControlsSettings
    STATE: SpectralStatsControlsState

    OUTPUT_RESET = ez.OutputStream(ez.Flag)
    OUTPUT_REFRESH = ez.OutputStream(ez.Flag)

    def initialize(self) -> None:

        self.STATE.refresh_queue = asyncio.Queue()
        self.STATE.refresh_btn = panel.widgets.Button(name = 'Update/Refresh Statistics')

        def on_refresh_btn(*events: Event) -> None:
            self.STATE.refresh_queue.put_nowait(ez.Flag())

        self.STATE.refresh_btn.param.watch(on_refresh_btn, 'value')

        self.STATE.reset_queue = asyncio.Queue()
        self.STATE.reset_btn = panel.widgets.Button(name = 'Reset')

        def on_reset_btn(*events: Event) -> None:
            self.STATE.reset_queue.put_nowait(ez.Flag())

        self.STATE.reset_btn.param.watch(on_reset_btn, 'value')

    @ez.publisher(OUTPUT_RESET)
    async def pub_reset(self) -> AsyncGenerator:
        while True:
            msg = await self.STATE.reset_queue.get()
            yield self.OUTPUT_RESET, msg

    @ez.publisher(OUTPUT_REFRESH)
    async def pub_refresh(self) -> AsyncGenerator:
        while True:
            msg = await self.STATE.refresh_queue.get()
            yield self.OUTPUT_REFRESH, msg

    @property
    def controls(self) -> panel.viewable.Viewable:
        return panel.Column(
            self.STATE.refresh_btn,
            self.STATE.reset_btn
        )


class SpectralStats(ez.Collection):

    SETTINGS: SpectralStatsSettings

    INPUT_SAMPLE = ez.InputStream(SampleMessage)
    INPUT_RESET = ez.InputStream(ez.Flag)
    INPUT_REFRESH = ez.InputStream(ez.Flag)

    CALC = SpectralStatsCalc()
    SPECT_NULL = Spectrum()
    SPECT_SSVEP = Spectrum()
    CONTROLS = SpectralStatsControls()
    PLOT = LinePlot()

    def configure(self) -> None:
        self.CALC.apply_settings(self.SETTINGS)
        spectrum_settings = SpectrumSettings(axis = 'time')
        self.SPECT_NULL.apply_settings(spectrum_settings)
        self.SPECT_SSVEP.apply_settings(spectrum_settings)
        self.CONTROLS.apply_settings(
            SpectralStatsControlsSettings(

            )
        )
        self.PLOT.apply_settings(
            LinePlotSettings(
                name = "Spectral Statistics",
                x_axis = 'freq', 
                x_axis_scale = AxisScale.LOG
            )
        )

    def network(self) -> ez.NetworkDefinition:
        return (
            (self.INPUT_SAMPLE, self.CALC.INPUT_SAMPLE),

            (self.CALC.OUTPUT_NULL_SIGNAL, self.SPECT_NULL.INPUT_SIGNAL),
            (self.CALC.OUTPUT_SSVEP_SIGNAL, self.SPECT_SSVEP.INPUT_SIGNAL),
            (self.SPECT_NULL.OUTPUT_SIGNAL, self.CALC.INPUT_NULL_SPECTRUM),
            (self.SPECT_SSVEP.OUTPUT_SIGNAL, self.CALC.INPUT_SSVEP_SPECTRUM),

            (self.INPUT_REFRESH, self.CALC.INPUT_REFRESH),
            (self.INPUT_RESET, self.CALC.INPUT_RESET),
            (self.CALC.OUTPUT_STATS, self.PLOT.INPUT_SIGNAL),
            (self.CONTROLS.OUTPUT_RESET, self.CALC.INPUT_RESET),
            (self.CONTROLS.OUTPUT_REFRESH, self.CALC.INPUT_REFRESH),
        )

    def panel(self) -> panel.viewable.Viewable:
        return panel.Row(
            self.PLOT.plot(),
            panel.Column(
                '__Line Plot Controls__',
                *self.PLOT.controls,
                '__Statistics Controls__',
                self.CONTROLS.controls
            )
        )