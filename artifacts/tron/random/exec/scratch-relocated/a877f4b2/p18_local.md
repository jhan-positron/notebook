Arm® C1-Nano Core Technical Reference Manual Document ID: 107753_0002_06_en
Issue 06
The C1-Nano core

## **1. The C1-Nano core**


The C1-Nano core is a high-efficiency, low-power, and area-efficient product that implements the
Arm [®] v9.3-A architecture. The Arm [®] v9.3-A architecture extends the architecture defined in the
Arm [®] v8‑A architectures up to Arm [®] v8.8‑A.


The C1-Nano core is implemented inside a C1-DSU cluster. It is connected to the C1-DynamIQ [™]
Shared Unit (DSU) that behaves as a full interconnect with L3 cache and snoop control. This
connection configuration is also used in systems with different types of cores where the C1-Nano
core is the high-efficiency core.


C1-Nano cores are implemented inside a block called a complex, which contains up to two cores.
Within a dual-core complex, the Vector Processing Unit (VPU), the L2 Translation Lookaside Buffer
(TLB), and the L2 cache logic are shared between cores.


The following figure shows an example of a dual-core complex configuration.


**Figure 1-1: Example configuration with a C1-Nano dual-core complex**


DynamIQ cluster


C1-Nano complex 0


C1-Nano core 0



Shared logic

|VPU|L2 TLB|
|---|---|
|VPU|L2<br>cache|



C1-Nano core 1


C1-SME2



DynamIQ

cluster
shared

logic



~~External memory interface~~


~~Interrupt interface~~

Power management

and clock control

~~_Design for Test_~~ ~~(DFT)~~


~~CoreSight infrastructure~~


~~Utility bus~~





You can also configure a complex that contains a single C1-Nano core with dedicated logic. You
can configure your systems so that all cores are configured in single-core complexes. This type of
configuration improves performance but at the cost of area efficiency.


The following figure shows an example of a cluster with single-core complexes.


Copyright © 2023–2025 Arm Limited (or its affiliates). All rights reserved.
Non-Confidential
Page **18** of **914**


