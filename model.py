"""An investigation of correlated errors in local collective motion.

Base alignment rule: Vicsek et al. (1995), DOI 10.1103/PhysRevLett.75.1226.
Extension here: Gaussian angular error with fixed marginal variance and
controlled common-noise fraction. Positions use newly updated headings.
"""
from dataclasses import dataclass
import numpy as np

@dataclass(frozen=True)
class Config:
    particles:int=1100
    side:float=25.
    radius:float=1.
    speed:float=.18
    sigma:float=1.2
    steps:int=1500
    tail:int=90
    summary_window:int=500

def neighborhood(pos,radius,side):
    dx=np.abs(pos[:,0,None]-pos[None,:,0]);dy=np.abs(pos[:,1,None]-pos[None,:,1])
    dx=np.minimum(dx,side-dx);dy=np.minimum(dy,side-dy)
    return dx*dx+dy*dy<=radius*radius

def errors(common,independent,c,sigma):
    return sigma*(np.sqrt(c)*common+np.sqrt(1-c)*independent)

def simulate(c,seed,config=Config()):
    if not 0<=c<=1:raise ValueError('Correlation fraction outside [0,1]')
    rng=np.random.default_rng(seed)
    pos=rng.uniform(0,config.side,(config.particles,2))
    theta=rng.uniform(-np.pi,np.pi,config.particles)
    track=[];phases=[];mean_vectors=[];moments=[]
    for step in range(config.steps):
        mask=neighborhood(pos,config.radius,config.side)
        theta=np.arctan2(np.sum(mask*np.sin(theta)[None,:],axis=1),
                         np.sum(mask*np.cos(theta)[None,:],axis=1))
        # Always consume both draws, including at c=0 and c=1, to match
        # random streams across conditions rather than change the seed.
        common=rng.normal();independent=rng.normal(size=config.particles)
        delta=errors(common,independent,c,config.sigma)
        theta+=delta
        heading=np.column_stack((np.cos(theta),np.sin(theta)))
        velocity=config.speed*heading
        if step==0:
            assert np.allclose(np.linalg.norm(velocity,axis=1),config.speed)
            assert mask.diagonal().all() and np.array_equal(mask,mask.T)
        pos=(pos+velocity)%config.side
        if not(np.isfinite(pos).all() and np.isfinite(theta).all()):
            raise ValueError('Non-finite model state')
        mean_vectors.append(heading.mean(axis=0))
        # Mean error, mean square, mean product across DISTINCT pairs.
        moments.append([delta.mean(),np.mean(delta**2),
                        (delta.sum()**2-np.sum(delta**2))/(config.particles*(config.particles-1))])
        if step>=config.steps-config.tail:
            track.append(pos.copy());phases.append(theta.copy())
    mean_vectors=np.array(mean_vectors)
    return dict(track=np.array(track),phases=np.array(phases),
                mean_vectors=mean_vectors,polarization=np.linalg.norm(mean_vectors,axis=1),
                error_moments=np.array(moments))

def check_model():
    fixture=np.array([[.1,.1],[24.9,.1],[5.,5.]])
    assert np.array_equal(neighborhood(fixture,.3,25),np.array([[1,1,0],[1,1,0],[0,0,1]],bool))
    angles=np.array([np.pi-.1,-np.pi+.1])
    assert np.isclose(abs(np.arctan2(np.sin(angles).sum(),np.cos(angles).sum())),np.pi)
    # Common angular rotation preserves instantaneous polarization exactly.
    phases=np.array([.3,1.2,-.7,2.3])
    assert np.isclose(abs(np.mean(np.exp(1j*phases))),abs(np.mean(np.exp(1j*(phases+1.7)))))
    # Opposite coherent steps can have P=1 throughout but zero net transport.
    vectors=np.array([[1.,0.],[-1.,0.]])
    assert np.isclose(np.linalg.norm(vectors,axis=1).mean(),1)
    assert np.isclose(np.linalg.norm(vectors.mean(axis=0)),0)
    # Empirically check marginal variance and pair correlation on independent
    # noise samples, rather than assuming the generator is implemented right.
    rng=np.random.default_rng(41);common=rng.normal(size=(100000,1));ind=rng.normal(size=(100000,2))
    for c in [0.,.5,1.]:
        generated=errors(common,ind,c,1.2)
        assert np.allclose(generated.var(axis=0),1.2**2,rtol=.025)
        assert abs(np.corrcoef(generated.T)[0,1]-c)<.015
    tiny=Config(particles=12,steps=8,tail=3,summary_window=3)
    a=simulate(.5,41,tiny);b=simulate(.5,41,tiny)
    assert all(np.array_equal(a[k],b[k]) for k in a)
    print('Checks passed: periodic geometry; circular mean; common-rotation invariance; transport distinction; noise variance/correlation; reproducibility.',flush=True)

if __name__=='__main__':check_model()
