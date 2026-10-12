"""Verify the completed experiment and prepare descriptions + project ZIP.
Run AFTER experiment.py and render.py have completed.
"""
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
import csv,hashlib,json,platform
import numpy as np
import PIL
from PIL import Image
from experiment import CORRELATIONS,SEED
from render import CASES,scientific_plot

OUT=Path(__file__).resolve().parent
details=json.loads((OUT/'experiment_details.json').read_text())
rendering=json.loads((OUT/'render_details.json').read_text())
with (OUT/'results.csv').open() as f:rows=list(csv.DictReader(f))
expected={(c,s) for c in CORRELATIONS for s in range(SEED,SEED+5)}
actual={(float(r['correlation']),int(r['seed'])) for r in rows}
assert actual==expected and len(rows)==30,'Need all 30 predeclared runs'
assert len(details['seeds'])==5
for r in rows:
    assert 0<=float(r['net_transport'])<=float(r['mean_polarization'])+1e-10<=1+1e-10
    assert abs(float(r['angular_error_rms'])/1.2-1)<.08,'Unexpected error-strength mismatch'
    assert abs(float(r['empirical_distinct_pair_correlation'])-float(r['correlation']))<.08
for c,slug,title in CASES:
    with Image.open(OUT/f'{slug}.png') as im:
        assert im.size==(8700,8700),'Need native 8700-pixel exports'
        im.verify()
scientific_plot(rows)

def val(c,key):
    return float(next(r for r in rows if float(r['correlation'])==c and int(r['seed'])==SEED)[key])

captions=f'''THE SHAPE OF A SHARED MISTAKE
Three computational images investigating how unreliable local decisions
affect collective motion.

SERIES DESCRIPTION
How much does it matter whether errors are private or shared? These images
follow 1,100 simulated particles that align with nearby neighbors while
receiving random directional perturbations. Error strength, speed, density,
sensing radius, starting conditions, and observation window stay fixed.
Only the fraction of error variance shared across particles changes. Each
thread traces a particle's path; its hue represents the particle's final
heading, while brightness increases toward the end of the path. A shared
error can leave particles strongly aligned even as the group keeps turning.
The images were generated computationally in Python using an extension of
an established collective-motion model.

1. INDEPENDENT ERRORS
Every particle receives its own independent directional perturbation.
The many-colored threads reveal diverse final headings, despite local
alignment interactions. In this run, mean alignment is {val(0,'mean_polarization'):.3f} and normalized
net directional transport is {val(0,'net_transport'):.3f}, measured over the final 500 simulation
steps. The image shows the final 90 steps. Gaussian angular error has a
standard deviation of 1.2 radians. Generated computationally in Python.

2. PARTIAL ECHO
Half the error variance is shared across all particles, while the other
half remains independent. The individual error strength is unchanged.
Patches of similarly colored paths reveal partial agreement in final
headings. Mean alignment is {val(.5,'mean_polarization'):.3f} and normalized net directional transport
is {val(.5,'net_transport'):.3f} over the final 500 steps. The image traces the final 90 steps.
This intermediate condition reveals a different organization from either
fully private or fully shared perturbations. Generated in Python.

3. A SHARED MISTAKE
All particles receive the same directional perturbation at each time step.
Its standard deviation is still 1.2 radians. The nearly unified hues show
strong agreement in final headings, while the looping paths reveal motion
that repeatedly changes direction. Mean alignment is {val(1,'mean_polarization'):.3f}, but normalized
net directional transport is only {val(1,'net_transport'):.3f} over the final 500 steps. The group
can move together without maintaining one direction over time. The image
shows the final 90 steps of a Python simulation.

CREATION DETAILS FOR ALL THREE
Medium: computational simulation and digital trajectory rendering.
Where generated: Python; an independent UT Austin data science visualization
project. No physical capture location applies to these computational images.
Creator name: [your preferred credited name]
Contact email: [your email]
Affiliation: UT Austin, Master of Science in Data Science.
The scientific focus on noise was selected by the entrant. Simulation code,
analysis, rendering, and caption drafts were developed with Codex assistance;
describe personal contributions and assistance accurately in the final entry.

MODEL CREDIT
Local alignment rule based on Vicsek et al. (1995), Physical Review Letters
75, 1226-1229, https://doi.org/10.1103/PhysRevLett.75.1226.
This project replaces uniform angular noise with correlated Gaussian noise
and advances positions using updated headings. It presents an independent
finite simulation experiment, rather than a claim of a new law of nature.
'''
(OUT/'submission_captions.txt').write_text(captions)

summary_text=[]
for item in details['summary']:
    p=item['mean_polarization'];q=item['net_transport']
    summary_text.append(f"c={item['correlation']:g}: mean alignment {p['mean']:.3f}, seed SD {p['sd_between_seeds']:.3f}; mean transport {q['mean']:.3f}, seed SD {q['sd_between_seeds']:.3f}")
