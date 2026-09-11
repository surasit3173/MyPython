import json,math
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.colors import LinearSegmentedColormap,TwoSlopeNorm
from matplotlib.path import Path as MPath
from matplotlib.patches import Polygon

BASE=Path(__file__).resolve().parent;OUT=BASE/'figures';OUT.mkdir(exist_ok=True)
data=json.loads((BASE/'plot_data_checks.json').read_text());series=data['series']
doc=json.loads((BASE/'inspection/manuscript.json').read_text(encoding='utf-8'))
stations=[r[0] for r in doc['tables'][0][1:]]
coords={r[0]:(float(r[2]),float(r[1])) for r in doc['tables'][0][1:]}
geo=json.loads((BASE/'thailand_adm1.geojson').read_text())
feature=next(f for f in geo['features'] if f['properties']['shapeName']=='Prachuap Khiri Khan Province')
def polys(f):
    g=f['geometry'];return g['coordinates'] if g['type']=='MultiPolygon' else [g['coordinates']]
province=polys(feature)
blue='#246E9E';orange='#B95B16';gray='#777777'
plt.rcParams.update({'font.family':'Times New Roman','font.size':9.5,'axes.titlesize':10,'axes.labelsize':9.5,'xtick.labelsize':9,'ytick.labelsize':9,'axes.linewidth':.75,'lines.linewidth':.8,'text.color':'black','axes.labelcolor':'black','xtick.color':'black','ytick.color':'black','legend.fontsize':9,'savefig.facecolor':'white','figure.facecolor':'white','mathtext.fontset':'stix'})
def save(fig,n):
    fig.savefig(OUT/f'Figure_{n}.png',dpi=600)
    fig.savefig(OUT/f'Figure_{n}.tiff',dpi=600,pil_kwargs={'compression':'tiff_lzw'})
    fig.savefig(OUT/f'Figure_{n}.pdf')
    plt.close(fig)
def get(st,sc):return next(s for s in series if s['station']==st and s['scale']==sc)
def tidy(ax):
    ax.grid(axis='y',color='#DDDDDD',lw=.35);ax.set_axisbelow(True)
    ax.tick_params(width=.75,length=3)
def boundary(ax,fill='#F1F1ED'):
    for p in province:ax.add_patch(Polygon(p[0],closed=True,fc=fill,ec='#555555',lw=.65,zorder=2))
    ax.set_xlim(99.08,100.10);ax.set_ylim(10.90,12.76);ax.set_aspect(1/math.cos(math.radians(11.8)))
    ax.set_xticks([99.2,99.6,100.0]);ax.set_xticklabels(['99.2°E','99.6°E','100.0°E'])
    ax.set_yticks([11.0,11.5,12.0,12.5]);ax.set_yticklabels(['11.0°N','11.5°N','12.0°N','12.5°N'])
def north(ax):ax.annotate('N',xy=(99.98,12.50),xytext=(99.98,12.66),ha='center',va='center',arrowprops={'arrowstyle':'-|>','lw':.75,'color':'black'})
def scalebar(ax):
    dx=20/(111.32*math.cos(math.radians(11.1)));x=99.68;y=11.04
    ax.plot([x,x+dx],[y,y],color='black',lw=1.5,zorder=6);ax.text(x+dx/2,y+.035,'20 km',ha='center',fontsize=9,zorder=6)

# Figure 1: clean, traceable locator replacing source's untraceable elevation layer.
fig=plt.figure(figsize=(6.2,5.2));ax=fig.add_axes([.36,.10,.55,.82]);boundary(ax);north(ax);scalebar(ax)
offset={'500005':(-.35,-.055),'500006':(.12,.045),'500008':(-.28,.04),'500301':(-.30,.10),'500202':(.08,.035),'500002':(.07,-.07),'500004':(.1,-.015),'500007':(-.32,-.015),'500201':(.1,-.025),'500001':(.10,.015),'500003':(.10,-.015),'500009':(.10,.01)}
for st,(x,y) in coords.items():
    ax.plot(x,y,'o',ms=4,mec='black',mfc=blue,mew=.5,zorder=5)
    dx,dy=offset[st];ax.annotate(st,(x,y),(x+dx,y+dy),fontsize=9,ha='left',va='center',arrowprops={'arrowstyle':'-','lw':.45,'color':'#444444'},zorder=6)
ax.set_title('Prachuap Khiri Khan rainfall stations',pad=8)
ins=fig.add_axes([.02,.42,.26,.46]);
for f in geo['features']:
    for p in polys(f):ins.add_patch(Polygon(p[0],fc=orange if f is feature else '#ECECEA',ec='#666666',lw=.2))
