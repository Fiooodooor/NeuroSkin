"""Explicit assumption-only resource budget. No fabricated BOM pricing."""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class ElectronicsAssumptions:
    channels: int = 7
    samples_per_second: int = 500
    afe_power_mW_per_channel: float = 0.7
    mcu_active_power_mW: float = 9.0
    mcu_duty_cycle: float = .1
    transmission_bytes_per_sample: int = 16
    link_bytes_per_second: int = 100_000
    sensing_latency_ms: float = 2.0
    serial_latency_ms: float = .5
    voltage_V: float = 3.3


def estimate_budget(assumptions: ElectronicsAssumptions = ElectronicsAssumptions()):
    a = assumptions
    if a.channels < 1 or a.samples_per_second < 1 or a.voltage_V <= 0:
        raise ValueError('Invalid electronics budget inputs')
    throughput = a.samples_per_second * a.transmission_bytes_per_sample
    power = a.channels * a.afe_power_mW_per_channel + a.mcu_active_power_mW * a.mcu_duty_cycle
    time_ms = 1000 / a.samples_per_second + a.sensing_latency_ms + a.serial_latency_ms
    return {
        'source': 'engineering_assumptions_not_component_specs',
        'channel_count': a.channels,
        'power_estimated_mW': round(power, 5),
        'energy_per_sample_mJ': round(power / a.samples_per_second, 7),
        'sample_latency_estimated_ms': round(time_ms, 4),
        'link_throughput_bytes_s': throughput,
        'link_capacity_pass': throughput <= a.link_bytes_per_second,
        'cost_status': 'unknown_no_verified_component_prices',
        'limitations': ['Uncalibrated current draw, no actual ADC/CDC choices, no hardware measured energy'],
        'assumptions': vars(a),
    }
