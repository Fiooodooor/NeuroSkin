"""Dimensionally explicit assumption-only resource budget, not component specs."""
from __future__ import annotations
from dataclasses import dataclass
import math
import numpy as np


@dataclass(frozen=True)
class ElectronicsAssumptions:
    channels: int = 7
    samples_per_second: int = 500
    afe_power_mW_per_channel: float = 0.7
    mcu_active_power_mW: float = 9.0
    mcu_duty_cycle: float = .1
    transmission_bytes_per_sample: int | None = None
    link_bytes_per_second: int = 100_000
    sensing_latency_ms: float = 2.0
    serial_latency_ms: float = .5
    voltage_V: float = 3.3
    resolution_bits: int = 16
    packet_overhead_bytes: int = 2
    parallel_adcs: int = 1
    conversion_time_s: float = .0001
    mux_settling_s: float = .00001
    front_end_rms_noise_V: float = .001


def estimate_budget(assumptions: ElectronicsAssumptions = ElectronicsAssumptions()):
    a = assumptions
    for k in ('channels','samples_per_second','link_bytes_per_second','resolution_bits','parallel_adcs','packet_overhead_bytes'):
        v=getattr(a,k)
        if type(v) is not int or v < (0 if k=='packet_overhead_bytes' else 1):
            raise ValueError(f'Invalid integer {k}')
    if a.channels>1024 or not 1<=a.resolution_bits<=32 or a.parallel_adcs>a.channels:
        raise ValueError('Invalid channel, ADC count or resolution')
    for k in ('afe_power_mW_per_channel','mcu_active_power_mW','mcu_duty_cycle','sensing_latency_ms',
              'serial_latency_ms','voltage_V','conversion_time_s','mux_settling_s','front_end_rms_noise_V'):
        v=getattr(a,k)
        if not math.isfinite(v) or v<0 or (k in ('voltage_V','conversion_time_s') and v==0):
            raise ValueError(f'Invalid {k}')
    if a.mcu_duty_cycle>1:raise ValueError('MCU duty cycle must be at most one')
    min_bytes=a.channels*math.ceil(a.resolution_bits/8)+a.packet_overhead_bytes
    packet_bytes=min_bytes if a.transmission_bytes_per_sample is None else a.transmission_bytes_per_sample
    if type(packet_bytes) is not int or packet_bytes<min_bytes:
        raise ValueError('Packet does not contain all logical output samples and overhead')
    throughput=a.samples_per_second*packet_bytes
    power=a.channels*a.afe_power_mW_per_channel+a.mcu_active_power_mW*a.mcu_duty_cycle
    scan_s=math.ceil(a.channels/a.parallel_adcs)*(a.conversion_time_s+a.mux_settling_s)
    time_ms=1000/a.samples_per_second+1000*scan_s+a.sensing_latency_ms+a.serial_latency_ms
    qnoise=a.voltage_V/(2**a.resolution_bits)/math.sqrt(12)
    return {
        'source':'engineering_assumptions_not_component_specs',
        'channel_count':a.channels,'packet_bytes':packet_bytes,
        'power_estimated_mW':round(power,5),
        'energy_per_sample_mJ':round(power/a.samples_per_second,7),
        'sample_latency_estimated_ms':round(time_ms,4),
        'scan_time_s':scan_s,'max_scan_rate_Hz':1/scan_s,
        'adc_capacity_pass':scan_s*a.samples_per_second<=1,
        'adc_quantization_noise_rms_V':qnoise,
        'adc_total_rms_noise_V_assumed':math.hypot(qnoise,a.front_end_rms_noise_V),
        'link_throughput_bytes_s':throughput,
        'link_capacity_pass':throughput<=a.link_bytes_per_second,
        'cost_status':'unknown_no_verified_component_prices',
        'limitations':['Logical channels, no physical ADC/CDC topology or datasheet choices',
                       'Uncalibrated power and noise; no measured energy or bus contention'],
        'assumptions':vars(a),
    }


def budget_for_response(response):
    """Count actual logical wired outputs, including active intermediate-stage channels."""
    p=response['piezoelectric'];e=response['electrical']
    wiring=np.asarray(p['wiring_matrix'],float)
    films=p['channels'];n=len(films)
    if wiring.ndim!=2 or wiring.shape[1]!=n or not len(wiring) or not np.isfinite(wiring).all():
        raise ValueError('Invalid PVDF wiring matrix')
    if not np.all(np.isin(wiring,[-1.,0.,1.])) or np.any(np.sum(np.abs(wiring),axis=1)==0):
        raise ValueError('PVDF wiring must specify nonempty signed film connections')
    static_count=len(e['pressure_delta_pF'])+len(e['lateral_delta_pF'])+1
    stage_count=len(e.get('hybrid_stage_channels',{}).get('readout_vector_pF_assumed',[]))
    out=estimate_budget(ElectronicsAssumptions(channels=static_count+stage_count+len(wiring)))
    initial=np.asarray([f['initial_charge_amplifier_V'] for f in films],float)
    caps=np.asarray([f['capacitance_pF'] for f in films],float)
    if not np.isfinite(initial).all() or not np.isfinite(caps).all() or np.any(caps<=0):
        raise ValueError('Invalid film electrical data')
    wt=2*math.pi*float(p['frequency_hz'])*float(p['leak_tau_s'])
    if not math.isfinite(wt) or wt<0:raise ValueError('Invalid RC frequency/time constant')
    peak=np.abs(wiring@initial)*wt/math.hypot(1.,wt)
    headroom=out['assumptions']['voltage_V']/2
    out.update(static_output_count=static_count,stage_output_count=stage_count,
               pvdf_film_count=n,pvdf_output_count=len(wiring),
               pvdf_capacitance_per_output_pF_assumed=(np.abs(wiring)@caps).tolist(),
               pvdf_output_peak_V_assumed=peak.tolist(),
               pvdf_saturated_outputs_assumed=int(np.sum(peak>headroom)),
               pvdf_peak_headroom_V_assumed=headroom,
               saturation_note='Diagnostic at the supplied load/frequency, centered ideal ADC span; not a circuit qualification')
    return out
