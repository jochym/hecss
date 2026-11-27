"""Helper functions"""


__all__ = ['normalize_conf', 'load_dfset', 'get_dfset_len', 'write_dfset', 'calc_init_xscale']

import itertools

from ase import units as un
from numpy import array, dot, loadtxt

flatten = itertools.chain.from_iterable

def select_asap_model(comp='SiC'):
    '''
    Select the latest working OpenKIM model whose name contains `comp`.

    Models are tried with ASAP3 and those that fail to load are skipped,
    since names and availability are not stable across installations.
    Returns the model name, or `None` when no working model is found.
    '''
    import asap3
    models = []
    for pot in [pot for pot in asap3.OpenKIMavailable() if comp in pot]:
        try :
            calc = asap3.OpenKIMcalculator(pot)
            models.append(pot)
        except asap3.AsapError :
            pass
    if models :
        model = sorted(models, key=lambda m: m.split('_')[3])[-1]
    else :
        model = None
    return model

def create_asap_calculator(model):
    """Create a fresh ASAP3 calculator for the named OpenKIM model."""
    import asap3
    return asap3.OpenKIMcalculator(model)

def normalize_conf(c, base):
    '''
    Normalize configuration `c` relative to the reference structure `base`.

    Atomic displacements crossing periodic boundaries are unwrapped so that
    they remain small and differentiable: an atom moving from (0,0,0) to
    (-0.01, 0, 0) is stored by PBC as (0.99, 0, 0), which would otherwise
    look like a displacement of almost one full cell vector.

    The result is `(cartesian_positions, fractional_positions)`. Displacements
    above half a cell are ambiguous; for safety this implementation raises
    `AssertionError` when any fractional component exceeds 1/3. It is not
    suitable for trajectories with systematic drift; consider the `dxutils`
    package for that case.
    '''
    cell = base.get_cell()
    spos = c.get_scaled_positions()
    bspos = base.get_scaled_positions()

    # Unwrap the displacement relative to base
    sdx = spos - bspos
    sht = (sdx < -0.5)*1 - (sdx > 0.5)*1
    sdx += sht

    # Check if fractional displacements are below 1/3
    assert (abs(sdx) < 1/3).all()

    # Calculate unwrapped spos
    spos = bspos + sdx

    # Return Cartesian positions, fractional positions
    return dot(spos,cell), spos

def load_dfset(fn):
    """Load an ALAMODE DFSET file into a list of sample tuples.

    Each tuple is `(number, configuration, positions, forces, energy)` with
    positions in Angstrom and forces in eV/Angstrom.
    """
    N = get_dfset_len(fn)
    dfset = loadtxt(fn).reshape(N,-1,6)
    nat=dfset.shape[1]
    
    confs = []
    sets = []
    es = []
    n = 0
    with open(fn) as dff:
        for l in dff:
            if 'set:' not in l:
                continue
            s, _, c, _, e = l.split()[2:7]
            s = int(s)
            c = int(c)
            e = float(e)
            confs.append((n,c, 
                          dfset[n,:,:3]*un.Bohr, 
                          dfset[n,:,3:]*un.Ry/un.Bohr, e))
            n += 1
            
    return confs

def get_dfset_len(fn):
    """Return the number of configurations in a DFSET file, or 0 if absent."""
    try :
        with open(fn) as dfset:
            return len([l for l in dfset if 'set:' in l])
    except FileNotFoundError:
            return 0

def write_dfset(fn, c, comment=''):
    '''
    Append one sample to `fn` in ALAMODE DFSET format.

    `c` is a `(number, configuration, positions, forces, energy)` tuple;
    positions and forces are converted from ASE units to the units used by
    ALAMODE. `comment`, when given, is written as a `##` line before the
    sample. The file is created if it does not exist.
    '''
    n, i, x, f, e = c
    with open(fn, 'at') as dfset:
        if comment:
            print('##', comment, file=dfset)
        print(f'# set: {n:04d} config: {i:04d}  energy: {e:8e} eV/at', file=dfset)
        for ui, fi in zip(x,f):
            print((3*'%15.7f ' + '     ' + 3*'%15.8e ') % 
                        (tuple(ui/un.Bohr) + tuple(fi*un.Bohr/un.Ry)), 
                        file=dfset)

def calc_init_xscale(cryst, xsl, skip=None):
    '''
    Calculate initial xscale amplitude correction coefficients 
    from the history exported from the previous calculation 
    (with `xscale_list` argument). 
    
    INPUT
    -----
    cryst : ASE structure 
    xsl   : List of amplitude correction coefficients. The shape of 
            each element of the list must be `cryst.get_positions().shape`
    skip  : Number of samples to skip at the start of the xsl list
    
    OUTPUT
    ------
    Array amplitude correction coefficients with the same shape as
    `cryst.get_positions()`. Pass it as `xscale_init` to `HECSS.sample()`.
    '''
    from numpy import array, ones
    elmap = cryst.get_atomic_numbers()
    if skip is not None:
        skip = min(skip, len(xsl)//2)
    xs = array(xsl)[skip:]
    xscale = ones(xs[0].shape)
    for i, el in enumerate(set(elmap)):
        xscale[elmap==el] = xs[:,elmap==el,:].mean()
    return xscale

def get_cell_data(cell):
    """Convert an ASE cell to a spglib cell tuple.

    Returns `(lattice, positions, numbers)` with the lattice rows in spglib
    order, fractional positions and atomic numbers.
    """
    
    lattice = array(cell.get_cell().T, dtype="double", order="C")
    positions = array(cell.get_scaled_positions(), dtype="double", order="C")
    numbers = array(cell.get_atomic_numbers(), dtype="intc")
    
    return (lattice, positions, numbers)
