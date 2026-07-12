# Pre-work is at ../pre-work/intel-amd-comparison/, please:
     1. Read pass2_writeup.md to understand current state
     2. Skim pass1_outline.md to see the outline
  The pre-work focused on comparing the performance between
  Intel system and AMD system. Focus on Intel system since
  Intel is the focus of this project.
  pre-work/ folder has a static capture of comparison between AMD and pre-SNC3 Intel,
  you can reference it for AMD data, the Intel data are to be measured at this project.

# The Chips and Cheese article URL is https://chipsandcheese.com/p/a-look-into-intel-xeon-6s-memory

# Resources
## Intel spec / data sheets:
   - A Google Drive MCP connector is configured (authenticated as jhan@positron.ai);
     source folder is https://drive.google.com/drive/folders/1ZyM7wOS8Ec9OWGGO3igTk6pBzqbwpNUK
   - A full-text cache of all 10 docs already exists at
     /scratch/jhan/Intel_vs_AMD/refs/  (*.txt + *.pdf + INDEX.md, rebuilt by
     refs/build_intel_refs.py). A copy is bundled in claude-workspace/refs/.
     Use the cache; do not re-download unless it is missing.

# The project's purpose is to measure whether SNC/3 shrinks
  the Intel-vs-AMD performance gap seen in pre-work (where Intel ran SNC/3 OFF and
  was sub-par to AMD). 

# SNC mode is RUNTIME-DETECTED, never assumed.
  `cat /sys/devices/system/node/online`:  0-5 = SNC/3 (3 nodes/socket);
  0-1 = SNC-OFF (1 node/socket = the whole socket). The machine may be in EITHER
  mode when you start. Read it first and branch every node-indexed test on it.

# This project measures BOTH modes on THIS machine with the SAME tools, by running
  the suite once per mode. The user flips the BIOS SNC setting + reboots between
  passes (a disruptive change the USER performs — the agent never changes SNC mode
  and never blocks waiting for it; it runs whatever mode is live and tags results).
  The SNC3-vs-SNC-OFF comparison is therefore between two LIVE, same-machine,
  identical-methodology passes.

# Pre-work is the cross-VENDOR reference (AMD EPYC 9654) and an independent
  cross-check on the SNC-OFF numbers — it is NO LONGER the source of the pre-SNC3
  baseline (this project measures pre-SNC3 live). If only one mode has been run so
  far, fill the other mode's comparison columns from the most recent same-machine
  pass for that mode (cite its date) and add a Todo for the missing pass.

