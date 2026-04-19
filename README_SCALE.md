# Load Cell Scale

Files:
- `scale.py` - calibration and live console weight readout.
- `High-Pricision_AD_HAT/python` - official Waveshare ADS1263 driver.
- `scale_calibration.json` - created after calibration.

## Wiring

Default script channel is differential channel 0:

```text
Load cell E+    -> HAT AVDD / 5V analog power
Load cell E-    -> HAT AVSS / GND
Load cell SIG+  -> HAT IN0
Load cell SIG-  -> HAT IN1
```

If the weight goes negative when loaded, swap `SIG+` and `SIG-`, or recalibrate with the current polarity and mentally treat the sign accordingly.

Other differential pairs are:

```text
channel 0: IN0 - IN1
channel 1: IN2 - IN3
channel 2: IN4 - IN5
channel 3: IN6 - IN7
channel 4: IN8 - IN9
```

## Raspberry Pi Setup

Enable SPI:

```bash
sudo raspi-config
```

Install Python GPIO/SPI libraries:

```bash
sudo apt update
sudo apt install python3-spidev python3-rpi.gpio
```

## Use

First calibrate with an empty scale and a known weight:

```bash
cd /home/pi/hat_test
sudo python3 scale.py calibrate --known 1000 --unit g
```

Then read weight:

```bash
sudo python3 scale.py read
```

Update zero later:

```bash
sudo python3 scale.py tare
```

Debug raw ADC counts:

```bash
sudo python3 scale.py raw
```

If raw output is stuck near `2147483647` or `-2147483648`, the ADC input is saturated. Check the four load-cell wires and start with low gain:

```bash
sudo python3 scale.py raw --gain ADS1263_GAIN_1
```

Defaults are differential channel `0` (`IN0-IN1`), data rate `ADS1263_20SPS`, PGA gain `ADS1263_GAIN_32`, and 40 averaged samples.
