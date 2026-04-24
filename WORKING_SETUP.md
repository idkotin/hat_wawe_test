# Working Setup Notes

This file records the currently verified working setup for parallel reading from a load-cell terminal without breaking the terminal itself.

## Goal

Read weight on Raspberry Pi through Waveshare High-Precision AD HAT while the original terminal continues to power and use the same load cell.

## Confirmed Working Electrical Mode

Use the ADS1263 `adc2` frontend in passive parallel mode.

Do **not** power the bridge from the HAT in this mode.

### Wiring

```text
Original terminal powers the bridge:
  +   -> bridge E+
  -   -> bridge E-
  A+  -> bridge SIG+
  A-  -> bridge SIG-

Waveshare HAT in parallel:
  IN0      -> A+
  IN1      -> A-
  AVSS/GND -> -
  AVDD/5V  -> not connected
```

## Why This Mode

- `adc1` interfered with the original terminal.
- `adc2` did not break the terminal and produced a usable raw signal.
- Parallel read works with three connections because the terminal already powers the bridge; the HAT only reads the differential signal `A+ - A-` and shares ground with `-`.

## Verified Useful Command

This read mode was reported as the one that behaves well:

```bash
sudo python3 scale.py read --samples 24 --interval 0.15 --alpha 0.12 --median-window 7
```

## Recommended Full Flow

Update repo:

```bash
cd ~/hat_wawe_test
git pull
```

Parallel raw test:

```bash
sudo python3 scale.py raw --frontend adc2 --reference internal
```

Calibration in passive parallel mode:

```bash
sudo python3 scale.py calibrate --known 1400 --unit g --frontend adc2 --reference internal --samples 80
```

Stable reading:

```bash
sudo python3 scale.py read --samples 24 --interval 0.15 --alpha 0.12 --median-window 7
```

If calibration was created with `adc2/internal`, plain `read` will reuse that calibration mode. The explicit command above is kept here because it gives the preferred display behavior.

## Notes

- `AVDD/5V` from the HAT must stay disconnected in parallel mode.
- If sign is inverted, swap `IN0` and `IN1`.
- Very slow `ADC1` modes like `ADS1263_2d5SPS` were not useful here.
- This setup was validated first on a kitchen-scale test bench before moving to the forklift terminal project.
