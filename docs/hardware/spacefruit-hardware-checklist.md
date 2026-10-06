# SpaceFruit robot parts checklist

Ownership notes from the user remain marked owned. New part numbers below are recommended selections for an 8 × 5 in (203.2 × 127 mm) chassis prototype; verify the exact variant/labels on already-owned boards before powering them.

## Owned

- [x] Raspberry Pi 5
- [x] PCA9685 PWM controller — set logic VCC to 3.3 V; servo V+ is a separate 5 V rail. Verify the exact board supports 3.3 V logic.
- [x] BME280 breakout — use 3.3 V I/O/pull-ups. If the owned board is a bare sensor, replace with a breakout such as Adafruit BME280.
- [x] Front camera: Raspberry Pi Camera Module 3 Wide
- [x] Arm camera: Raspberry Pi Camera Module 3 autofocus
- [x] YD-RP2040 dual-core controller
- [x] Motor driver board (model unknown; retain for inspection, but do not connect until its ratings match the selected motors)

## Recommended selected components

### Chassis, wheels, drive

- [ ] Four 60 × 8 mm Pololu wheels, item #1420 (two pairs); 60 mm diameter, 3 mm D-shaft.
- [ ] Four 210:1 Micro Metal Gearmotors MP 6 V with 12 CPR encoders, Pololu #5142; 100 rpm no-load, 0.67 A theoretical stall each. Add encoder leads appropriate to its 6-pin back connector.
- [ ] Two Pololu Motoron M2T256 dual I²C motor controllers, #5064; one board per left/right pair; set distinct I²C addresses. Each supports two channels and 1.8 A continuous/channel.
- [ ] Four compatible micro metal gearmotor mounting brackets (two pairs) and printed clamp/bolt features.
- [ ] M2/M2.5 fastener assortment, standoffs, cable clips, four bumper switches, arm joint limit switches, and a guarded normally-closed latching E-stop.
- [ ] Chassis print: [editable OpenSCAD model](spacefruit-robot-concept.scad), [body-only STL](spacefruit-robot-body-8x5-print.stl), and [preview assembly STL](spacefruit-robot-assembly-8x5.stl). The arm remains separate.

### Sensors and arm

- [ ] One Adafruit BNO085 9-DOF IMU breakout; feed 3.3 V and use 3.3 V I²C logic.
- [ ] Two Pololu VL53L1X carriers #3415 for front/rear ranging; power VIN from 3.3 V. Use separate RP2040 XSHUT GPIOs and assign addresses during boot.
- [ ] Four TowerPro SG92R micro servos (3–6 V; use a 5 V rail) for the light-duty printed arm. Recheck payload and joint torque before loading the arm.
- [ ] Camera cables: two Pi 5 22-pin-to-camera 15-pin CSI cables; verify whether supplied with cameras. Use strain relief on arm CSI cable.
- [ ] Optional: 3.3 V ADS1115 breakout plus a 3.3 V-capable capacitive soil-moisture probe if the app needs analog soil readings.

### Power / safety

- [ ] 3S 18650 Li-ion battery, 9–12.6 V, with matched cells and ≥15 A BMS; use a chemistry-compatible 12.6 V 3S balance charger. Capacity 2.5–3 Ah is a compact starting point; runtime depends on duty cycle.
- [ ] Main fuse close to battery, master disconnect, branch fuses, normally-closed latching E-stop relay/contact rated for the DC loads, and a star-ground distribution block.
- [ ] 6 V regulated motor rail capable of ≥3 A continuous and motor-start transients; fuse after measuring real motor currents. Do not connect the 3S battery directly to 6 V motors.
- [ ] Dedicated 5 V, 5 A servo buck regulator, fused separately; PCA9685 V+ only.
- [ ] DFRobot FIT0992 Pi 5 UPS/regulator (6–18 V input, advertised 5.1 V / 5 A output) from the 3S bus. Use its intended Pi connection and confirm available output under simultaneous camera/compute load.
- [ ] 3.3 V rail for sensor breakouts/logic, from controller/regulator; check cumulative load and I²C pull-ups.
- [ ] Appropriately sized wire/connectors, insulating covers, strain relief, and a ventilated splash/dust-resistant enclosure. Keep plant moisture away from open PCBs.

## Fit and limits

The printed overall bumper envelope is 203.2 × 127 mm (8 × 5 in); the rounded shell is 196.8 mm long and the curved front/rear bumpers complete the 203.2 mm length without wrapping beside the wheel wells. The 60 mm wheels use 70 mm-diameter pockets with 5 mm radial clearance and 14 mm width, recessed 1 mm. This is a compact, light-duty indoor/garden prototype. The motor brackets, electronics, cable bends, battery, camera FOV, arm reach, and service access still need a physical mock-fit before printing final hardware. The current concept STL is a shell prototype, not a validated production chassis or IP-rated enclosure. The 8 × 5 in envelope does not include the separate arm model.

The BME280 and PCA9685 already owned may be different breakout variants; confirm that their logic pins are 3.3 V-compatible. The unidentified owned driver board might replace the proposed Motorons only after its exact model is checked against four 6 V motors and encoder/controller interface.
