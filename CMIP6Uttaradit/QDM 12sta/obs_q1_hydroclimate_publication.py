# obs_q1_hydroclimate_publication.py
import pandas as pd, numpy as np, matplotlib.pyplot as plt
from pathlib import Path
from scipy.stats import spearmanr, kendalltau
import seaborn as sns

BOOT=1000; WET=1.0; ACF_MAX_LAG=7
WET_MONTHS=[5,6,7,8,9,10]
DRY_MONTHS=[11,12,1,2,3,4]

def find_obs():
    pats=["*Observed*.csv","*Observed*.xlsx","*observed*.csv","*observed*.xlsx"]
    f=[]
    for p in pats: f+=list(Path(".").glob(p))
    if not f: raise FileNotFoundError("Observed file not found")
    return f[0]

def load_obs(fp):
    df=pd.read_excel(fp) if str(fp).endswith(("xlsx","xls")) else pd.read_csv(fp)
    df["date"]=pd.to_datetime(dict(year=df.YEAR,month=df.MONTH,day=df.DAY))
    st=[c for c in df.columns if c not in ["YEAR","MONTH","DAY","date"]]
    return df.set_index("date")[st]

def acf(x,k):
    if len(x)<=k:return np.nan
    r,_=spearmanr(x[:-k],x[k:])
    return r
def effn(x):
    n=len(x); sig=1.96/np.sqrt(n); rs=[]
    for k in range(1,min(ACF_MAX_LAG,int(np.sqrt(n)))+1):
        r=acf(x,k)
        if not np.isnan(r) and abs(r)>=sig: rs.append(r)
    cf=1+sum(2*np.array(rs))
    return max(3,n/max(cf,1e-6))
def sen(y):
    return np.median([(y[j]-y[i])/(j-i) for i in range(len(y)-1) for j in range(i+1,len(y))])
obs=load_obs(find_obs())
out=Path("Obs_analysis"); out.mkdir(exist_ok=True)
fig=out/"Figures"; fig.mkdir(exist_ok=True)
annual=obs.resample("YS").sum()
trend=[]; sens=[]
for st in obs.columns:
 y=annual[st].dropna().values
 tau,p=kendalltau(range(len(y)),y)
 trend.append([st,sen(y),tau,p,effn(y)])
 for lag in range(1,8): sens.append([st,lag,acf(y,lag)])
# trend panel
fig1,axs=plt.subplots(3,4,figsize=(16,10))
for ax,st in zip(axs.flatten(),obs.columns):
 a=annual[st]
 ax.plot(a.index.year,a.values,lw=2)
 ax.set_title(st)
fig1.tight_layout(); fig1.savefig(fig/"Fig01_TrendPanel.png",dpi=300)
plt.close(fig1)
# heatmap
et=[]
for st in obs.columns:
 et.append([st,obs[st].quantile(.95),obs[st].quantile(.99)])
edf=pd.DataFrame(et,columns=["Station","R95p","R99p"]).set_index("Station")
plt.figure(figsize=(6,6))
plt.imshow(edf,aspect="auto"); plt.yticks(range(len(edf.index)),edf.index); plt.xticks(range(2),edf.columns)
plt.colorbar(); plt.tight_layout(); plt.savefig(fig/"Fig02_ETCCDI_Heatmap.png",dpi=300); plt.close()
pd.DataFrame(trend,columns=["Station","Sen","Tau","p","Neff"]).to_excel(out/"03_Obs_Trend.xlsx",index=False)
pd.DataFrame(sens,columns=["Station","Lag","Rho"]).to_excel(out/"07_Obs_Sensitivity.xlsx",index=False)
print("done")