ins.set_xlim(97,106);ins.set_ylim(5.5,21);ins.set_aspect('equal');ins.axis('off');ins.set_title('Thailand',fontsize=10)
fig.text(.03,.26,'●  Rain-gauge station',fontsize=9.5)
fig.text(.03,.18,'Coordinates: Table 1\nBoundary: geoBoundaries\nOpenStreetMap contributors',fontsize=9,linespacing=1.5)
save(fig,1)

# Figure 2: same ranges across all panels and 9+ pt at actual width.
fig,axs=plt.subplots(1,3,figsize=(6.2,4.2),sharey=True)
for ax,sc,title in zip(axs,['Annual','Wet','Dry'],['(a) Annual','(b) Wet season','(c) Dry season']):
    for i,st in enumerate(stations):
        s=get(st,sc)['reported'];sig=s['p']<.05;c=orange if sig else gray
        ax.plot([s['low'],s['high']],[i,i],color=c,lw=1)
        ax.plot(s['slope'],i,'o' if sig else 'o',ms=4,mfc=c if sig else 'white',mec=c,mew=.8)
    ax.axvline(0,color='black',ls='--',lw=.65);ax.set_xlim(-16,18);ax.set_xticks([-15,0,15]);ax.set_title(title,pad=8);tidy(ax)
axs[0].set_yticks(range(12));axs[0].set_yticklabels(stations);axs[0].invert_yaxis();axs[0].set_ylabel('Station')
fig.supxlabel("Sen's slope (mm/year)",y=.12,fontsize=9.5)
fig.legend(handles=[Line2D([],[],color=orange,marker='o',lw=1,label='p < 0.05'),Line2D([],[],color=gray,marker='o',mfc='white',lw=1,label='p ≥ 0.05')],loc='lower center',ncol=2,frameon=False,bbox_to_anchor=(.53,.005))
fig.subplots_adjust(left=.16,right=.99,top=.88,bottom=.24,wspace=.12)
save(fig,2)

# Figure 3: seven original observations, slopes/interval bounds from manuscript tables.
order=[('500002','Annual'),('500002','Dry'),('500004','Dry'),('500006','Dry'),('500003','Wet'),('500005','Wet'),('500006','Wet')]
fig,axs=plt.subplots(4,2,figsize=(6.2,8.0))
for ax,(st,sc),letter in zip(axs.flat,order,'abcdefg'):
    s=get(st,sc);x=np.array(s['years']);y=np.array(s['rainfall']);r=s['reported'];t=x-np.median(x);center=np.median(y)
    lower=np.minimum(center+r['low']*t,center+r['high']*t);upper=np.maximum(center+r['low']*t,center+r['high']*t)
    ax.fill_between(x,lower,upper,color=orange,alpha=.14,lw=0)
    ax.plot(x,y,'o-',color='#333333',ms=2.1,lw=.65)
    ax.plot(x,center+r['slope']*t,color=orange,lw=1.15)
    ax.set_title(f'({letter}) {st}  {sc.lower()}'+(' season' if sc!='Annual' else ''),loc='left',pad=5)
    ax.text(.03,.92,f"β = {r['slope']:+.2f} mm/year; p = {r['p']:.3f}",transform=ax.transAxes,va='top',fontsize=8.8,bbox={'fc':'white','ec':'none','pad':1,'alpha':.9})
    ax.set_xlim(1980,2015);ax.set_xticks([1981,1990,2000,2014]);ax.set_ylabel('Rainfall (mm)');ax.set_xlabel('Year' if sc!='Dry' else 'Dry-season ending year');tidy(ax)
axs[3,1].axis('off');axs[3,1].legend(handles=[Line2D([],[],color='#333333',marker='o',ms=3,lw=.75,label='Observed rainfall'),Line2D([],[],color=orange,lw=1.15,label="Sen's trend line"),Line2D([],[],color=orange,lw=7,alpha=.2,label='95% slope envelope')],loc='upper left',frameon=False)
axs[3,1].text(.02,.36,'Envelope reflects slope uncertainty,\nnot a rainfall prediction interval.\n\nPointwise tests at α = 0.05.',transform=axs[3,1].transAxes,va='top',fontsize=9)
fig.subplots_adjust(left=.11,right=.98,top=.96,bottom=.06,hspace=.66,wspace=.31)
save(fig,3)

