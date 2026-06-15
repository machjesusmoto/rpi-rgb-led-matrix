// -*- mode: c++; c-basic-offset: 2; indent-tabs-mode: nil; -*-
// Copyright (C) 2013 Henner Zeller <h.zeller@acm.org>
//
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation version 2.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <http://gnu.org/licenses/gpl-2.0.txt>

// ORANGE_PI_ZERO2W: H618 GPIO register definitions for Allwinner H618 SoC
// Used by Orange Pi Zero 2W platform support.

#ifndef RPI_GPIO_BITS_H618_H
#define RPI_GPIO_BITS_H618_H

#include <stdint.h>

// H618 PIO (Parallel I/O) base address — physical address of GPIO controller
#define ORANGEPI_H618_PIO_BASE 0x0300B000

// H618 GPIO register layout per port:
//   Each port (PA..PI) has its own register block.
//   Block size per port = 0x300 (768 bytes).
//   Port index: A=0, B=1, C=2, D=3, E=4, F=5, G=6, H=7, I=8

#define H618_PORT_BLOCK_SIZE  0x300   // bytes between port bases

// Register offsets within each port block
#define H618_CFG0_OFFSET  0x00   // Port configuration register 0 (pins 0-7)
#define H618_CFG1_OFFSET  0x04   // Port configuration register 1 (pins 8-15)
#define H618_CFG2_OFFSET  0x08   // Port configuration register 2 (pins 16-23)
#define H618_CFG3_OFFSET  0x0C   // Port configuration register 3 (pins 24-31)
#define H618_DAT_OFFSET   0x10   // Port data register
#define H618_DRV0_OFFSET  0x14   // Port drive level register 0
#define H618_DRV1_OFFSET  0x18   // Port drive level register 1
#define H618_PULL0_OFFSET 0x1C   // Port pull register 0 (pins 0-15)
#define H618_PULL1_OFFSET 0x20   // Port pull register 1 (pins 16-31)

// GPIO mode constants for config registers (2 bits per pin)
#define H618_GPIO_MODE_INPUT   0x00
#define H618_GPIO_MODE_OUTPUT  0x01
#define H618_GPIO_MODE_ALT2    0x02
#define H618_GPIO_MODE_ALT3    0x03

// Port indices for Orange Pi Zero 2W GPIO ports
#define H618_PORT_A  0
#define H618_PORT_B  1
#define H618_PORT_C  2
#define H618_PORT_D  3
#define H618_PORT_E  4
#define H618_PORT_F  5
#define H618_PORT_G  6
#define H618_PORT_H  7
#define H618_PORT_I  8

// Calculate absolute GPIO number from port and pin
#define H618_GPIO_NUMBER(port, pin)  ((port) * 32 + (pin))

// Calculate memory offset for a port's register block
#define H618_PORT_OFFSET(port)  ((port) * H618_PORT_BLOCK_SIZE)

// Number of Hub75 virtual signals for Orange Pi Zero 2W
#define H618_NUM_VIRTUAL_PINS 14

// ORANGE_PI_ZERO2W: Virtual-to-physical pin translation table
// Maps virtual GPIO index (used in HardwareMapping) to (port, pin) on H618.
// Virtual indices match the orangepi-zero2w HardwareMapping struct.
//
// Pin mapping follows the Adafruit RGB Matrix Bonnet physical layout.
// The bonnet routes RPi BCM GPIOs to Hub75 signals via specific physical
// header pins. When plugged into the Orange Pi Zero 2W, those same physical
// pins map to different H618 GPIO numbers.
//
// Virtual index mapping (Bonnet → Orange Pi Zero 2W):
//  0: OE  = PI13 (port=8, pin=13) - Physical 7   (RPi GPIO 4)
//  1: CLK = PH2  (port=7, pin=2)  - Physical 11  (RPi GPIO 17)
//  2: LAT = PI3  (port=8, pin=3)  - Physical 40  (RPi GPIO 21)
//  3: A   = PI5  (port=8, pin=5)  - Physical 15  (RPi GPIO 22)
//  4: B   = PI16 (port=8, pin=16) - Physical 37  (RPi GPIO 26)
//  5: C   = PH3  (port=7, pin=3)  - Physical 13  (RPi GPIO 27)
//  6: D   = PI4  (port=8, pin=4)  - Physical 38  (RPi GPIO 20)
//  7: E   = PH4  (port=7, pin=4)  - Physical 18  (RPi GPIO 24)
//  8: R1  = PI0  (port=8, pin=0)  - Physical 29  (RPi GPIO 5)
//  9: G1  = PI12 (port=8, pin=12) - Physical 33  (RPi GPIO 13)
// 10: B1  = PI15 (port=8, pin=15) - Physical 31  (RPi GPIO 6)
// 11: R2  = PI11 (port=8, pin=11) - Physical 32  (RPi GPIO 12)
// 12: G2  = PC12 (port=2, pin=12) - Physical 36  (RPi GPIO 16)
// 13: B2  = PI14 (port=8, pin=14) - Physical 16  (RPi GPIO 23)

#ifdef __cplusplus
extern "C" {
#endif

struct H618Pin {
  uint8_t port;   // Port index: 0=A, 1=B, ..., 7=H, 8=I
  uint8_t pin;    // Pin number within port (0-31)
};

// Static translation table — defined in gpio.cc (C++ context)
// Declared here for documentation; actual definition in gpio.cc
// because it needs to be accessible from C++ GPIO class methods.

#ifdef __cplusplus
}
#endif

#endif  // RPI_GPIO_BITS_H618_H
