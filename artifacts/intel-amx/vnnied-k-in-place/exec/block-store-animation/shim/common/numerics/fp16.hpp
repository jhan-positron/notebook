#pragma once
#include <cstdint>
namespace tron { struct fp16 { uint16_t bits_ = 0; operator float() const noexcept { return 0.f; } }; }
