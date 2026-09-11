import hashlib,json,re,math
from pathlib import Path
import numpy as np
import pandas as pd

BASE=Path(__file__).resolve().parent
src=BASE.parent/'Observed_Rain_daily_198101_201412_Prachuap Khiri Khan.csv'
raw=pd.read_csv(src)
stations=list(raw.columns[3:])
dates=pd.to_datetime(raw[['YEAR','MONTH','DAY']].rename(columns=str.lower))
annual=raw.groupby('YEAR')[stations].sum(min_count=1)
wet=raw.loc[raw.MONTH.between(5,10)].groupby('YEAR')[stations].sum(min_count=1)
dryrows=raw.loc[~raw.MONTH.between(5,10)].copy()
dryrows['season_year']=dryrows.YEAR+(dryrows.MONTH>=11)
dry=dryrows.groupby('season_year')[stations].sum(min_count=1).loc[1982:2014]
doc=json.loads((BASE/'inspection/manuscript.json').read_text(encoding='utf-8'))
def r1(y):
    z=y-y.mean()
    return float(np.dot(z[:-1],z[1:])/np.dot(z,z))
def stats(y):
    n=len(y)
    s=sum(np.sign(y[j]-y[:j]).sum() for j in range(1,n))
    cnt=np.unique(y,return_counts=True)[1]
    var=(n*(n-1)*(2*n+5)-np.sum(cnt*(cnt-1)*(2*cnt+5)))/18
    z=(s-np.sign(s))/np.sqrt(var) if s else 0
    slopes=np.sort(np.concatenate([(y[j]-y[:j])/(j-np.arange(j)) for j in range(1,n)]))
    slope=float(np.median(slopes));intercept=float(np.median(y)-slope*np.median(np.arange(n)))
    ci=1.959963984540054*np.sqrt(var)
    lo=slopes[max(0,int(round((len(slopes)-ci)/2))-1)]
    hi=slopes[min(len(slopes)-1,int(round((len(slopes)+ci)/2)))]
    return {'n':n,'tau':s/(n*(n-1)/2),'z':float(z),'p':math.erfc(abs(z)/np.sqrt(2)),'slope':float(slope),'low':float(lo),'high':float(hi),'intercept':float(intercept)}
out={'source':str(src),'sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'rows':len(raw),'date_start':str(dates.min().date()),'date_end':str(dates.max().date()),'duplicate_dates':int(dates.duplicated().sum()),'missing_values':int(raw[stations].isna().sum().sum()),'negative_values':int((raw[stations]<0).sum().sum()),'series':[],'equations':{p['p']:re.findall(r'<m:t[^>]*>(.*?)</m:t>',p['xml']) for p in doc['paragraphs'] if '<m:oMath' in p['xml']}}
for idx,(scale,frame) in enumerate([('Annual',annual),('Wet',wet),('Dry',dry)]):
    reported={r[0]:r for r in doc['tables'][idx+1][1:]}
    for st in stations:
        years=frame.index.to_numpy(); y=frame[st].to_numpy(); original=stats(y)
        t=np.arange(len(y)); detr=y-original['slope']*t; a=r1(detr)
        do_pw=bool(abs(a)>1.96/np.sqrt(len(y)))
        final=y.copy(); fy=years.copy(); detr_r=None
        if do_pw:
            t=np.arange(len(y)); detr=y-original['slope']*t; detr_r=r1(detr)
            final=detr[1:]-detr_r*detr[:-1]+original['slope']*t[1:]
            fy=years[1:]
        fs=stats(final); rep=reported[st]
        series={'station':st,'scale':scale,'years':years.tolist(),'rainfall':y.tolist(),'r1':a,'prewhitened':do_pw,'detrended_r1':detr_r,'final_years':fy.tolist(),'final_series':final.tolist(),'original':original,'final':fs,'reported':{'n':int(rep[1]),'tau':float(rep[2]),'z':float(rep[3]),'p':float(rep[4]),'slope':float(rep[5]),'low':float(rep[6]),'high':float(rep[7]),'r1':float(rep[8])}}
        series['differences']={k:fs[k]-series['reported'][k] for k in ('n','tau','z','p','slope','low','high')}
        out['series'].append(series)
(BASE/'plot_data_checks.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print('SOURCE',out['source'],out['sha256'])
print('ROWS/DATES/DUPLICATES/MISSING/NEGATIVE',out['rows'],out['date_start'],out['date_end'],out['duplicate_dates'],out['missing_values'],out['negative_values'])
print('ANNUAL MEANS',annual.mean().round(2).to_dict())
print('MAX ABS DIFFERENCE VS PUBLISHED TABLES',{k:max(abs(r['differences'][k]) for r in out['series']) for k in ('n','tau','z','p','slope','low','high')})
for r in out['series']:
    if r['prewhitened'] or r['reported']['p']<.05:
        print(r['station'],r['scale'],'r1',round(r['r1'],4),'PW',r['prewhitened'],'final',r['final'],'delta',r['differences'])
print('EQUATIONS',json.dumps(out['equations'],ensure_ascii=False))
