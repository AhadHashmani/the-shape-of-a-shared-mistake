"""Predeclared fixed-strength noise experiment; resume from cached runs.
python experiment.py --seeds 5
"""
from pathlib import Path
from dataclasses import asdict
import argparse,csv,json,time
import numpy as np
from model import Config,simulate,check_model

OUT=Path(__file__).resolve().parent
CORRELATIONS=[0.,.25,.5,.75,.9,1.]
IMAGE_CORRELATIONS=[0.,.5,1.]
SEED=20261011

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--seeds',type=int,default=5)
    args=parser.parse_args();cfg=Config();check_model();rows=[]
    # Render the three predeclared image conditions first. Supporting
    # intermediate points follow; images never select a favorable seed.
    order=IMAGE_CORRELATIONS+[c for c in CORRELATIONS if c not in IMAGE_CORRELATIONS]
    for c in order:
        for seed in range(SEED,SEED+args.seeds):
            path=OUT/f'correlation_{c:g}_seed_{seed}.npz';start=time.time()
            if path.exists():
                with np.load(path) as saved:
                    assert json.loads(str(saved['config']))==asdict(cfg),'Cached configuration mismatch'
                    data={k:saved[k] for k in ['track','phases','mean_vectors','polarization','error_moments']}
            else:
                data=simulate(c,seed,cfg)
                np.savez_compressed(path,**data,config=json.dumps(asdict(cfg)))
            pol=data['polarization'][-cfg.summary_window:]
            vectors=data['mean_vectors'][-cfg.summary_window:]
            moment=data['error_moments'].mean(axis=0)
            variance=moment[1]-moment[0]**2
            row=dict(correlation=c,seed=seed,mean_polarization=float(pol.mean()),
                     net_transport=float(np.linalg.norm(vectors.mean(axis=0))),
                     temporal_sd_polarization=float(pol.std()),
                     first_half_summary_mean=float(pol[:len(pol)//2].mean()),
                     second_half_summary_mean=float(pol[len(pol)//2:].mean()),
                     angular_error_rms=float(np.sqrt(moment[1])),
                     empirical_distinct_pair_correlation=float((moment[2]-moment[0]**2)/variance))
            assert row['net_transport']<=row['mean_polarization']+1e-10
            rows.append(row)
            print(f'c={c:g}, seed={seed}: alignment={pol.mean():.3f}, transport={row["net_transport"]:.3f}, {time.time()-start:.1f}s',flush=True)
            with (OUT/'results.tmp').open('w',newline='') as f:
                w=csv.DictWriter(f,fieldnames=list(row));w.writeheader();w.writerows(rows)
            (OUT/'results.tmp').replace(OUT/'results.csv')
    summary=[]
    for c in CORRELATIONS:
        selected=[r for r in rows if r['correlation']==c]
        entry=dict(correlation=c,runs=len(selected))
        for key in ['mean_polarization','net_transport']:
            values=np.array([r[key] for r in selected])
            entry[key]=dict(mean=float(values.mean()),sd_between_seeds=float(values.std(ddof=1)) if len(values)>1 else None,
                            minimum=float(values.min()),maximum=float(values.max()))
        summary.append(entry)
    details=dict(question='At fixed error variance, does sharing directional errors change alignment and net transport?',
                 config=asdict(cfg),correlations=CORRELATIONS,image_correlations=IMAGE_CORRELATIONS,image_seed=SEED,
                 seeds=list(range(SEED,SEED+args.seeds)),summary=summary,
                 noise_equation='delta_i = sigma * (sqrt(c) * Z_common + sqrt(1-c) * Z_i); independent standard normal Z',
                 matching='Identical initial positions/headings and underlying random draws for each seed across conditions',
                 polarization_definition='time mean of norm(mean particle unit headings)',
                 transport_definition='norm(time-and-particle mean unit headings)',
                 source='https://doi.org/10.1103/PhysRevLett.75.1226',
                 limits='1500-step finite simulations; final 500 steps summarized; no equilibrium or transition-threshold claim.')
    (OUT/'experiment_details.json').write_text(json.dumps(details,indent=2))
    print(json.dumps(summary,indent=2),flush=True)

if __name__=='__main__':main()
