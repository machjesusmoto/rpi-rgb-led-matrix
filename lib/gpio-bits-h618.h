// -*- mode: c++; c-basic-offset: 2; indent-tabs-mode: nil; -*-
// ORANGE_PI_ZERO2W: Allwinner H618 GPIO register definitions
// Copyright (C) 2026 Orange Pi Zero 2W support contributors
//
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation version 2.

#ifndef RPI_GPIO_BITS_H618_H
#define RPI_GPIO_BITS_H618_H

#include <stdint.h>

// ORANGE_PI_ZERO2W: H618 PIO (GPIO) base address
// Source: Allwinner H616/H618 User Manual, sunxi-tools
#define H618_PIO_BASE 0x0300B000

// ORANGE_PI_ZERO2W: GPIO register block size (4KB per port bank)
#define H618_PIO_BLOCK_SIZE (4 * 1024)

// ORANGE_PI_ZERO2W: Port indices for GPIO number calculation
// GPIO number = (port_index * 32) + pin_number
// Example: PI13 = (8 * 32) + 13 = 269
enum H618_GPIO_Port {
  H618_PORT_A = 0,  // PA0-PA31
  H618_PORT_B = 1,  // PB0-PB31
  H618_PORT_C = 2,  // PC0-PC31
  H618_PORT_D = 3,  // PD0-PD31
  H618_PORT_E = 4,  // PE0-PE31
  H618_PORT_F = 5,  // PF0-PF31
  H618_PORT_G = 6,  // PG0-PG31
  H618_PORT_H = 7,  // PH0-PH31
  H618_PORT_I = 8,  // PI0-PI31
  H618_PORT_COUNT = 9
};

// ORANGE_PI_ZERO2W: Per-port register offsets (relative to PIO_BASE + port*0x24)
// Each port has registers at offset: port_index * 0x24 (36 bytes per port)
#define H618_PORT_OFFSET(port) ((port) * 0x24)

// ORANGE_PI_ZERO2W: Register offsets within each port
#define H618_Pn_CFG0  0x00  // Port n Configure Register 0 (pins 0-7)
#define H618_Pn_CFG1  0x04  // Port n Configure Register 1 (pins 8-15)
#define H618_Pn_CFG2  0x08  // Port n Configure Register 2 (pins 16-23)
#define H618_Pn_CFG3  0x0C  // Port n Configure Register 3 (pins 24-31)
#define H618_Pn_DAT   0x10  // Port n Data Register
#define H618_Pn_DRV0  0x14  // Port n Multi-Driving Register 0
#define H618_Pn_DRV1  0x18  // Port n Multi-Driving Register 1
#define H618_Pn_PUL0  0x1C  // Port n Pull Register 0 (pins 0-15)
#define H618_Pn_PUL1  0x20  // Port n Pull Register 1 (pins 16-31)

// ORANGE_PI_ZERO2W: Pin function configuration values (4 bits per pin)
#define H618_GPIO_INPUT   0x0  // Input mode
#define H618_GPIO_OUTPUT  0x1  // Output mode
// Functions 2-7 are alternate functions (varies by pin)
#define H618_GPIO_DISABLE 0xF  // Disabled

// ORANGE_PI_ZERO2W: Pull-up/down configuration (2 bits per pin)
#define H618_PULL_DISABLE  0x0
#define H618_PULL_UP       0x1
#define H618_PULL_DOWN     0x2

// ORANGE_PI_ZERO2W: Helper macros for GPIO calculations
#define H618_GPIO_PORT(gpio)  ((gpio) / 32)
#define H618_GPIO_PIN(gpio)   ((gpio) % 32)
#define H618_GPIO_NUM(port, pin) ((port) * 32 + (pin))

// ORANGE_PI_ZERO2W: Get the configuration register offset for a pin
// Each CFG register handles 8 pins (4 bits each = 32 bits)
#define H618_CFG_REG_OFFSET(pin) (((pin) / 8) * 4)  // CFG0, CFG1, CFG2, or CFG3
#define H618_CFG_BIT_OFFSET(pin) (((pin) % 8) * 4)  // Bit position within register

// ORANGE_PI_ZERO2W: Get the pull register offset for a pin
// Each PUL register handles 16 pins (2 bits each = 32 bits)
#define H618_PUL_REG_OFFSET(pin) (((pin) / 16) * 4)  // PUL0 or PUL1
#define H618_PUL_BIT_OFFSET(pin) (((pin) % 16) * 2)  // Bit position within register

// ORANGE_PI_ZERO2W: Hub75 signal GPIO assignments for Orange Pi Zero 2W
// Based on research.md R4 pin mapping table
// Physical Pin | GPIO Name | GPIO Number
//
// Data signals - using Port I (PI) pins for grouping
#define H618_HUB75_R1   256  // PI0,  Physical pin 29
#define H618_HUB75_G1   257  // PI1,  Physical pin 12
#define H618_HUB75_B1   258  // PI2,  Physical pin 35
#define H618_HUB75_R2   259  // PI3,  Physical pin 40
#define H618_HUB75_G2   260  // PI4,  Physical pin 38
#define H618_HUB75_B2   271  // PI15, Physical pin 31

// Address signals - mixed PH and PI
#define H618_HUB75_A    226  // PH2,  Physical pin 11
#define H618_HUB75_B    227  // PH3,  Physical pin 13
#define H618_HUB75_C    228  // PH4,  Physical pin 18
#define H618_HUB75_D    261  // PI5,  Physical pin 15
#define H618_HUB75_E    262  // PI6,  Physical pin 22

// Control signals
#define H618_HUB75_CLK  230  // PH6,  Physical pin 23 (SPI1_CLK capable)
#define H618_HUB75_LAT  231  // PH7,  Physical pin 19 (SPI1_MOSI capable)
#define H618_HUB75_OE   267  // PI11, Physical pin 32 (PWM1 capable)

#endif  // RPI_GPIO_BITS_H618_H
