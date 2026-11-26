# Fixed ids of the page asimov-c1nano-perf.html

## Short version

- Every section, subsection, figure and table of the page has one fixed id, listed here.
- A section author passes these ids to `S.h3`, `S.fig(..., id_=)` and `S.table(..., id_=)`, and names another part of the page with `S.xref(id)`, `S.figref(id)` or `S.tabref(id)`.
- `ids.py` in this folder holds the same list for the generator, which prints a note for a subsection id that differs.

## Rules

- The `h2` of a section is written by the generator from `KEY` and `TITLE` of the module. Its id is the section key. The title below is a suggestion.
- The `h3` ids and their order are fixed. The title may be reworded. A subsection that the author drops must be reported, because another section may link to it.
- Figure codes and table codes are those of the outline in section 5 of the critic sheet (`facts/critic.md`). The id is `fig-<code>` or `tab-<code>`.
- Never type a section, figure, table or reference number. `S.render` writes the numbers.
- In a partial build (`--only`, or a section module that does not exist yet) a link to an id that is not on the page is written as plain text. In a full build it raises.

## Short version of the page

- Written by `sec_setup.short_version(D, V, S)`. Figure: `fig-H1` (the headline bars).

## 1. Section key `setup`: What was measured

| h3 id | Title | Number |
|---|---|---|
| `setup-chip` | The chip under test | 1.1 |
| `setup-mesh` | The mesh | 1.2 |
| `setup-boots` | The boots | 1.3 |
| `setup-latency-test` | The latency test | 1.4 |
| `setup-bandwidth-test` | The bandwidth test | 1.5 |
| `setup-counters` | Counters, clock, integrity | 1.6 |

- Figures: `fig-S1`, `fig-S2`, `fig-S3`, `fig-S4`.
- Tables: `tab-TS1`, `tab-TS2`, `tab-TS3`, `tab-TS4`.

## 2. Section key `glance`: Results at a glance

| h3 id | Title | Number |
|---|---|---|
| `glance-numbers` | Numbers to quote | 2.1 |
| `glance-repeat` | Repeatability | 2.2 |

- Figures: `fig-G1`.
- Tables: `tab-TG1`, `tab-TG2`.

## 3. Section key `latency`: Latency by footprint

| h3 id | Title | Number |
|---|---|---|
| `lat-footprint` | By footprint, CPU 2 | 3.1 |
| `lat-levels` | Which level serves each footprint | 3.2 |
| `lat-l3` | What an L3-served load costs | 3.3 |
| `lat-dram` | The DRAM-model row | 3.4 |
| `lat-clusters` | The other clusters | 3.5 |
| `lat-order` | Address order and the prefetchers | 3.6 |
| `lat-pfoff` | Random chains with the prefetchers off | 3.7 |

- Figures: `fig-L1`, `fig-L2`, `fig-L3`, `fig-L4`, `fig-L5`, `fig-L6`.
- Tables: `tab-TL1`, `tab-TL2`, `tab-TL3`, `tab-TL4`, `tab-TL5`, `tab-TL6`.

## 4. Section key `bandwidth`: One-core bandwidth

| h3 id | Title | Number |
|---|---|---|
| `bw-1core` | One core by footprint | 4.1 |
| `bw-l1forms` | Inside the L1: two forms | 4.2 |
| `bw-variants` | The read stream and the prefetchers | 4.3 |
| `bw-stream` | Stream against chain | 4.4 |

- Figures: `fig-B1`, `fig-B2`, `fig-B3`.
- Tables: `tab-TB1`, `tab-TB2`, `tab-TB3`, `tab-TB4`, `tab-TB5`.

## 5. Section key `multicore`: Multi-core bandwidth

| h3 id | Title | Number |
|---|---|---|
| `mc-clusters` | One core per cluster, all eight | 5.1 |
| `mc-writers` | Writer placement | 5.2 |
| `mc-pair` | Two cores of one cluster, small footprints | 5.3 |

- Figures: `fig-M1`, `fig-M2`.
- Tables: `tab-TM1`, `tab-TM2`, `tab-TM3`.

## 6. Section key `ocm`: OCM latency and bandwidth

| h3 id | Title | Number |
|---|---|---|
| `ocm-quote` | The OCM row to quote | 6.1 |
| `ocm-page` | One line per page: not an OCM latency | 6.2 |
| `ocm-region` | Per region and per mesh step | 6.3 |
| `ocm-pagemap` | Page mapping | 6.4 |
| `ocm-bw` | OCM bandwidth | 6.5 |

- Figures: `fig-O1`, `fig-O2`, `fig-O3`, `fig-O4`, `fig-O5`.
- Tables: `tab-TO1`, `tab-TO2`, `tab-TO3`, `tab-TO4`, `tab-TO5`, `tab-TO6`.

## 7. Section key `mesh`: Mesh counters

| h3 id | Title | Number |
|---|---|---|
| `mesh-own` | Each command reached its own node | 7.1 |
| `mesh-dram` | DRAM-backed commands | 7.2 |

- Figures: `fig-N1`.
- Tables: `tab-TN1`, `tab-TN2`.

## 8. Section key `open`: Open items

| h3 id | Title | Number |
|---|---|---|
| `open-l3` | The read stream and the L3 state | 8.1 |
| `open-items` | Other open items | 8.2 |
| `open-notmeasured` | Not measured | 8.3 |

- Figures: `fig-P1`, `fig-P2`.
- Tables: `tab-TP1`, `tab-TP2`, `tab-TP3`, `tab-TP4`.

## After the sections

- `words`: "Words used here" (section 9, written by the shell).
- `references`: "References" (section 10, written by the shell).

## Counts

- 32 subsections, 26 figures (with `fig-H1`), 32 tables.
