#pragma once
// Shim for the ground-truth build with g++ 11 (no __bf16 type): same API as
// tron's bf16 (from_bits, to_bits, float ctor, operator float), RNE rounding.
#include <bit>
#include <cstdint>
#include <cstring>
namespace tron {
struct bf16 {
  uint16_t bits_ = 0;
  constexpr bf16() = default;
  bf16(float f) noexcept {
    uint32_t u = std::bit_cast<uint32_t>(f);
    uint32_t lsb = (u >> 16) & 1u;
    u += 0x7FFFu + lsb;  // round to nearest even (finite inputs only)
    bits_ = uint16_t(u >> 16);
  }
  operator float() const noexcept { return std::bit_cast<float>(uint32_t(bits_) << 16); }
  static constexpr bf16 from_bits(uint16_t b) noexcept { bf16 x; x.bits_ = b; return x; }
  constexpr uint16_t to_bits() const noexcept { return bits_; }
};
}  // namespace tron