# Figure 4: remove dual axes; keep transformation visible with clear mean alignment.
s=get('500003','Wet');fig,axs=plt.subplots(2,1,figsize=(6.2,5.2),sharex=True,sharey=True)
for ax,x,y,st,title,c in [(axs[0],np.array(s['years']),np.array(s['rainfall']),s['original'],'(a) Original wet-season series','#333333'),(axs[1],np.array(s['final_years']),np.array(s['final_series'])+np.mean(s['rainfall'])-np.mean(s['final_series']),s['final'],'(b) TFPW series mean-aligned for display',blue)]:
    t=x-np.median(x);center=np.median(y)
    ax.plot(x,y,'o-',color=c,ms=2.5,lw=.8);ax.plot(x,center+st['slope']*t,color=orange,lw=1.1)
    ax.set_title(title,loc='left',pad=5);ax.set_ylabel('Rainfall (mm)');ax.set_ylim(450,1450);tidy(ax)
    ax.text(.02,.91,f"n = {st['n']}; Z = {st['z']:.3f}; p = {st['p']:.3f}; β = {st['slope']:+.2f} mm/year",transform=ax.transAxes,va='top',fontsize=9,bbox={'fc':'white','ec':'none','alpha':.9,'pad':1})
axs[1].set_xlabel('Year');axs[1].set_xticks([1981,1985,1990,1995,2000,2005,2010,2014]);axs[1].set_xlim(1980,2015)
fig.text(.11,.035,'Detrended lag-1 r = 0.542; screening threshold = ±0.336',fontsize=9)
fig.subplots_adjust(left=.11,right=.985,top=.93,bottom=.15,hspace=.28)
save(fig,4)

# Figure 5: signed IDW in geographic coordinates, no inferred spatial significance.
fig,axs=plt.subplots(1,3,figsize=(6.2,4.7),sharey=True)
gx=np.linspace(99.08,100.10,220);gy=np.linspace(10.90,12.76,330);xx,yy=np.meshgrid(gx,gy);points=np.c_[xx.ravel(),yy.ravel()]
mask=np.zeros(len(points),dtype=bool)
for poly in province:
    part=MPath(poly[0]).contains_points(points)
    for hole in poly[1:]:part &= ~MPath(hole).contains_points(points)
    mask|=part
xy=np.array([coords[st] for st in stations]);dist=(points[:,None,0]-xy[None,:,0])**2+(points[:,None,1]-xy[None,:,1])**2;weights=1/np.maximum(dist,1e-12)
cmap=LinearSegmentedColormap.from_list('rainfall_signed',[blue,'#FAFAF6',orange]);norm=TwoSlopeNorm(vmin=-10,vcenter=0,vmax=10)
for ax,sc,letter in zip(axs,['Annual','Wet','Dry'],'abc'):
    boundary(ax,'none');slopes=np.array([get(st,sc)['reported']['slope'] for st in stations]);z=weights@slopes/weights.sum(axis=1);z[~mask]=np.nan
    ax.pcolormesh(xx,yy,z.reshape(xx.shape),cmap=cmap,norm=norm,shading='auto',zorder=1,rasterized=True)
    for st in stations:
        x,y=coords[st];r=get(st,sc)['reported'];sig=r['p']<.05
        ax.scatter(x,y,s=62 if sig else 16,marker='*' if sig else 'o',c=[r['slope']],cmap=cmap,norm=norm,edgecolors='black',linewidths=.55,zorder=5)
        if sig:
            dx,dy={'500002':(-.34,-.075),'500003':(-.38,.05),'500004':(.08,-.08),'500005':(-.43,-.08),'500006':(.08,.10)}[st]
            ax.annotate(st,(x,y),(x+dx,y+dy),fontsize=8.5,va='center',arrowprops={'arrowstyle':'-','lw':.45},zorder=6)
    north(ax);ax.set_title(f'({letter}) {sc}'+(' season' if sc!='Annual' else ''),pad=6);ax.tick_params(labelsize=8,length=2)
    ax.set_xticks([99.3,99.9]);ax.set_xticklabels(['99.3°E','99.9°E'])
scalebar(axs[0]);fig.subplots_adjust(left=.09,right=.985,top=.90,bottom=.20,wspace=.10)
cax=fig.add_axes([.24,.095,.52,.025]);cb=fig.colorbar(plt.cm.ScalarMappable(norm=norm,cmap=cmap),cax=cax,orientation='horizontal',ticks=[-10,-5,0,5,10]);cb.set_label("Sen's slope (mm/year)",labelpad=1)
fig.text(.50,.014,'★ p < 0.05     ○ p ≥ 0.05     Background: illustrative IDW',ha='center',fontsize=9)
save(fig,5)
print('EXPORTED',len(list(OUT.glob('*.tiff'))),'TIFF figures at 600 DPI')
