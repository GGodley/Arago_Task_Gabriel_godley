#!/usr/bin/env python3
"""Figure 2: bottleneck transition with workload size on the recommended design (Nd=8, Nm=20, S=256).

Square N x N x N, N = 64..4096. Plots the model's three lower bounds (DMA with reloads, compute,
dependency path) and the predicted time T. Also writes fig2_data.json.

    python graphs/fig2_bottleneck.py [--out DIR]
"""
import json
import matplotlib.pyplot as plt
from matplotlib.ticker import FixedLocator, NullLocator, FuncFormatter
from _common import out_dir, bounds
OUT=out_dir(desc='Figure 2')
from _common import INK, SUB, GRID, BLUE, ORANGE, AQUA
ND,NM,S=8,20,256
Ns=sorted(set([64*j for j in range(1,65)]))
B=[bounds(n,n,n,ND,NM,S) for n in Ns]
fig,ax=plt.subplots(figsize=(7.2,4.6),dpi=200)
# regime bands from model limiter
def reg(b):
    if b['tpath']>=max(b['tmat'],b['tdma'])-1e-9: return 'path'
    r=b['tdma']/b['tmat']
    return 'dma' if r>1.15 else ('matrix' if r<1/1.15 else 'bal')
b1=next(n for n,b in zip(Ns,B) if max(b['tdma'],b['tmat'])>b['tpath'])
b1=b1/ (2**0.25)
spans=[('path',56,b1),('dma',b1,1100),('bal',1100,2800),('matrix',2800,4600)]
names={'path':'dependency-\nbound','dma':'DMA-bound','matrix':'compute-\nbound','bal':'DMA ≈ compute\n(balanced)'}
shade={'path':'#eefaf6','dma':'#eef4fd','matrix':'#fef1ea','bal':'#f6f2f9'}
import math
for l,a,b in spans:
    lo=a/ (2**0.0); ax.axvspan(a,b,color=shade[l],lw=0,zorder=0)
    ax.text(math.sqrt(max(a,60)*min(b,4300)),7e4,names[l],ha='center',va='top',fontsize=7.6,color=SUB)
ax.plot(Ns,[b['tdma0'] for b in B],color=BLUE,lw=1.2,ls=':',label='DMA bound, perfect reuse (every tile loaded once)')
ax.plot(Ns,[b['tdma'] for b in B],color=BLUE,lw=2,label=f'DMA bound with S = {S} tiles (reloads)')
ax.plot(Ns,[b['tmat'] for b in B],color=ORANGE,lw=2,label='Compute bound  2Ld + ⌈W/Nm⌉Lm')
ax.plot(Ns,[b['tpath'] for b in B],color=AQUA,lw=2,label='Dependency bound (critical path)')
ax.plot(Ns,[b['T'] for b in B],color=INK,lw=1.4,ls='--',label='Model-predicted execution time T = max(bounds), best tiling',zorder=5)
ax.set_xscale('log',base=2); ax.set_yscale('log')
ax.xaxis.set_major_locator(FixedLocator([64,128,256,512,1024,2048,4096])); ax.xaxis.set_minor_locator(NullLocator())
ax.xaxis.set_major_formatter(FuncFormatter(lambda v,_:f'{int(v)}'))
ax.set_xlim(56,4600); ax.set_ylim(1,1.0e5)
ax.set_xlabel('Matrix dimension N  (square N×N×N matmul)',fontsize=9.5,color=INK)
ax.set_ylabel('Execution time (ticks, 1 tick = 128 cycles)',fontsize=9.5,color=INK)
ax.grid(True,which='major',color=GRID,lw=0.8); ax.set_axisbelow(True)
for sp in ['top','right']: ax.spines[sp].set_visible(False)
for sp in ['left','bottom']: ax.spines[sp].set_color('#bdbdbd')
ax.tick_params(colors=SUB,labelsize=8.5)
ax.set_title(f'Lower bounds and predicted time on one design: Nd = {ND}, Nm = {NM}, S = {S} tiles',fontsize=9.5,color=INK,loc='left')
ax.legend(loc='upper left',bbox_to_anchor=(0.0,0.86),fontsize=7.5,frameon=True,facecolor='white',edgecolor='none',framealpha=0.9)
plt.savefig(OUT/'fig2_bottleneck_transition.png',bbox_inches='tight',facecolor='white')
json.dump({'model':[dict(N=n,**b) for n,b in zip(Ns,B)],'note':'model only'},open(OUT/'fig2_data.json','w'),indent=1)
print('wrote',OUT/'fig2_bottleneck_transition.png')
