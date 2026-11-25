#!/usr/bin/env python3
"""Figure 3: memory versus DMA trade-off for 2048^3.

For Nm in {4, 8, 16, 32, 64}: the fewest DMA units Nd whose predicted time keeps the matrix units
at least 90% busy, at each memory size S. The dot is the memory floor. Also writes fig3_data.json.

    python graphs/fig3_memory_vs_dma.py [--out DIR]
"""
import json, matplotlib
import matplotlib.pyplot as plt
from _common import out_dir, tiles, LM, predict_time
OUT=out_dir(desc='Figure 3')

def req_nd(M,nm,S,U,ndmax=512):
    m,k,n=tiles(M,M,M); W=m*n*(2*k-1)
    Tstar=W*LM/(nm*U)
    for nd in range(1,ndmax+1):
        p=predict_time(M,M,M,nd,nm,S)
        if p and p.T<=Tstar+1e-9: return nd,p
    return None,None
Ss=sorted(set(int(round(2**(x/12))) for x in range(36,133)))
d={}
for nm in [4,8,16,32,64]:
    d[nm]=[]
    for S in Ss:
        nd,p=req_nd(2048,nm,S,0.9,ndmax=128)
        d[nm].append((S,nd,p.T if p else None,p.strategy if p else None))
json.dump(d,open(OUT/'fig3_data.json','w'))
from matplotlib.ticker import FixedLocator, NullLocator
INK='#191919'; SUB='#666666'; GRID='#e6e6e6'; ORANGE='#f47230'
RAMP={4:'#8ab8ee',8:'#5a9be6',16:'#257de0',32:'#1b5ead',64:'#103c70'}
fig,ax=plt.subplots(figsize=(7.2,4.6),dpi=200)
for nm,pts in d.items():
    xs=[s for s,n,_,_ in pts if n]; ys=[n for s,n,_,_ in pts if n]
    ax.step(xs,ys,where='post',color=RAMP[nm],lw=2,solid_capstyle='round')
    ax.plot([xs[0]],[ys[0]],'o',ms=5,color=RAMP[nm],mec='white',mew=1.2,zorder=4)
    ax.text(2048*1.08,ys[-1],f'Nm = {nm}',va='center',fontsize=8.5,color=INK)
ax.set_xscale('log',base=2); ax.set_yscale('log',base=2)
ax.xaxis.set_major_locator(FixedLocator([8,16,32,64,128,256,512,1024,2048])); ax.xaxis.set_minor_locator(NullLocator())
ax.yaxis.set_major_locator(FixedLocator([1,2,4,8,16,32])); ax.yaxis.set_minor_locator(NullLocator())
ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v,_:f'{int(v)}'))
ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v,_:f'{int(v)}'))
ax.set_xlim(8,2048*1.0); ax.set_ylim(0.8,50)
ax.set_xlabel('Available on-chip memory S (tiles of 64×64)',color=INK,fontsize=9.5)
ax.set_ylabel('Required DMA units Nd',color=INK,fontsize=9.5)
ax.grid(True,color=GRID,lw=0.8); ax.set_axisbelow(True)
for sp in ['top','right']: ax.spines[sp].set_visible(False)
for sp in ['left','bottom']: ax.spines[sp].set_color('#bdbdbd')
ax.tick_params(colors=SUB,labelsize=8.5)
ax.set_title('Fewest DMA units that keep matrix units ≥ 90% busy  (2048³ matmul, analytical model)',fontsize=9.5,color=INK,loc='left')
from matplotlib.lines import Line2D
h=[Line2D([],[],color=RAMP[16],lw=2,label='model: required Nd (step)'),
   Line2D([],[],marker='o',color=RAMP[16],ls='none',mec='white',label='memory floor: no Nd suffices to the left'),]
ax.legend(handles=h,loc='upper right',fontsize=7.5,frameon=False)
plt.savefig(OUT/'fig3_memory_vs_dma.png',bbox_inches='tight',facecolor='white')
print('wrote',OUT/'fig3_memory_vs_dma.png')
