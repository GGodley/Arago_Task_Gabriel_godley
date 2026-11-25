## Table 1: minimum hardware to reach the timing target

Optimizer goal: speed preset `fast`, memory preset `compact`. Common design = larger need in each resource.

| Parameter | Small (128³) | Large (2048³) | Common design |
|---|---|---|---|
| Matrix units | 2 | 20 | 20 |
| DMA units | 4 | 8 | 8 |
| Memory tiles | 16 | 256 | 256 |
| Target T* (ticks) | 14 | 3234 | |
| Execution time | 1,792 cycles (14 ticks) | 413,952 cycles (3,234 ticks) | small 1,280 cycles (10 ticks); large 413,952 cycles (3,234 ticks) |
| Utilization (matrix, DMA, memory peak) | (42.9%, 85.7%, 75.0%) | (99.7%, 95.0%, 80.9%) | small: (6.0%, 60.0%, 4.7%); large: (99.7%, 95.0%, 80.9%) |

## Figure 2 facts (Nd = 8, Nm = 20, S = 256)

- DMA-limited square sizes: 192³ to 1024³ (and some larger sizes where reloads step up)
- 4096³: matrix bound 26,018 ticks vs DMA bound 20,480 ticks -> limiter matrix
- dependency floor at 64³: 9 ticks
- dependency floor at 128³: 10 ticks
- dependency floor at 1024³: 13 ticks
- dependency floor at 4096³: 15 ticks

## Figure 3 facts (2048³, matrix units >= 90% busy)

- Nm = 32, S = 256: fewest DMA units = 11
- Nm = 32, S = 1024: fewest DMA units = 8
- Nm = 16, S = 256: fewest DMA units = 6

## Experiment 3: workload shape

| Workload | Output tiles | COMPUTEs | ACCs | Minimum DMA transfers |
|---|---:|---:|---:|---:|
| Square 256 | 16 | 64 | 48 | 48 |
| Rectangular 64x4096 (64x4096x64) | 1 | 64 | 63 | 129 |

## Figure 4: memory occupancy on 8/20/256

| Workload | Run | Avg matrix-unit util. | Avg DMA util. | Peak / mean occupancy | Tiling | Limiter |
|---|---|---|---|---|---|---|
| 128³ | 1,280 cycles (10 ticks) | 6.0% | 60.0% | 4.7% / 3.1% | block2x2 | path |
| 512³ | 12,288 cycles (96.0 ticks) | 50.0% | 100.0% | 33.9% / 31.8% | block8x8 | dma |
| 2048³ | 413,952 cycles (3,234 ticks) | 99.7% | 95.0% | 80.9% / 80.4% | block11x16 | matrix |

## Validation (model only)

| Check | Result |
|---|---|
| Hand calculation of 128³ on 20/8/256 | 4 + 2 + 4 = 10 ticks; model gives 10 -> match |
| Area under matrix-usage curve equals counted work W | max error 0.00% over 3 workloads |
| Optimizer designs re-run through the timing model meet T* | yes (full check: `python -m pytest`) |
