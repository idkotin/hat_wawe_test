#!/usr/bin/env python3
"""
Console scale for Waveshare High-Precision AD HAT + bridge load cell.

Typical flow on Raspberry Pi:
    cd /home/pi/hat_test
    sudo python3 scale.py calibrate --known 1000
    sudo python3 scale.py read
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
DRIVER_DIR = BASE_DIR / "High-Pricision_AD_HAT" / "python"
CALIBRATION_FILE = BASE_DIR / "scale_calibration.json"

DEFAULT_CHANNEL = 0
DEFAULT_DRATE = "ADS1263_20SPS"
DEFAULT_GAIN = "ADS1263_GAIN_32"
DEFAULT_SAMPLES = 40
DEFAULT_UNIT = "g"
ADC_FULL_SCALE_POSITIVE = 0x7FFFFFFF
ADC_FULL_SCALE_NEGATIVE = -0x80000000


def load_driver() -> Any:
    if not DRIVER_DIR.exists():
        raise SystemExit(
            f"Driver directory not found: {DRIVER_DIR}\n"
            "Clone Waveshare High-Pricision_AD_HAT into this folder first."
        )

    sys.path.insert(0, str(DRIVER_DIR))
    try:
        import ADS1263  # type: ignore
    except ImportError as exc:
        raise SystemExit(
            "Cannot import Waveshare ADS1263 driver. On Raspberry Pi install:\n"
            "  sudo apt install python3-spidev python3-rpi.gpio\n"
            "and enable SPI with:\n"
            "  sudo raspi-config\n"
        ) from exc

    return ADS1263


def signed32(value: int) -> int:
    return value - 0x100000000 if value & 0x80000000 else value


def configure_adc(ads_module: Any, channel: int, gain: str, drate: str) -> Any:
    if channel < 0 or channel > 4:
        raise SystemExit("Differential channel must be 0..4 (0 = IN0-IN1).")
    if gain not in ads_module.ADS1263_GAIN:
        raise SystemExit(f"Unknown gain {gain!r}. Use one of: {', '.join(ads_module.ADS1263_GAIN)}")
    if drate not in ads_module.ADS1263_DRATE:
        raise SystemExit(f"Unknown data rate {drate!r}. Use one of: {', '.join(ads_module.ADS1263_DRATE)}")

    adc = ads_module.ADS1263()
    if adc.ADS1263_init_ADC1(drate) == -1:
        raise SystemExit("ADS1263 init failed. Check HAT power, SPI, and GPIO wiring.")

    adc.ADS1263_SetMode(1)  # Differential mode: 0=IN0-IN1, 1=IN2-IN3, ...
    adc.ADS1263_WriteCmd(ads_module.ADS1263_CMD["CMD_STOP1"])

    mode2 = (ads_module.ADS1263_GAIN[gain] << 4) | ads_module.ADS1263_DRATE[drate]
    adc.ADS1263_WriteReg(ads_module.ADS1263_REG["REG_MODE2"], mode2)
    adc.ADS1263_WriteReg(ads_module.ADS1263_REG["REG_REFMUX"], 0x24)  # AVDD/AVSS reference
    adc.ADS1263_WriteReg(
        ads_module.ADS1263_REG["REG_MODE0"],
        ads_module.ADS1263_DELAY["ADS1263_DELAY_8d8ms"],
    )
    adc.ADS1263_WriteReg(ads_module.ADS1263_REG["REG_MODE1"], 0x84)  # FIR filter
    adc.ADS1263_WriteCmd(ads_module.ADS1263_CMD["CMD_START1"])
    time.sleep(0.2)
    return adc


def read_count(adc: Any, channel: int) -> int:
    return signed32(adc.ADS1263_GetChannalValue(channel))


def average_count(adc: Any, channel: int, samples: int, discard: int = 5) -> tuple[float, float]:
    for _ in range(discard):
        read_count(adc, channel)

    values = [read_count(adc, channel) for _ in range(samples)]
    mean = statistics.fmean(values)
    stdev = statistics.pstdev(values) if len(values) > 1 else 0.0
    return mean, stdev


def ensure_not_saturated(mean: float, noise: float) -> None:
    full_scale_margin = 1000
    if (
        abs(mean - ADC_FULL_SCALE_POSITIVE) <= full_scale_margin
        or abs(mean - ADC_FULL_SCALE_NEGATIVE) <= full_scale_margin
    ):
        raise SystemExit(
            "ADC is saturated at full-scale. This is not a valid load-cell signal.\n"
            "Check wiring: E+ -> AVDD, E- -> AVSS/GND, SIG+ -> IN0, SIG- -> IN1.\n"
            "Also try lower gain: --gain ADS1263_GAIN_1, then ADS1263_GAIN_2/4/8.\n"
            f"Last average: {mean:.1f} counts, noise sigma: {noise:.1f}"
        )


def save_calibration(data: dict[str, Any]) -> None:
    CALIBRATION_FILE.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def load_calibration() -> dict[str, Any]:
    if not CALIBRATION_FILE.exists():
        raise SystemExit(
            f"No calibration file: {CALIBRATION_FILE}\n"
            "Run first: sudo python3 scale.py calibrate --known 1000"
        )
    return json.loads(CALIBRATION_FILE.read_text(encoding="utf-8"))


def calibrate(args: argparse.Namespace) -> None:
    known = args.known
    if known is None:
        known = float(input(f"Known weight ({args.unit}): ").strip())
    if known == 0:
        raise SystemExit("Known weight must be non-zero.")

    ads_module = load_driver()
    adc = configure_adc(ads_module, args.channel, args.gain, args.drate)

    try:
        input("Remove everything from the scale, then press Enter...")
        zero, zero_noise = average_count(adc, args.channel, args.samples)
        print(f"Zero: {zero:.1f} counts, noise sigma: {zero_noise:.1f}")
        ensure_not_saturated(zero, zero_noise)

        input(f"Put exactly {known:g} {args.unit} on the scale, then press Enter...")
        loaded, loaded_noise = average_count(adc, args.channel, args.samples)
        print(f"Loaded: {loaded:.1f} counts, noise sigma: {loaded_noise:.1f}")
        ensure_not_saturated(loaded, loaded_noise)

        span = loaded - zero
        if abs(span) < 100:
            raise SystemExit(
                "Calibration span is too small. Check SIG+/SIG-, excitation wires, "
                "and that the load cell really changed load."
            )

        calibration = {
            "zero_counts": zero,
            "counts_per_unit": span / known,
            "known_weight": known,
            "unit": args.unit,
            "channel": args.channel,
            "gain": args.gain,
            "drate": args.drate,
            "samples": args.samples,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        save_calibration(calibration)
        print(f"Saved calibration to {CALIBRATION_FILE}")
        print(f"Scale factor: {calibration['counts_per_unit']:.6f} counts/{args.unit}")
    finally:
        adc.ADS1263_Exit()


def tare(args: argparse.Namespace) -> None:
    calibration = load_calibration()
    channel = args.channel if args.channel is not None else calibration["channel"]
    ads_module = load_driver()
    adc = configure_adc(
        ads_module,
        channel,
        args.gain or calibration["gain"],
        args.drate or calibration["drate"],
    )

    try:
        input("Remove everything from the scale, then press Enter to tare...")
        zero, noise = average_count(adc, channel, args.samples or calibration["samples"])
        ensure_not_saturated(zero, noise)
        calibration["zero_counts"] = zero
        calibration["channel"] = channel
        calibration["tare_updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        save_calibration(calibration)
        print(f"New zero: {zero:.1f} counts, noise sigma: {noise:.1f}")
    finally:
        adc.ADS1263_Exit()


def read_loop(args: argparse.Namespace) -> None:
    calibration = load_calibration()
    channel = args.channel if args.channel is not None else calibration["channel"]
    gain = args.gain or calibration["gain"]
    drate = args.drate or calibration["drate"]
    samples = args.samples or calibration["samples"]
    unit = calibration["unit"]

    ads_module = load_driver()
    adc = configure_adc(ads_module, channel, gain, drate)

    filtered_weight: float | None = None
    try:
        print("Reading weight. Press Ctrl+C to stop.")
        while True:
            count, noise = average_count(adc, channel, samples, discard=1)
            ensure_not_saturated(count, noise)
            weight = (count - calibration["zero_counts"]) / calibration["counts_per_unit"]
            filtered_weight = weight if filtered_weight is None else (
                args.alpha * weight + (1.0 - args.alpha) * filtered_weight
            )
            sys.stdout.write(
                f"\rweight: {filtered_weight:10.2f} {unit}   "
                f"raw: {count:12.1f}   noise: {noise:8.1f}   "
            )
            sys.stdout.flush()
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        adc.ADS1263_Exit()


def raw_loop(args: argparse.Namespace) -> None:
    ads_module = load_driver()
    adc = configure_adc(ads_module, args.channel, args.gain, args.drate)
    try:
        print("Raw differential counts. Press Ctrl+C to stop.")
        while True:
            count, noise = average_count(adc, args.channel, args.samples, discard=1)
            status = " SATURATED " if (
                abs(count - ADC_FULL_SCALE_POSITIVE) <= 1000
                or abs(count - ADC_FULL_SCALE_NEGATIVE) <= 1000
            ) else ""
            sys.stdout.write(f"\rraw: {count:12.1f}   noise: {noise:8.1f} {status:11s}")
            sys.stdout.flush()
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        adc.ADS1263_Exit()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Calibrate and read a load-cell scale via Waveshare High-Precision AD HAT.",
    )
    sub = parser.add_subparsers(dest="command")

    cal = sub.add_parser("calibrate", help="Calibrate zero and known load.")
    cal.add_argument("--known", type=float, help="Known calibration weight, e.g. 1000 for 1000 g.")
    cal.add_argument("--unit", default=DEFAULT_UNIT, help="Unit label to print, default: g.")
    cal.add_argument("--channel", type=int, default=DEFAULT_CHANNEL, help="Differential channel 0..4.")
    cal.add_argument("--gain", default=DEFAULT_GAIN, help="ADS1263 PGA gain.")
    cal.add_argument("--drate", default=DEFAULT_DRATE, help="ADS1263 ADC1 data rate.")
    cal.add_argument("--samples", type=int, default=DEFAULT_SAMPLES, help="Samples to average.")
    cal.set_defaults(func=calibrate)

    read = sub.add_parser("read", help="Read calibrated weight continuously.")
    read.add_argument("--channel", type=int, help="Override differential channel 0..4.")
    read.add_argument("--gain", help="Override ADS1263 PGA gain.")
    read.add_argument("--drate", help="Override ADS1263 ADC1 data rate.")
    read.add_argument("--samples", type=int, help="Samples to average.")
    read.add_argument("--interval", type=float, default=0.2, help="Delay between prints, seconds.")
    read.add_argument("--alpha", type=float, default=0.25, help="Display smoothing 0..1.")
    read.set_defaults(func=read_loop)

    zero = sub.add_parser("tare", help="Update zero using existing calibration.")
    zero.add_argument("--channel", type=int, help="Override differential channel 0..4.")
    zero.add_argument("--gain", help="Override ADS1263 PGA gain.")
    zero.add_argument("--drate", help="Override ADS1263 ADC1 data rate.")
    zero.add_argument("--samples", type=int, help="Samples to average.")
    zero.set_defaults(func=tare)

    raw = sub.add_parser("raw", help="Show raw ADC counts for wiring/debug.")
    raw.add_argument("--channel", type=int, default=DEFAULT_CHANNEL, help="Differential channel 0..4.")
    raw.add_argument("--gain", default=DEFAULT_GAIN, help="ADS1263 PGA gain.")
    raw.add_argument("--drate", default=DEFAULT_DRATE, help="ADS1263 ADC1 data rate.")
    raw.add_argument("--samples", type=int, default=DEFAULT_SAMPLES, help="Samples to average.")
    raw.add_argument("--interval", type=float, default=0.2, help="Delay between prints, seconds.")
    raw.set_defaults(func=raw_loop)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.command is None:
        args = parser.parse_args(["read" if CALIBRATION_FILE.exists() else "calibrate"])
    args.func(args)


if __name__ == "__main__":
    main()
