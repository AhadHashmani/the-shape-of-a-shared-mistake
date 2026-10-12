"""Render simulated paths directly; no generative image model is used.
python render.py --size 8700
"""
from pathlib import Path
import argparse,csv,json
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageFilter,ImageChops
from model import Config

OUT=Path(__file__).resolve().parent
CASES=[(0.,'01_independent_errors','Independent Errors'),
       (.5,'02_partial_echo','Partial Echo'),
       (1.,'03_a_shared_mistake','A Shared Mistake')]
SEED=20261011
ANCHORS=np.array([[255,185,70],[255,70,105],[172,106,255],
                  [65,140,255],[52,239,220],[182,245,110],[255,185,70]],float)

def heading_color(theta):
    h=(theta%(2*np.pi))/(2*np.pi)*6;j=np.minimum(h.astype(int),5);f=h-j
    return ANCHORS[j]*(1-f[...,None])+ANCHORS[j+1]*f[...,None]

def paths(track,phases,size):
    cfg=Config();im=Image.new('RGB',(size,size),(0,0,0));d=ImageDraw.Draw(im)
    scale=size/cfg.side;width=max(1,round(size/1050))
    for t in range(1,len(track)):
        old,new=track[t-1],track[t]
        good=np.max(np.abs(new-old),axis=1)<cfg.side/2
        # Assign each entire trajectory its FINAL heading color. This makes
        # end-state agreement legible without conflating turning over time
        # with disagreement between particles. The mapping is identical
        # in every condition and is explicitly labeled in the captions.
        colors=heading_color(phases[-1])*(.28+.72*(t/(len(track)-1))**1.5)
        for p,q,color in zip(old[good],new[good],colors[good]):
            d.line([(float(p[0]*scale),float(size-p[1]*scale)),
                    (float(q[0]*scale),float(size-q[1]*scale))],fill=tuple(map(int,color)),width=width)
    radius=max(1,size//2400)
    for p,color in zip(track[-1],heading_color(phases[-1])):
        x,y=p[0]*scale,size-p[1]*scale
        d.ellipse((x-radius,y-radius,x+radius,y+radius),fill=tuple(map(int,color)))
    glow=im.filter(ImageFilter.GaussianBlur(size/800))
    return ImageChops.add(ImageChops.add(im,glow.point(lambda a:int(a*.48))),
                          Image.new('RGB',(size,size),(6,13,23)))

def font(size):
    try:return ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc',size)
    except OSError:return ImageFont.load_default()

def scientific_plot(rows):
    # Conventional scatter/mean/SD chart: dots are independent-seed runs;
    # whiskers show BETWEEN-SEED SD, not confidence intervals.
    image=Image.new('RGB',(1800,1050),'white');d=ImageDraw.Draw(image)
    ink=(27,40,53);gray=(125,137,146)
    d.text((90,35),'Equally strong errors. Different coordination.',font=font(36),fill=ink)
    d.text((90,88),'Gaussian angular error SD = 1.2 radians; radius, speed and density held fixed',font=font(23),fill=gray)
    cs=sorted(set(float(row['correlation']) for row in rows))
    colors=[(27,139,154),(181,102,124)]
    for panel,(key,title),color in zip(range(2),[('mean_polarization','Instantaneous alignment'),('net_transport','Net directional transport')],colors):
        x0=100+panel*880;y0=200;w=690;h=650
        def point(c,v):return (x0+c*w,y0+(1-v)*h)
        d.text((x0,y0-55),title,font=font(29),fill=ink)
        for value in [0,.2,.4,.6,.8,1]:
            y=point(0,value)[1]
            d.line((x0,y,x0+w,y),fill=(229,234,237),width=2)
            d.text((x0-48,y-13),f'{value:.1f}',font=font(20),fill=gray)
        d.line((x0,y0,x0,y0+h,x0+w,y0+h),fill=ink,width=2)
        means=[]
        for c in cs:
            values=np.array([float(row[key]) for row in rows if float(row['correlation'])==c])
            mean=float(values.mean());sd=float(values.std(ddof=1)) if len(values)>1 else 0
            center=point(c,mean);means.append(center)
            lo,hi=point(c,max(0,mean-sd)),point(c,min(1,mean+sd))
            d.line((lo,hi),fill=color,width=3)
            for p in [lo,hi]:d.line((p[0]-7,p[1],p[0]+7,p[1]),fill=color,width=3)
            for i,v in enumerate(values):
                px,py=point(c,v);px+=(i-(len(values)-1)/2)*7
                d.ellipse((px-4,py-4,px+4,py+4),fill=(174,186,191))
            d.ellipse((center[0]-6,center[1]-6,center[0]+6,center[1]+6),fill=color)
            d.text((point(c,0)[0]-17,y0+h+15),f'{c:g}',font=font(20),fill=ink)
        d.line(means,fill=color,width=3)
        d.text((x0+125,y0+h+65),'Shared fraction of error variance, c',font=font(22),fill=ink)
    d.text((100,955),'Dots: independent seeds. Colored points: means. Whiskers: SD across seeds.',font=font(23),fill=ink)
    d.text((100,995),'Both metrics use the final 500 of 1,500 steps; finite-time results, not equilibrium estimates.',font=font(21),fill=gray)
    image.save(OUT/'scientific_results.png',dpi=(180,180))

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--size',type=int,default=2400);args=parser.parse_args()
    cfg=Config();metrics=[]
    for c,slug,title in CASES:
        with np.load(OUT/f'correlation_{c:g}_seed_{SEED}.npz') as saved:
            assert json.loads(str(saved['config']))['sigma']==cfg.sigma
            image=paths(saved['track'],saved['phases'],args.size)
            image.save(OUT/f'{slug}.png',dpi=(600,600));image.close()
            p=float(saved['polarization'][-cfg.summary_window:].mean())
            q=float(np.linalg.norm(saved['mean_vectors'][-cfg.summary_window:].mean(axis=0)))
        metrics.append(dict(correlation=c,title=title,alignment=p,transport=q))
        print(f'Rendered {title}: P={p:.3f}, Q={q:.3f}',flush=True)
    sheet=Image.new('RGB',(1800,840),(237,235,227));d=ImageDraw.Draw(sheet)
    d.text((25,20),'THE SHAPE OF A SHARED MISTAKE',font=font(30),fill=(25,35,44))
    d.text((25,66),'Same error strength. Same starting conditions. Different degrees of shared noise.',font=font(21),fill=(65,75,83))
    for i,((c,slug,title),m) in enumerate(zip(CASES,metrics)):
        im=Image.open(OUT/f'{slug}.png');im.thumbnail((570,570),Image.Resampling.LANCZOS)
        sheet.paste(im,(15+600*i,110));im.close()
        d.text((15+600*i,700),title,font=font(27),fill=(25,35,44))
        d.text((15+600*i,745),f'Shared fraction {c:g} · alignment {m["alignment"]:.3f}',font=font(21),fill=(65,75,83))
    d.text((25,801),'Each thread is a particle path. Hue = final heading; brightness = time. All three use the same color mapping.',font=font(19),fill=(65,75,83))
    sheet.save(OUT/'preview.jpg',quality=95)
    (OUT/'render_details.json').write_text(json.dumps(dict(
        image_resolution=[args.size,args.size],image_seed=SEED,images=metrics,
        palette=ANCHORS.tolist(),mapping='Each trajectory has the hue of its particle final absolute heading; brightness encodes trajectory time',
        window_steps=cfg.tail,display_effect='A small halo derived from the path raster; not physical emission',
        boundary='Segments crossing periodic seams are omitted',
        framing='Full periodic square, with no condition-specific rotation or crop'),indent=2))
    with (OUT/'results.csv').open() as f:rows=list(csv.DictReader(f))
    scientific_plot(rows)

if __name__=='__main__':main()
