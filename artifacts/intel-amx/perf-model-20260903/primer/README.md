# One-page primer: how the AMX decode boost was predicted

Source of the Notion sub page "Predicting the AMX Decode Boost" (child of Daily notes /
Intel AMX / Primer / Estimate / Generate primer), created 2026-09-04.

- final.md: the page body in Notion-flavored Markdown (FIGURE_PLACEHOLDER marks the image block).
- fig.py: generates fig.svg and fig.png (the "three measurements, two comparisons" figure with
  the measured values; used under "4. Result"); it measures every label with PIL and prints an
  overflow list, which must be empty.
- fig-setup.py: the same layout with every number removed (used under "1. Setup"); writes
  fig-setup.svg / fig-setup.png.
- a4sim.py: rough A4 fill estimate of final.md (DejaVu metrics; pessimistic by about 10%).
  Usage: python3 a4sim.py final.md 10.5 200

Numbers come from exec/results/perf-model-20260903/model.json and perf-model/index.html
(sections 3 to 6 and 8). Regenerate the figure with: python3 fig.py
