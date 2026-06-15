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

#ifndef RPI_GPIO_INTERNAL_H
#define RPI_GPIO_INTERNAL_H

#include "gpio-bits.h"
#include "gpio-bits-h618.h"

#include <vector>

#if __ARM_ARCH >= 7
#define LED_MATRIX_ALLOW_BARRIER_DELAY 1
#else
#define LED_MATRIX_ALLOW_BARRIER_DELAY 0
#endif

namespace rgb_matrix {
class GPIO {
public:
  GPIO();

  bool Init(int slowdown);

  gpio_bits_t InitOutputs(gpio_bits_t outputs,
                          bool adafruit_hack_needed = false);

  gpio_bits_t RequestInputs(gpio_bits_t inputs);

  void ResetState();

  inline void SetBits(gpio_bits_t value) {
    if (!value) return;
    if (is_h618_) {
      H618SetBits(value);
    } else {
      WriteSetBits(value);
    }
    delay();
  }

  inline void ClearBits(gpio_bits_t value) {
    if (!value) return;
    if (is_h618_) {
      H618ClearBits(value);
    } else {
      WriteClrBits(value);
    }
    delay();
  }

  inline void WriteMaskedBits(gpio_bits_t value, gpio_bits_t mask) {
    if (is_h618_) {
      H618ClearBits(~value & mask);
      H618SetBits(value & mask);
    } else {
      WriteClrBits(~value & mask);
      WriteSetBits(value & mask);
    }
    delay();
  }

  inline gpio_bits_t Read() const {
    if (is_h618_) return H618ReadBits() & input_bits_;
    return ReadRegisters() & input_bits_;
  }

  static bool IsPi4();
  static bool IsPi5Family();

private:
  inline void delay() const {
#if LED_MATRIX_ALLOW_BARRIER_DELAY
    if (slowdown_ == -1) {
        asm volatile("dsb\tst");
        return;
    }
#endif
    if (is_h618_) {
      if (s_GPIO_registers_) {
        volatile uint32_t *pi_data =
          s_GPIO_registers_ + (0x1800 + 0x10) / 4;
        (void)*pi_data;
      }
      for (int n = 0; n < slowdown_; n++) {
        asm volatile("" ::: "memory");
      }
    } else {
      for (int n = 0; n < slowdown_; n++) {
        *gpio_clr_bits_low_ = 0;
      }
    }
  }

  inline gpio_bits_t ReadRegisters() const {
    return (static_cast<gpio_bits_t>(*gpio_read_bits_low_)
#ifdef ENABLE_WIDE_GPIO_COMPUTE_MODULE
            | (static_cast<gpio_bits_t>(*gpio_read_bits_low_) << 32)
#endif
            );
  }

  inline void WriteSetBits(gpio_bits_t value) {
    *gpio_set_bits_low_ = static_cast<uint32_t>(value & 0xFFFFFFFF);
#ifdef ENABLE_WIDE_GPIO_COMPUTE_MODULE
    if (uses_64_bit_)
      *gpio_set_bits_high_ = static_cast<uint32_t>(value >> 32);
#endif
  }

  inline void WriteClrBits(gpio_bits_t value) {
    *gpio_clr_bits_low_ = static_cast<uint32_t>(value & 0xFFFFFFFF);
#ifdef ENABLE_WIDE_GPIO_COMPUTE_MODULE
    if (uses_64_bit_)
      *gpio_clr_bits_high_ = static_cast<uint32_t>(value >> 32);
#endif
  }

  // ORANGE_PI_ZERO2W: H618-specific methods (defined in gpio.cc)
  void H618SetBits(gpio_bits_t value);
  void H618ClearBits(gpio_bits_t value);
  gpio_bits_t H618ReadBits() const;

private:
  gpio_bits_t output_bits_;
  gpio_bits_t input_bits_;
  gpio_bits_t reserved_bits_;
  int slowdown_;
  bool is_h618_;

  volatile uint32_t *gpio_set_bits_low_;
  volatile uint32_t *gpio_clr_bits_low_;
  volatile uint32_t *gpio_read_bits_low_;

#ifdef ENABLE_WIDE_GPIO_COMPUTE_MODULE
  bool uses_64_bit_;
  volatile uint32_t *gpio_set_bits_high_;
  volatile uint32_t *gpio_clr_bits_high_;
  volatile uint32_t *gpio_read_bits_high_;
#endif

  // ORANGE_PI_ZERO2W: H618 memory-mapped register base
  volatile uint32_t *s_GPIO_registers_;
};

class PinPulser {
public:
  static PinPulser *Create(GPIO *io, gpio_bits_t gpio_mask,
                           bool allow_hardware_pulsing,
                           const std::vector<int> &nano_wait_spec);

  virtual ~PinPulser() {}
  virtual void SendPulse(int time_spec_number) = 0;
  virtual void WaitPulseFinished() {}
};

uint32_t GetMicrosecondCounter();
void SleepMicroseconds(long);

}  // end namespace rgb_matrix

#endif  // RPI_GPIO_INGERNALH