notes='''SCIENTIFIC QUESTION
At fixed individual error strength, how does sharing directional errors
change moment-to-moment agreement and sustained directional transport?

CONTROLLED EXPERIMENT
Six predeclared shared fractions c = 0, .25, .5, .75, .9, 1.
Five independent seeds per fraction; 30 runs total.
Across conditions at each seed, both initial states and underlying random
number draws match. The displayed cases were preselected as c = 0, .5, 1
with seed 20261011. They were not selected from the most favorable runs.

Each run has 1,100 particles, a periodic square of side 25 model length
units, interaction radius 1, speed .18 units per step, 1,500 steps, and
Gaussian angular-error SD sigma = 1.2 radians. Images use the last 90
states (89 connecting segments); statistics use the final 500 states.

NOISE FORMULA
delta_i(t) = sigma [sqrt(c) Z_common(t) + sqrt(1-c) Z_i(t)].
All Z are independent standard normal draws, except for the shared draw
explicitly reused across particles at a given time. Each delta_i has
variance sigma^2 at every c. The correlation between distinct particles'
unwrapped errors is c. Common draws are refreshed at every time step.
Finite-sample RMS and estimated pair correlations are included in results.csv.

TWO METRICS
Let m(t) be the mean particle unit-heading vector at time t.
Alignment P = average_t |m(t)|.
Directional transport Q = |average_t m(t)|.
Both range from zero to one, and Q <= P. P measures agreement at a moment;
Q also requires persistence in direction across the analysis window.
Transport is measured from heading/velocity vectors, not from wrapped
position differences across the periodic seam.

WHY SHARED NOISE IS DIFFERENT
Rotating all heading vectors by one common angle preserves their
instantaneous alignment magnitude exactly. Independent rotations can
reduce agreement. Spatial neighborhoods still evolve, and finite-run
collective dynamics are measured rather than assumed.

RESULTS ACROSS FIVE SEEDS
'''+ '\n'.join(summary_text)+'''

READING THE ARTWORK
Hue is each particle's FINAL heading along its ENTIRE displayed path.
It is not the instantaneous heading at every earlier segment.
Brightness increases with time; old trails are darker.
All images use the same cyclic palette, width rule, scale, full-domain
framing, time window, and trajectory-derived halo. No condition-specific
crop, rotation, palette choice, or synthetic particle path is introduced.
The halo is a presentation effect rather than physical emission.
Overlaid paths can occlude one another; these are not calibrated density maps.

LIMITS
These are finite-time results at one density, radius, speed and error SD.
They do not establish equilibrium, a critical threshold, a universal law,
or a behavioral explanation for a particular organism. Error or "mistake"
means a perturbation from the local mean heading; no externally correct
target direction is defined. Phase and density patterns are simulated.
First/second half means of the summary window are retained in results.csv
so remaining temporal evolution can be inspected.

CHECKS
Independent fixtures check periodic neighbor geometry, circular averaging,
common-rotation invariance, and the distinction between agreement and net
transport. A separate 100,000-sample test checks noise variance and pair
correlation. Tiny simulations check exact seeded reproducibility.
Every run checks finite states; initial velocity magnitudes, self-inclusion
and symmetric neighborhoods are checked. Package verification checks all
30 runs, empirical noise statistics, P/Q bounds, and final image dimensions.

REPRODUCING
Install Python dependencies from requirements.txt.
1. python model.py
2. python experiment.py --seeds 5
3. python render.py --size 8700
4. python package.py
Cached NPZ runs are checked against configuration before reuse. Delete or
move matching NPZ files if you change the model implementation itself.
Primary artworks are three PNGs at 8700 x 8700 pixels with 600-dpi metadata.
preview.jpg and scientific_results.png are supporting material, not three
additional competition entries. Preview labels use Helvetica when available;
primary artworks contain no typography and do not depend on that font.

SOURCE AND CONTRIBUTION
Base model: https://doi.org/10.1103/PhysRevLett.75.1226.
The entrant selected noise as the scientific focus. Code, experiment design,
analysis, renderings and draft descriptions were developed with Codex
assistance. Personal credit and contributions should be described accurately.
'''
(OUT/'project_notes.txt').write_text(notes)
(OUT/'requirements.txt').write_text(f'numpy=={np.__version__}\nPillow=={PIL.__version__}\n')
files=[p for p in OUT.iterdir() if p.is_file() and p.name!='manifest.json']
manifest=dict(python=platform.python_version(),numpy=np.__version__,pillow=PIL.__version__,
              experiment_runs=30,image_resolution=[8700,8700],
              files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)})
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2))
target=OUT.parent/'the_shape_of_a_shared_mistake.zip'
with ZipFile(target,'w',ZIP_DEFLATED,compresslevel=2) as archive:
    for p in sorted(OUT.iterdir()):
        if p.is_file():archive.write(p,Path('the_shape_of_a_shared_mistake')/p.name)
print('Verified and packaged: '+str(target),flush=True)
print('\n'.join(summary_text),flush=True)
