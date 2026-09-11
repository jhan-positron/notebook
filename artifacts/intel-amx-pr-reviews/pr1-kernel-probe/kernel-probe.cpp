#include <immintrin.h>
#include <array>
#include <bit>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <random>
#include <stdexcept>
// Instrument only the tile instructions. AVX-512 packing/transposition and
// the PR's kernel loop bodies below are unchanged. bf16 is a 2-byte storage
// shim because this environment has GCC 12, not the repository's Clang 19.
namespace emulated_tile {
unsigned char registers[8][16][64]{};
bool configured=false;
void config(const void* p) {
  const auto* b=static_cast<const unsigned char*>(p);
  if(b[0]!=1 || b[1]!=0) throw std::runtime_error("bad palette");
  for(int t=0;t<8;++t) {
    uint16_t cols; std::memcpy(&cols,b+16+t*2,2);
    if(cols!=64 || b[48+t]!=16) throw std::runtime_error("bad tile shape");
  }
  configured=true;
}
void check(){if(!configured) throw std::runtime_error("tile outside region");}
void zero(int t){check();std::memset(registers[t],0,1024);}
void load(int t,const void* p,size_t stride){check();for(int r=0;r<16;++r)std::memcpy(registers[t][r],static_cast<const unsigned char*>(p)+r*stride,64);}
void store(int t,void* p,size_t stride){check();for(int r=0;r<16;++r)std::memcpy(static_cast<unsigned char*>(p)+r*stride,registers[t][r],64);}
float bf(const unsigned char* p){uint16_t v;std::memcpy(&v,p,2);return std::bit_cast<float>(uint32_t(v)<<16);}
void dp(int d,int a,int b){
  check();
  for(int r=0;r<16;++r)for(int c=0;c<16;++c){
    float sum;std::memcpy(&sum,&registers[d][r][c*4],4);
    for(int k=0;k<16;++k){
      sum+=bf(&registers[a][r][k*4])*bf(&registers[b][k][c*4]);
      sum+=bf(&registers[a][r][k*4+2])*bf(&registers[b][k][c*4+2]);
    }
    std::memcpy(&registers[d][r][c*4],&sum,4);
  }
}
}
#undef _tile_loadconfig
#undef _tile_release
#undef _tile_zero
#undef _tile_loadd
#undef _tile_stored
#undef _tile_dpbf16ps
#define _tile_loadconfig(p) emulated_tile::config(p)
#define _tile_release() (emulated_tile::configured=false)
#define _tile_zero(t) emulated_tile::zero(t)
#define _tile_loadd(t,p,s) emulated_tile::load(t,p,s)
#define _tile_stored(t,p,s) emulated_tile::store(t,p,s)
#define _tile_dpbf16ps(d,a,b) emulated_tile::dp(d,a,b)
#include "/home/jhan/workspace/tron-amx/src/tron/kernels/amx_attn.cpp"

uint16_t rne(float x){auto b=std::bit_cast<uint32_t>(x);return (b+0x7fffu+((b>>16)&1))>>16;}
float to_float(tron::bf16 x){return std::bit_cast<float>(uint32_t(x.bits)<<16);}
void require(bool p,const char* msg){if(!p)throw std::runtime_error(msg);}
int main(){
  using namespace tron::amx_attn_h128g4;
  size_t checks=0;
  for(unsigned seed: {11u,12u,13u,14u,31u}){
    std::mt19937 rng(seed);std::uniform_real_distribution<float> dist(-1,1),ex(-10,0);
    alignas(64) std::array<tron::bf16,512> q;
    alignas(64) std::array<tron::bf16,8192> k,v;
    alignas(64) std::array<tron::bf16,2048> packed{};
    for(auto& x:q)x.bits=rne(dist(rng));
    for(auto& x:k)x.bits=rne(dist(rng));
    for(auto& x:v)x.bits=rne(dist(rng));
    pack_q_group_128x4(q.data(),packed.data());
    for(size_t s=0;s<4;++s)for(size_t d=0;d<16;++d)for(size_t h=0;h<16;++h)for(size_t j=0;j<2;++j){
      require(packed[((s*16+d)*16+h)*2+j].bits==(h<4?q[h*128+s*32+2*d+j].bits:0),"pack layout");++checks;
    }
    // Test non-default score and weight row strides, and canaries.
    std::array<float,4*71+2> scores;scores.fill(123456.f);
    begin_region();qk_rowmajor_128x4(k.data(),packed.data(),scores.data()+1,71);end_region();
    for(size_t h=0;h<4;++h)for(size_t t=0;t<64;++t){
      double expected=0,mass=0;
      for(size_t d=0;d<128;++d){double p=double(to_float(q[h*128+d]))*to_float(k[t*128+d]);expected+=p;mass+=std::fabs(p);}
      require(std::fabs(scores[1+h*71+t]-expected)<=1e-4*mass+1e-6,"QK output");++checks;
    }
    require(scores.front()==123456.f&&scores.back()==123456.f,"QK overrun");
    for(size_t h=0;h<4;++h)for(size_t i=64;i<71;++i)require(scores[1+h*71+i]==123456.f,"QK stride padding");
    std::array<float,4*69> weights{};for(auto& x:weights)x=std::exp(ex(rng));
    std::array<float,16*128+2> output;output.fill(123456.f);
    begin_region();weights_times_v_128x4(v.data(),weights.data(),69,output.data()+1);end_region();
    for(size_t h=0;h<4;++h)for(size_t d=0;d<128;++d){
      double expected=0,mass=0;
      for(size_t t=0;t<64;++t){double p=double(to_float(tron::bf16{rne(weights[h*69+t])}))*to_float(v[((t/2)*128+d)*2+t%2]);expected+=p;mass+=std::fabs(p);}
      require(std::fabs(output[1+h*128+d]-expected)<=1e-4*mass+1e-6,"PV output");++checks;
    }
    for(size_t i=4*128;i<16*128;++i){require(output[1+i]==0,"PV padded rows");++checks;}
    require(output.front()==123456.f&&output.back()==123456.f,"PV overrun");
  }
  std::printf("PASS: %zu pack/QK/PV/padding comparisons across 5 seeds; stride and output guards intact. Tile operations emulated, not hardware AMX.\n",checks);
}
