# Model equations

All quantities are in tiles (one 64x64 block) or ticks (128 cycles).

## Variables

| Symbol | Meaning |
|---|---|
| M, K, N | matrix sizes: A is MxK, B is KxN |
| m, k, n | sizes in tiles: ceil(M/64), ceil(K/64), ceil(N/64) |
| acc | 1 if k > 1 (partials must be added), else 0 |
| Nd, Nm | number of DMA units, matrix units |
| S | local memory size, in tiles |
| Ld, Lm | DMA transfer time (4 ticks), matrix op time (1 tick) |
| W | matrix commands, COMPUTE + ACC |
| Sv | SAVE commands |
| L0, L(S) | compulsory LOADs; LOADs needed with S tiles (reloads included) |
| R | tiles a tiling keeps resident (running sums or a resident panel) |
| F | slots free for tiles in flight, S - R - 1 |
| tau | slot-time one streamed tile costs, Ld + Lm(1 + acc) |

## Step 1: work (implemented in `tilesizer/counts.py`)

    COMPUTE = m n k        ACC = m n (k - 1)        W = m n (2k - 1)
    SAVE    = m n          LOAD >= L0 = k (m + n)

## Step 2: memory sets traffic (implemented in `tilesizer/counts.py`)

    block bm x bn:  L = k (m ceil(n/bn) + n ceil(m/bm)),  needs (bm + 1)(bn + 1) <= S
                    best square side b = floor(sqrt(S)) - 1,  L ~ 2 m n k / sqrt(S)
    A panel of p:   L = m k + n k ceil(m/p),  p = floor((S - 2) / (k + acc))
    L(S) = min over block, A panel, B panel
    no reloads once S >= S0 = min(m, n) (k + acc) + 2

## Step 2b: overlap overhead (implemented in `tilesizer/counts.py`)

    O = Nd + 2 Nm - 1       slots kept free so LOAD/SAVE (1 per DMA unit) and
                            COMPUTE/ACC (2 per matrix unit) can overlap
    tiling budget:  (bm + 1)(bn + 1) <= S - O,   no reloads once S >= S0 + O

  Superseded by the Little's-law check (`tilesizer/parallelism.py: little_memory`),
  which counts slots at the rates the schedule actually runs, not with every unit busy:

    M = R + (L tau + COMPUTE 2 Lm + SAVE Ld) / (T - 2 Ld) <= S,   tau = Ld + Lm (1 + acc)
    R = acc bm bn (block),  p (k + acc) (panel)

  The optimizer and `graphs/cheapest_setup.py` use it (`--overhead fixed` there gives the old check).

## Step 2c: independent-work cap (implemented in `tilesizer/parallelism.py`)

    Nm_eff <= (1 + acc) * open     open = bm bn (block) or p (panel): output tiles with a running sum in memory
                                   each running sum takes one ACC per tick, fed by one COMPUTE

## Step 3: memory sets concurrency (implemented in `tilesizer/timing.py`)

    Little's law:  DMA rate <= min(Nd / Ld, F / tau)

## Step 4: time (implemented in `tilesizer/timing.py`)

    T_mat  = 2 Ld + (1 + ceil((W - min(Nm, mn)) / Nm)) Lm    (= 2 Ld + ceil(W / Nm) Lm when Nm <= mn;
                                                              the last matrix tick runs only final operations)
    T_dma  = (L + Sv) max(Ld / Nd, tau / F)
    T_path = Ld ceil(2 / min(Nd, 2)) + Lm (1 + ceil(log2 k)) + Ld    (one DMA unit loads A and B one after the other)
    T      = min over tilings of max(T_mat, T_dma, T_path),   cycles = 128 T

## Step 5: outputs over time (implemented in `tilesizer/profile.py`)

    U_m = W Lm / (Nm T)            average matrix unit usage
    U_d = (L + Sv) Ld / (Nd T)     average DMA unit usage

    three phases:  fill [0, t_fill]  ->  steady [t_fill, T - Ld]  ->  drain [T - Ld, T]
    memory needed (steady) = R + lam_load tau + min(lam_comp 2 Lm, 2 Nm) + lam_save Ld
                             (Little's law at the steady-state arrival rates lam)
    memory with prefetch   = needed + (1 - U_d) x loads still to come, capped at S

    The area under each usage curve equals the work counted in Step 1.

## Step 6: optimization (implemented in `tilesizer/optimizer.py`)

    speed P (matrix units' worth)  ->  target T* = 2 Ld + ceil(W / P) Lm
    Nm   = ceil(W / (T* - 2 Ld))                        set by the work alone
    for every tiling t with cap_t >= Nm:
        Nd_t = ceil((L_t + Sv) Ld / T*)                 set by its transfers
        M_t  = min(Little's-law memory, mk + kn + mn)   must fit in S
    pick the fewest Nd, then the least memory

    speed ladder:  P = 1 ... P_max = W / ceil(W / (m n))   (one matrix unit per output tile), geometric steps
    memory ladder: S = 4, 8, 16, ... up to the largest s_sat
    s_min(T*): least memory that meets T*         (left edge of the region map; "tiny")
    s_sat(T*): memory past which more saves no DMA unit   (right edge)
    "compact" = the memory step closest to sqrt(s_min s_sat)
    named speeds: steady = P 1, fast = first step >= P_max^(1/3),
                  extremely fast = first step >= P_max^(2/3), max = P_max
