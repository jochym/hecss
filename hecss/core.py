# AUTOGENERATED! DO NOT EDIT! File to edit: 00_core.ipynb (unless otherwise specified).

__all__ = ['normalize_conf', 'write_dfset', 'HECSS']

# Cell
def normalize_conf(c, base):
    '''
    Normalize the configuration `c` relative to the basic structure `base`.
    Normalization is performed by "nuwrapping" the displacements of atoms
    when they cross the periodic boundary conditions in such a way that the
    atoms are not "jumping" from one side of the cell to the other.

    E.g. if the atom at r=(0,0,0) goes to the relative position (-0.01, 0, 0)
    it is "wrapped" by PBC to the r=(0.99, 0, 0). Thus if we naiively calculate
    the displacement we will get a large positive displacement (0.99 of the cell
    vector) instead of a small negative one.

    This function reverses that process making the positions suitable for
    differentiation. The positions may be part of a continous trajectory or
    just independent configurations. This makes it impossible for described
    procedure to work if the displacements are above 1/2 of the unit cell.
    For sefety this implementation is limited to displacements < 1/3 of the
    unit cell. If any coordinate changes by more then 1/3 the function
    will rise an AssertionError exception.

    This implementation is not suitable for tracking positions in the system
    with systematic drift (e.g. long MD trajectory with non-perfect momentum
    conservation). For stronger implementation suitable for such cases look
    at dxutils package.
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

    # Return carthesian positions, fractional positions
    return dot(spos,cell), spos

# Cell

def write_dfset(fn, c, n=0):
    '''
    Append displacement-force data from the conf to the fn file.
    The format is suitable for use as ALAMODE DFSET file.
    Optionaly you can provide configuration number in n.
    File need not exist prior to first call.
    If it does not it will be created.
    '''
    i, x, f, e = c
    with open(fn, 'at') as dfset:
        print(f'# set: {n:04d} config: {i:04d}  energy: {e:8e} eV/at', file=dfset)
        for ui, fi in zip(x,f):
            print((3*'%15.7f ' + '     ' + 3*'%15.8e ') %
                        (tuple(ui/un.Bohr) + tuple(fi*un.Bohr/un.Ry)),
                        file=dfset)


# Cell

def HECSS(cryst, calc, T_goal, delta=0.05, width=0.033, maxburn=20, sigma=2,
            directory=None, reuse_base=None, verb=True):
    '''
    Run HECS sampler on the system `cryst` using calculator `calc` at target
    temperature `T_goal`. The `delta`, `width`, `maxburn` and `directory` parameters
    determine detailed aspects of the algorithm.

    This is a generator and cannot be used as regular function.
    It is intended to be used as a source of the sequence of
    configurations in the `for` loop and must be closed after
    finishing the iteration. On the other hand, the iteration
    may be continued if additional samples are required.
    The state is preserved until the .close() method is called.

    ```
    sampler = HECSS(cryst, calc, T)
    for i, x, f, e in sampler:
        process_sample(i, x, f, e)
        if i > N :
            break
    sampler.close()
    ```

    INPUT
    =====
    cryst   - ASE structure to sample
    calc    - ASE calculator to use for potential energy evaluations
    T_goal  - Target temperature in Kelvin

    delta   - speed of the adaptation - maximal change of the prior width in one step
    width   - initial width of the position distribution in Angstrom
    maxburn - max number of burn-in steps
    sigma   - width in energy sigmas of the prior energy distribution.
              This should be approx 2 (default), if your posteriors seem too narrow
              make it bigger, if too wide make it smaller (1-3 range in general).
              Too large a number makes the acceptance ratio lower.

    directory - directory for calculations and generated samples. If left as None,
                the `calc/{T_goal:.1f}K/` will be used and the generated samples will be
                stored in the `smpl/{i:04d}` subdirectories.

    reuse_base - None or the base calc directory for the ground state config
                 if None the base will be recalculated at the start of the run
                 if directory name - the energy from this dir will be reused as
                 ground state energy for the calculation.
                 Be careful to have the same VASP setup in calc and reuse_base,
                 otherwise the ground state energy and distribution wil be wrong.

    verb    - print verbose progress messages for interactive use

    OUTPUT
    ======
    The generator yields samples from the thermodynamic distribution at T=T_goal as tuples
    (index, displacement, forces, energy):
    index        - integer numbering the samples in the `smpl` subdirectory. The index may
                   repeat if the sample must be repeated in the sequence.
    displacement - set of atomic displacements (in A) in the sample (numpy array)
    forces       - set of forces (in eV/A) generated by the displacement
    energy       - potential energy of the configuration

    '''

    def smpl_print(r=0):
        if i==0:
            print(f'Burn-in sample:{k}  w:{w:.4f}  alpha:{alpha:6.4e}  dE:{(e_star-E_goal)/(2*Es):+6.2f} sigma', end='\r')
        else :
            print(f'Sample:{i-1:04d}  a:{100*i/n:5.1f}%  w:{w:.4f}  <w>:{np.mean(wl):.4f}  alpha:{alpha:6g} ' + (r*'x'), end='\r')
        sys.stdout.flush()


    if verb:
        print(f'Calculating base structure.    ', end='\r')
        sys.stdout.flush()

    nat = cryst.get_global_number_of_atoms()
    dim = (nat, 3)

    if reuse_base is not None :
        calc0 = ase.calculators.vasp.Vasp2(label='base', directory=reuse_base, restart=True)
        Ep0 = calc0.get_potential_energy()
    else :
        Ep0 = cryst.get_potential_energy()

    E_goal = 3*T_goal*un.kB/2
    Es = np.sqrt(3/2)*un.kB*T_goal/np.sqrt(nat)

    P = stats.norm.pdf
    Q = stats.norm

    w = width
    w_prev = w
    x = Q.rvs(size=dim, scale=w)
    wl = []

    i = 0
    n = 0

    if directory is None :
        basedir = f'calc/T_{T_goal:.1f}K'
    else :
        basedir = directory

    cr = ase.Atoms(numbers = cryst.get_atomic_numbers(),
                   cell=cryst.get_cell(),
                   scaled_positions=cryst.get_scaled_positions(),
                   pbc=True, calculator=calc)

    if verb:
        print(f'Calculating initial sample.    ', end='\r')
        sys.stdout.flush()

    cr.set_positions(cryst.get_positions()+x)
    cr.calc.set(directory=f'{basedir}/smpl/{i:04d}')

    e = (cr.get_potential_energy()-Ep0)/nat
    f = cr.get_forces()

    k = 0
    r = 0
    alpha = 0


    if verb:
        print(f'Starting burn-in.            ', end='\r')
        sys.stdout.flush()

    while True:
        if verb and (n>0 or k>0):
            smpl_print(r)

        x_star = Q.rvs(size=dim, scale=w)

        cr.set_positions(cryst.get_positions()+x_star)
        cr.calc.set(directory=f'{basedir}/smpl/{i:04d}')

        e_star = (cr.get_potential_energy()-Ep0)/nat
        f_star = cr.get_forces()

        alpha = P(e_star, E_goal, Es) / P(e, E_goal, Es)

        q_x = log(Q.pdf(x, w_prev)).sum()
        q_star_x_star = log(Q.pdf(x_star, w)).sum()
        q_star_x = log(Q.pdf(x, w)).sum()
        q_x_star = log(Q.pdf(x_star, w_prev)).sum()

        alpha *= exp(q_x + q_star_x_star - q_star_x - q_x_star)

        w_prev = w
        w *= 1-2*(expit((e_star-E_goal)/Es/sigma)-0.5)*delta*(10 if i==0 else 1)

        if np.random.rand() < alpha:
            x = x_star
            e = e_star
            f = f_star
            if i==0 and abs(e_star-E_goal) > 2*Es :
                # At the burn-in stage and still further then 2 sigma from target
                # Let us keep searching for correct w
                k += 1
                if k>maxburn :
                    print(f'\nError: reached maxburn ({maxburn}) without finding target energy.\n'+
                      f'You probably need to change initial width parameter to a {"higher" if (e_star-E_goal)<0 else "lower"} value.')
                    return
                continue
            else :
                # We are at sampling stage or just found the proper w
                # Either way: switch to the next sample directory (i)
                # and zero the rejection counter
                wl.append(w)
                i += 1
                n += 1
                r = 0
        else:
            # Sample rejected - nothing to yield. Try again
            r += 1
            n += 1
            continue

        if verb:
            smpl_print(r)

        yield i-1, x, f, e
