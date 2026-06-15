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
// Virtual index mapping:
//  0: OE  = PI11 (port=8, pin=11) - Physical 32
//  1: CLK = PH6  (port=7, pin=6)  - Physical 23
//  2: LAT = PH7  (port=7, pin=7)  - Physical 19
//  3: A   = PH2  (port=7, pin=2)  - Physical 11
//  4: B   = PH3  (port=7, pin=3)  - Physical 13
//  5: C   = PH4  (port=7, pin=4)  - Physical 18
//  6: D   = PI5  (port=8, pin=5)  - Physical 15
//  7: E   = PI6  (port=8, pin=6)  - Physical 22
//  8: R1  = PI0  (port=8, pin=0)  - Physical 29
//  9: G1  = PI1  (port=8, pin=1)  - Physical 12
// 10: B1  = PI2  (port=8, pin=2)  - Physical 35
// 11: R2  = PI3  (port=8, pin=3)  - Physical 40
// 12: G2  = PI4  (port=8, pin=4)  - Physical 38
// 13: B2  = PI15 (port=8, pin=15) - Physical 31

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
