"""DC operating points for TandEx's diode, resistor, and current-source circuits."""

import math

import numpy as np
from scipy.optimize import brentq

# Match the original SPICE temperature and DC junction conductance.
SPICE_VT = 1.380649e-23 * 300.15 / 1.602176634e-19
GMIN = 1e-12


def _diode_current(voltage, saturation, ideality):
    exponent = voltage / (SPICE_VT * ideality)
    if exponent < -3:
        current = -saturation * (1 + (3 / (exponent * math.e)) ** 3)
    else:
        current = saturation * math.expm1(min(exponent, 600))
    return current + GMIN * voltage


def _pvk_current(voltage, cell):
    photo, shunt, ideal, defect, defect_resistance, recombination = cell
    current = photo + voltage / shunt + _diode_current(voltage, ideal, 1)
    if recombination > 0:
        current += _diode_current(voltage, recombination, 2)
    if defect > 0:
        if voltage and defect_resistance > 0:
            # The voltage is divided between the defect diode and its series resistor.
            diode_voltage = brentq(
                lambda v: v + defect_resistance * _diode_current(v, defect, 1) - voltage,
                min(voltage, 0), max(voltage, 0), xtol=1e-13,
            )
        else:
            diode_voltage = voltage
        current += _diode_current(diode_voltage, defect, 1)
    return current


def _si_current(voltage, cell):
    photo, shunt, ideal, auger, defect, defect_ideality = cell
    return (photo + voltage / shunt + _diode_current(voltage, ideal, 1)
            + _diode_current(voltage, auger, 2 / 3)
            + _diode_current(voltage, defect, defect_ideality))


def _operating_point(residual, center):
    span = 1.0
    for _ in range(24):
        lo, hi = center - span, center + span
        if residual(lo) <= 0 <= residual(hi):
            return brentq(residual, lo, hi, xtol=1e-13)
        span *= 2
    raise ValueError('无法确定电路工作点，请检查输入参数。')


def _sweep(current_at_voltage, resistance, area, voltages):
    def load_current(voltage):
        if resistance <= 0:
            return current_at_voltage(voltage)
        # Terminal voltage equals junction voltage plus the series resistor drop.
        internal = _operating_point(
            lambda v: v + resistance * current_at_voltage(v) - voltage, voltage,
        )
        return current_at_voltage(internal)

    voltages = np.asarray(voltages, dtype=float)
    # Match the original VLOAD branch direction, opposite to junction current.
    currents = np.array([-load_current(float(v)) / area for v in voltages])
    return voltages, currents


def simulate_circuit(top_cell, bottom_cell, Rser, w, l, Vcell):
    area = w * l / 2

    def tandem_current(voltage):
        top_voltage = _operating_point(
            lambda v: _pvk_current(v, top_cell) - _si_current(voltage - v, bottom_cell),
            voltage / 2,
        )
        return _pvk_current(top_voltage, top_cell)

    return _sweep(tandem_current, Rser / area, area, Vcell)


def simulate_pvk_sj(top_cell, Rser, w, l, Vcell):
    area = w * l / 2
    photo, shunt, ideal, defect, _, recombination = top_cell
    if max(ideal, defect, recombination) < 1e-16:
        # Preserve the original high-bandgap branch and its 300 K temperature.
        voltage = np.asarray(Vcell, dtype=float)
        vt = 1.380649e-23 * 300 / 1.60217662e-19
        current = (photo + voltage / shunt
                   + (ideal + defect) * (np.exp(np.clip(voltage / vt, -120, 120)) - 1)
                   + recombination * (np.exp(np.clip(voltage / (2 * vt), -120, 120)) - 1))
        return voltage, current / area
    return _sweep(lambda v: _pvk_current(v, top_cell), Rser / area, area, Vcell)


def simulate_Si_sj(bottom_cell, Rser, w, l, Vcell):
    area = w * l / 2
    return _sweep(lambda v: _si_current(v, bottom_cell), Rser / area, area, Vcell)
