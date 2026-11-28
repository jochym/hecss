# Mapping of DOFs to minimal set

> procedures for mapping degrees of freedom in the supercell to the minimal set of DOFs in the primitive unit cell.

```python
import spglib as spg
import ase
import ase.io
import numpy as np
```

```python
from ase import spacegroup as sg
from hecss.util import get_cell_data
```

```python
# cryst = ase.io.read('/home/jochym/cryst/TiO2_hecss/PBE_2x2x4/uc/CONTCAR')
# cryst = ase.io.read('/home/jochym/cryst/TiO2_hecss/PBE_Tetra/uc/CONTCAR')*(2,2,4)
# cryst = ase.io.read('/home/pastukh/Czech.calculation/sc/CONTCAR')
cryst = ase.io.read('example/VASP_3C-SiC_calculated/2x2x2/sc/CONTCAR')
```

```python
puc = spg.find_primitive(get_cell_data(cryst))
cryst_pc = ase.Atoms(cell=puc[0], scaled_positions=puc[1], numbers=puc[2], pbc=True)
sym = spg.get_symmetry(get_cell_data(cryst_pc))
symds = spg.get_symmetry_dataset(get_cell_data(cryst_pc))
spg.get_spacegroup(get_cell_data(cryst_pc))
```

```python
SG = sg.get_spacegroup(cryst_pc)
SG
```

```python
sg.get_basis(cryst_pc)
```

```python
eps = 0.01
dv = eps*np.diag(np.ones(3))
uvec = {n:v for n, v in zip((0,1,2),dv)}
uvec
```

```python
def find_key(val, dic):
    for k, v in dic.items():
        if np.allclose(v, val):
            return k
```

```python
eqdir = {}
for sp in set(symds['equivalent_atoms']):
    pci = symds['mapping_to_primitive'][sp]
    print(sp, pci, puc[1][pci], puc[2][pci])
    pos = puc[1][pci]
    m = {}
    for n, d in uvec.items(): 
        v = pos+d
        m[n]=set()
        for elp in SG.equivalent_lattice_points([v]):
            # if np.allclose(v, elp):
            #     continue
            if np.any(elp - pos < 0):
                continue
            if np.all(np.abs(elp - pos) < 2*eps):
                di = v-pos
                df = elp-pos
                m[n]|={find_key(elp-pos, uvec)}
                # print(find_key(v-pos, uvec), '->',  find_key(elp-pos, uvec))
    # print(m)
    for k, v in m.items():
        print(k, '->', sorted(v)[0])
    eqdir[sp] = np.array([sorted(v)[0] for k, v in sorted(m.items())])
print(eqdir)    
# print(SG.tag_sites(cryst_pc.get_scaled_positions()))
```

```python
at_map = symds['equivalent_atoms'][spg.get_symmetry_dataset(get_cell_data(cryst))['mapping_to_primitive']]
```

```python
dc = cryst.copy()
dc.rattle()
```

```python
dx = dc.get_positions() - cryst.get_positions()
```

```python
d_avg = {ai:dx[at_map == ai] for ai in set(at_map)}
```

```python
for ai, eqd in eqdir.items():
    for di in set(eqd):
        print(ai, di, d_avg[ai][:,eqd==di].shape, d_avg[ai][:,eqd==di].std())
```

```python
cryst.get_scaled_positions()[np.zeros((64),dtype=int)].shape
```

```python
np.array(np.zeros((64,2)), dtype=int)
```
