#!/usr/bin/env python3
"""Figure 1: methodology and model flow (model only, quasi-optimal schedule).

    python graphs/fig1_methodology.py [--out DIR]
"""
from _common import out_dir
OUT=out_dir(desc="Figure 1")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
INK='#191919'; SUB='#666666'; BLUE='#257de0'; ORANGE='#f47230'; GRID='#d9d9d9'
fig,ax=plt.subplots(figsize=(12,3.65),dpi=200); ax.set_xlim(0,12); ax.set_ylim(0.65,4.3); ax.axis('off')
def box(x,y,w,h,title,sub,ec=INK,fc='white',tc=INK,lw=1.4):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.02,rounding_size=0.12',ec=ec,fc=fc,lw=lw))
    ax.text(x+w/2,y+h-0.22,title,ha='center',va='top',fontsize=10.5,weight='bold',color=tc)
    ax.text(x+w/2,y+h-0.52,sub,ha='center',va='top',fontsize=7.6,color=SUB,linespacing=1.3)
def arrow(x0,y0,x1,y1,c=INK,ls='-',cs='arc3'):
    ax.add_patch(FancyArrowPatch((x0,y0),(x1,y1),arrowstyle='-|>',mutation_scale=12,color=c,lw=1.3,ls=ls,connectionstyle=cs))
stages=[('Workload','C = A·B\nM×K×N'),('Tiling','64×64 tiles\nm×k×n = ⌈dims/64⌉'),
 ('Dependencies','LOAD→COMPUTE→\nACC tree→SAVE'),('Scheduling','assumed quasi-optimal:\nbest tiling, overlap'),
 ('Performance','T, utilization,\nmemory, limiter'),('HW optimization','fewest Nd, Nm, S\nmeeting target T*')]
w,h,gap=1.62,1.05,0.36; x0=0.2; y=2.95
xs=[]
for i,(t,s) in enumerate(stages):
    x=x0+i*(w+gap); xs.append(x)
    box(x,y,w,h,t,s,ec=INK if i<5 else BLUE,lw=1.4 if i<5 else 2)
    if i: arrow(x-gap+0.02,y+h/2,x-0.02,y+h/2)
# lanes (model only)
mx0=xs[1]; mx1=xs[5]+w
box(mx0,0.82,mx1-mx0,1.05,'Analytical performance model',
 'operation counts (W, Sv)  →  memory reuse L(S)  →  T = max(T_mat, T_dma, T_path), minimised over tilings  →  U_m = W·Lm / (Nm·T)\nclosed form: any (M,K,N, Nd,Nm,S) in < 1 s, so it can sweep the hardware space and draw Figures 2–3',ec=BLUE,tc=BLUE)
arrow(xs[2]+w/2,y-0.03,xs[2]+w/2,1.87,c=BLUE)
ax.text(xs[2]+w/2+0.06,2.35,'counts',fontsize=7.4,color=BLUE)
arrow(xs[4]+w/2,1.87,xs[4]+w/2,y-0.03,c=BLUE)
ax.text(xs[4]+w/2+0.06,2.35,'predicts',fontsize=7.4,color=BLUE)
arrow(xs[5]+w/2,1.87,xs[5]+w/2,y-0.03,c=BLUE)
ax.text(xs[5]+w/2+0.06,2.35,'sizes',fontsize=7.4,color=BLUE)
path=OUT/'fig1_methodology_flow.png'
plt.savefig(path,bbox_inches='tight',facecolor='white')
print('wrote',path)
