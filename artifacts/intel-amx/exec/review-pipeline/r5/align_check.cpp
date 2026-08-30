#include <cstdio>
#include <cstdint>
#include <vector>
int main(){
  // mimic: thread_local std::vector<uint16_t> amx_qpack; resize(items * 2048)
  for (size_t items : {1u, 4u, 16u, 64u, 256u}) {
    std::vector<uint16_t> v; v.resize(items * 2048);
    std::printf("items=%3zu bytes=%8zu base%%64=%2zu\n", items, v.size()*2, (uintptr_t)v.data() % 64);
  }
}
