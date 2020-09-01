# Kcalibrator
Alternative K-factor calibration pattern generator.
Should provide better (or at least different) way to calibrate Liniar Advance (and similar algorythms) than default Marlin K-factor Calibration Pattern (https://marlinfw.org/tools/lin_advance/k-factor.html)

## Requirements
Requires Python 3 to run.
No additional packages except the Standard Library required.

## Usage
Currently it is a simple script which provides no interface. Configuration is done by changing parameters in the script body.
Configure the script and run it with Python - it will generate output G-Code file in the working directory.

User can adjust:
- Basic machine parameters (bed size, filament diameter, autoleveling, etc.)
- Basic printing settings (temperature, cooling, retraction, etc.)
- Pattern parameters (size, speeds, K-factor range and step, number of perimeters, number of layers prited with each specific K-factor)
