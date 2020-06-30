# AUTOGENERATED! DO NOT EDIT! File to edit: 00_core.ipynb (unless otherwise specified).

__all__ = ['normalize_conf']

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