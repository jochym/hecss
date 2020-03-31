#!/usr/bin/env python3

from ase.calculators.vasp import Vasp2
import ase.units as un
import sys
import hecss

calc0 = Vasp2(restart=sys.argv[1]+'/')
E0 = calc0.get_potential_energy()
nat = calc0.atoms.get_global_number_of_atoms()

for n, d in enumerate(sys.argv[2:]):
    print(f'Processing: {d}', file=sys.stderr)
    try: 
        calc = Vasp2(restart=d+'/')
    except IndexError:
        print(f'Problem with {d}', file=sys.stderr)
        continue
    e = (calc.get_potential_energy()-E0)/nat
    print(f'# set: {n+1:04d} config: {d}  energy: {e:8e} eV/at')
    u = hecss.normalize_conf(calc.atoms, calc0.atoms)[0] - calc0.atoms.get_positions()
    f = calc.get_forces()
    for ui, fi in zip(u,f):
        print((3*'%15.7f ' + '     ' + 3*'%15.8e ') % 
                    (tuple(ui/un.Bohr) + tuple(fi*un.Bohr/un.Ry)) )