# Waveshare HAT Load Cell Scale

Console scale for Raspberry Pi + Waveshare High-Precision AD HAT + bridge load cell.

## Wiring

Default script channel is differential channel 0:

```text
Load cell E+    -> HAT AVDD / 5V analog power
Load cell E-    -> HAT AVSS / GND
Load cell SIG+  -> HAT IN0
Load cell SIG-  -> HAT IN1
```

If the weight goes negative when loaded, swap `SIG+` and `SIG-`.

## Raspberry Pi

Enable SPI:

```bash
sudo raspi-config
```

Install dependencies:

```bash
sudo apt update
sudo apt install -y git python3-spidev python3-rpi.gpio
```

Clone and run:

```bash
cd ~
git clone https://github.com/idkotin/hat_wawe_test.git
cd hat_wawe_test
sudo python3 scale.py raw --gain ADS1263_GAIN_1
sudo python3 scale.py calibrate --known 1000 --unit g
sudo python3 scale.py read
```

Use `tare` later to update zero:

```bash
sudo python3 scale.py tare
```

The Raspberry Pi hostname may be `isrk`; the driver in this repo no longer depends on the hostname being exactly `raspberrypi`.

If raw output is stuck near `2147483647` or `-2147483648`, the ADC input is saturated. Check that the bridge is powered and wired as `E+ -> AVDD/5V`, `E- -> AVSS/GND`, `SIG+ -> IN0`, `SIG- -> IN1`, and start with `--gain ADS1263_GAIN_1`.

## Parallel With Original Terminal

Let the original terminal power the load cell. Do not connect the HAT `AVDD/5V` to the load cell excitation in this mode.

Keep the load cell on the original terminal:

```text
blue        -> terminal E+
white-green -> terminal E-
white-blue  -> terminal SIG+
green       -> terminal SIG-
```

Connect the HAT in parallel only as a high-impedance reader:

```text
HAT IN0      -> terminal SIG+ / white-blue
HAT IN1      -> terminal SIG- / green
HAT AVSS/GND -> terminal E- / white-green
HAT AVDD/5V  -> leave disconnected from the terminal/load-cell wires
```

Run with the internal ADC reference:

```bash
sudo python3 scale.py raw --reference internal --gain ADS1263_GAIN_1
sudo python3 scale.py calibrate --known 1400 --unit g --reference internal --gain ADS1263_GAIN_1
sudo python3 scale.py read
```
