# HECSS
> High Efficiency Configuration Space Sampler


HECSS is a Markow chain Monte-Carlo Metropolis-Hastings configuration space sampler. It provides an alternative way to create representations of systems at thermal equilibrium without running a very expensive molecular dynamics simulation. The theoretical foundation of the code are presented in the section [Background](https://jochym.gitlab.io/hecss/Background) in the [Documentation](https://jochym.gitlab.io/hecss/). More detailed examples are included in the [LAMMPS](https://jochym.gitlab.io/hecss/LAMMPS_Tutorial) and [VASP](https://jochym.gitlab.io/hecss/VASP_Tutorial) tutorials.

## A very short example

Minimal example using LAMMPS potential from the asap3 package and OpenKIM database. Here we will sample the thermodynamic distribution of 3C-SiC crystal at 300K. We start by importing required modules, define the crystal and energy/forces calculator, run the sampler and finally plot the energy distribution. 

```python
from ase.build import bulk
import asap3
from hecss.monitor import plot_stats
```

Then we define the crystal and interaction model used in the calculation. In this case we use 3x3x3 supercell of the SiC crystal in zincblende structure and describe the interaction using LAMMPS potential from the OpenKIM database and ASAP3 implementation of the calculator.

```python
model = 'Tersoff_LAMMPS_ErhartAlbe_2005_SiC__MO_903987585848_003'
cryst = bulk('SiC', crystalstructure='zincblende', a=4.38120844, cubic=True).repeat((3,3,3))
cryst.set_calculator(asap3.OpenKIMcalculator(model))
```

Then we define the sampler parameters (N -- number of samples, T -- temperature) and run it.

```python
T = 300
N = 1_000
samples = HECSS(cryst, asap3.OpenKIMcalculator(model), T).generate(N)
```

And finally we plot the histogram of the resulting energy distribution which corresponds to the thermal equilibrium distribution.

```python
plot_stats(samples, T)
```


![png](docs/images/output_9_0.png)


## Install

The HECSS package is avaliable on pypi and conda. Installation is simple, but requires a number of other packages to be installed as well. Both package menagers handle these dependencies automatically. It just run:
```
pip install hecss
```
if you prefer pip as your package manager or:
```
conda install -c jochym hecss
```
if you prefer to use conda. The channel above will be changed to conda-forge at a later date.
