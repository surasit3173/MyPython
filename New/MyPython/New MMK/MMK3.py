#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, glob
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import norm

# ================= STYLE =================
plt.rcParams.update({
    "font.family": "serif",
    "font.size": 11,
    "axes.titlesize": 14,
    "axes.labelsize": 12
})

# ================= CORE =================
def sen(x,y):
    slopes=[(y[j]-y[i])/(x[j]-x[i]) for i in range(len(x)) for j in range(i+1,len(x))]
    return np.median(slopes)

def mk(y):
    n=len(y)
    S=sum(np.sum(np.sign(y[i+1:]-y[i])) for i in range(n-1))
    var=n*(n-1)*(2*n+5)/18
    Z=(S-1)/np.sqrt(var) if S>0 else (S+1)/np.sqrt(var) if S<0 else 0
    p=2*(1-norm.cdf(abs(Z)))
    return Z,p

def mmk(y):
    n=len(y)
    r1=np.corrcoef(y[:-1],y[1:])[0,1]
    ne=n*(1-r1)/(1+r1) if (1+r1)!=0 else n

    S=sum(np.sum(np.sign(y[i+1:]-y[i])) for i in range(n-1))
    var=n*(n-1)*(2*n+5)/18
    var_mod=var*(n/ne)

    Z=(S-1)/np.sqrt(var_mod) if S>0 else (S+1)/np.sqrt(var_mod) if S<0 else 0
    p=2*(1-norm.cdf(abs(Z)))
    return Z,p,r1

def ci(x,y):
    slopes=[sen(x[np.random.choice(len(x),len(x),True)],
                y[np.random.choice(len(y),len(y),True)]) for _ in range(300)]
    return np.percentile(slopes,[2.5,97.5])

# ================= DATA =================
def load(f):
    df=pd.read_csv(f)
    st=[c for c in df.columns if str(c).isdigit()]
    df['date']=pd.to_datetime(df[['YEAR','MONTH','DAY']])
    df['year']=df['date'].dt.year
    df['month']=df['date'].dt.month
    return df,st

def split_season(df,st):
    ann=df.groupby('year')[st].sum()
    wet=df[df['month'].isin([5,6,7,8,9,10])].groupby('year')[st].sum()
    dry=df[df['month'].isin([11,12,1,2,3,4])].groupby('year')[st].sum()
    return {"Annual":ann,"Wet":wet,"Dry":dry}

# ================= PLOT =================
def plot_mk(x,y,st,season,out):

    slope=sen(x,y)
    c=ci(x,y)
    Z,p=mk(y)

    yfit=slope*x+(np.median(y)-slope*np.median(x))

    fig,ax=plt.subplots(figsize=(10,6))

    ax.bar(x,y,alpha=0.7,edgecolor='black')
    ax.plot(x,yfit,color='darkred',lw=2.8)
    ax.fill_between(x,yfit+c[0],yfit+c[1],alpha=0.2,color='red')

    text=(
        f"Standard Mann–Kendall\n"
        f"Z = {Z:.3f}\n"
        f"p = {p:.4f} {'*' if p<0.05 else ''}\n\n"
        f"Sen’s slope = {slope:.2f} mm yr⁻¹\n"
        f"95% CI = [{c[0]:.2f}, {c[1]:.2f}]"
    )

    ax.text(0.02,0.98,text,transform=ax.transAxes,va='top',
            bbox=dict(facecolor='white',alpha=0.9))

    ax.set_title(f"Station {st} - {season}\nStandard Mann–Kendall Trend",
                 fontweight='bold')

    ax.set_xlabel("Year")
    ax.set_ylabel("Rainfall (mm)")
    ax.grid(True,alpha=0.3)

    plt.tight_layout()
    plt.savefig(os.path.join(out,f"{st}_{season}_MK.png"),dpi=500)
    plt.close()

def plot_mmk(x,y,st,season,out):

    slope=sen(x,y)
    c=ci(x,y)
    Z,p,r1=mmk(y)

    yfit=slope*x+(np.median(y)-slope*np.median(x))

    fig,ax=plt.subplots(figsize=(10,6))

    ax.bar(x,y,alpha=0.7,edgecolor='black')
    ax.plot(x,yfit,color='navy',lw=2.8)
    ax.fill_between(x,yfit+c[0],yfit+c[1],alpha=0.2,color='blue')

    text=(
        f"Modified Mann–Kendall (MMK)\n"
        f"Z = {Z:.3f}\n"
        f"p = {p:.4f} {'*' if p<0.05 else ''}\n"
        f"ρ₁ = {r1:.2f}\n\n"
        f"Sen’s slope = {slope:.2f} mm yr⁻¹\n"
        f"95% CI = [{c[0]:.2f}, {c[1]:.2f}]"
    )

    ax.text(0.02,0.98,text,transform=ax.transAxes,va='top',
            bbox=dict(facecolor='white',alpha=0.9))

    ax.set_title(f"Station {st} - {season}\nModified Mann–Kendall Trend",
                 fontweight='bold')

    ax.set_xlabel("Year")
    ax.set_ylabel("Rainfall (mm)")
    ax.grid(True,alpha=0.3)

    plt.tight_layout()
    plt.savefig(os.path.join(out,f"{st}_{season}_MMK.png"),dpi=500)
    plt.close()

# ================= MAIN =================
def main():

    files=glob.glob("*.csv")
    out="Q2_MK_MMK_Plots"
    os.makedirs(out,exist_ok=True)

    summary=[]

    for f in files:
        df,stations=load(f)

        for st in stations:

            seasons=split_season(df,st)

            for s_name,series in seasons.items():

                series=series.dropna()
                if len(series)<10: continue

                x=series.index.values
                y=series.values

                # plots
                plot_mk(x,y,st,s_name,out)
                plot_mmk(x,y,st,s_name,out)

                # summary
                Z,p=mk(y)
                Zm,pm,r1=mmk(y)

                summary.append([st,s_name,p,pm,r1])

    pd.DataFrame(summary,
        columns=['Station','Season','p_MK','p_MMK','Rho1']
    ).to_excel(os.path.join(out,"Comparison.xlsx"),index=False)

    print("✅ DONE: MK vs MMK (Multi-season)")

if __name__=="__main__":
    main()