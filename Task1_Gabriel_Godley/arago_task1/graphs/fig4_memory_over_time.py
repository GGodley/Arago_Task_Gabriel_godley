#!/usr/bin/env python3
"""Figure 4: local-memory occupancy over time on Nd=8, Nm=20, S=256 for 128^3, 512^3 and 2048^3.

Model estimates (reloads included), not simulator traces. Each panel caption gives the run time and
the average matrix-unit utilization. Also writes fig4_data.json.

    python graphs/fig4_memory_over_time.py [--out DIR]
"""
import json
from _common import out_dir, ND, NM, S
OUT=out_dir(desc='Figure 4')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, MaxNLocator
from tilesizer import api
from tilesizer.workload import from_dims
from _common import INK, SUB, GRID, BLUE
CYC=128
fig,axes=plt.subplots(1,3,figsize=(12,4.2),dpi=200,sharey=True)
out={}
labels={128:'Small, latency floor',512:'DMA-limited regime',2048:'Large, compute-bound'}
for ax,s in zip(axes,[128,512,2048]):
    r=api.run_model(from_dims(s,s,s),nd=ND,nm=NM,S=S)
    c=r['curves']; t=[x*CYC for x in c['t']]
    ax.fill_between(t,c['mem_pct'],color=BLUE,alpha=0.15,lw=0,step=None)
    ax.plot(t,c['mem_pct'],color=BLUE,lw=2)
    ax.set_ylim(0,100); ax.set_xlim(0,t[-1])
    ax.xaxis.set_major_locator(MaxNLocator(5)); ax.xaxis.set_major_formatter(FuncFormatter(lambda v,p,big=(t[-1]>=50000): f'{v/1000:,.0f}k' if big else f'{v:,.0f}'))
    ax.set_xlabel('Elapsed cycles',fontsize=9,color=INK)
    ax.set_title(f"{s}³  ({labels[s]})",fontsize=10,color=INK,loc='left',fontweight='bold')
    ax.text(0.02,-0.30,f"Run {r['cycles']:,.0f} cycles ({r['ticks']:,.0f} ticks). Avg matrix-unit\nutilization {r['matrix_util']*100 if r['matrix_util']<=1 else r['matrix_util']:.1f}%. Peak occupancy {r['mem_peak']:.1f}%, mean {r['mem_mean']:.1f}%.",
            transform=ax.transAxes,fontsize=8,color=SUB,va='top')
    ax.grid(True,color=GRID,lw=0.8); ax.set_axisbelow(True)
    for sp in ['top','right']: ax.spines[sp].set_visible(False)
    for sp in ['left','bottom']: ax.spines[sp].set_color('#bdbdbd')
    ax.tick_params(colors=SUB,labelsize=8)
    out[s]={k:r[k] for k in ('ticks','cycles','matrix_util','dma_util','mem_peak','mem_mean','limiter','tiling','phases')}
axes[0].set_ylabel('Occupied local memory (% of 256 tiles)',fontsize=9,color=INK)
fig.suptitle('Local-memory occupancy over time on Nd = 8, Nm = 20, S = 256 (analytical model estimate incl. reloads, not a simulator trace)',fontsize=10.5,color=INK,x=0.01,ha='left')
plt.tight_layout(rect=(0,0.08,1,1))
plt.savefig(OUT/'fig4_memory_over_time.png',bbox_inches='tight',facecolor='white')
json.dump(out,open(OUT/'fig4_data.json','w'),indent=1,default=str)
print('wrote',OUT/'fig4_memory_over_time.png')
