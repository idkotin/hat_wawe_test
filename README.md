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
sudo python3 scale.py calibrate --known 1000 --unit g
sudo python3 scale.py read
```

Use `tare` later to update zero:

```bash
sudo python3 scale.py tare
```

The Raspberry Pi hostname may be `isrk`; the driver in this repo no longer depends on the hostname being exactly `raspberrypi`.
