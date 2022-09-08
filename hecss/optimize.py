# AUTOGENERATED! DO NOT EDIT! File to edit: ../12_optimize.ipynb.

# %% auto 0
__all__ = ['get_sample_weights', 'make_sampling']

# %% ../12_optimize.ipynb 3
from scipy import stats
from matplotlib import pylab as plt
import ase.units as un
import numpy as np
import itertools 

# %% ../12_optimize.ipynb 4
flatten = itertools.chain.from_iterable

# %% ../12_optimize.ipynb 9
def get_sample_weights(data, T, sigma_scale=1.0, border=False, debug=False):
    '''
    Generate data weights making the probability distribution of `data` in 
    sample format into normal distribution corresponding to temperature `T`.
    The actual distribution traces the normal curve. Normally, no weight 
    is given to the data outside the input data range. This may skew the 
    resulting distribution and shift its parameters but avoids nasty border
    artefacts in the form of large weights given to border samples to account 
    for the rest of the domain. You can switch this behavior on by passing 
    `border` parameter (not recommended).
    
    #### Input
    * `data`        - list of samples generated by HECSS sampler ([n, i, x, f, e])
    * `T`           - temperature in kelvin
    * `sigma_scale` - scaling factor for variance. Defaults to 1.0.
    * `border`      - make border samples account for unrepresented part of domain
    * `debug`       - plot diagnostic plots
    
    #### Output (weights, index)
    * weights     - array of weights in sorted energy order
    * index       - indexing array which sorts samples by energy
    
    '''
    nat = data[0][2].shape[0]
    mu = 3*T*un.kB/2
    sigma = np.sqrt(3/2)*un.kB*T/np.sqrt(nat)   

    # Yuo can use slightly (10%) wider sigma to compensate 
    # for the missing tails below weight=1
    g = stats.norm(mu, sigma_scale*sigma)
    e = np.fromiter((s[-1] for s in data), float)
    idx = np.argsort(e)
    ridx = np.arange(len(idx))[idx]
    d = e[idx]
    if debug:
        N_bins = max(len(data)//5, 20)
        data_range = 4*sigma
        plt.hist(d, range=(mu-data_range, mu+data_range), bins=N_bins,
                 histtype='step', density=True, alpha=0.75, 
                 label='Raw data')
        plt.plot(d, -0.05*g.pdf(mu)*np.ones(d.shape), '|', 
                 alpha=max(0.01, min(1.0, 100/len(d))))
        plt.axhline(lw=1, ls=':')
        
    bb = np.zeros(len(d)+1)
    bb[1:-1] = (d[:-1]+d[1:])/2
    bb[0] = d[0]-(d[1]-d[0])/2
    bb[-1] = d[-1]+(d[-1]-d[-2])/2
    # bin widths
    bw = bb[1:]-bb[:-1]

    cdf = g.cdf(bb)
    if border:
        # make border sample account for the rest of the domain
        cdf[0]=0
        cdf[-1]=1
    
    w = cdf[1:]-cdf[:-1]
    w /= w.sum()
    if debug:
        plt.stairs(w/bw, bb, fill=False, lw=1, label='Weighted samples')
        x = np.linspace(e.min(), e.max(), 100)
        # The norm of the pdf is adiusted according to the norm
        # inside the represented domain
        plt.plot(x, g.pdf(x)/(cdf[-1]-cdf[0]), '-', label='Target')
        plt.hist(d, weights=w, range=(mu-data_range, mu+data_range), 
                 bins=N_bins, density=True, alpha=0.3, label='Weighted data')
        plt.xlim(mu-data_range, mu+data_range)
        plt.legend(loc='upper left', bbox_to_anchor=(0.6, 0.98))
        plt.show()

    return w, idx

# %% ../12_optimize.ipynb 11
def make_sampling(data, T, sigma_scale=1.0, border=False, probTH=0.25, 
                  Nmul=4, N=None, nonzero_w=True, debug=False):
    '''
    Generate new sample with normal energy probability distribution
    corresponding to temperature `T` and size of the system inferred 
    from data. The output is generated by multiplying samples 
    proportionally to the wegihts generated by `get_sample_weights`
    and assuming the final dataset will be `Nmul` times longer 
    (or the length `N` which takes precedence). If `nonzero_w` is `True`
    the data multiplyers in the range (probTH, 1) will be clamped to 1,
    to avoid losing low-probability data. This will obviously deform the
    distribution but may be beneficial for the interaction model constructed
    from the data. The data on output will be ordered in increasing energy
    and re-numbered. The configuration index is retained.
    
    #### Input
    * `data`        - list of samples generated by HECSS sampler ([n, i, x, f, e])
    * `T`           - temperature in kelvin
    * `sigma_scale` - scaling factor for variance. Defaults to 1.0.
    * `border`      - make border samples account for unrepresented part of domain
    * `probTH`      - threshold for probability (N*weight) clamping.
    * `Nmul`        - data multiplication factor. The lenght of output data will be
                      approximately `Nmul*len(data)`.
    * `N`           - approximate output data length. Takes precedence over `Nmul`
    * `nonzero_w`   - prevent zero weights for data with weights in (probTH, 1) range
    * `debug`       - plot diagnostic plots
    
    #### Output
    Weighted, sorted by energy and re-numbered samples as a new list. 
    The data in the list is just reference-duplicated, not copied.
    Thus the data elements should not be modified.
    The format is the same as the data produced by `HECSS` sampler.
    
    '''
    if N is None:
        N = int(Nmul*len(data))
        
    if Nmul>25 :
        print('Warning: You cannot generate data from thin air.\n'
              'Nmul above 25 is pointless. Doing it anyway.')

    nat = data[0][2].shape[0]
    mu = 3*T*un.kB/2
    sigma = np.sqrt(3/2)*un.kB*T/np.sqrt(nat)   

    w, idx = get_sample_weights(data, T, sigma_scale=sigma_scale, border=border, debug=debug)
    
    # Block zero weights in the +/- 3*sigma zone to not lose data
    # iw = np.round(w*nf) + (1*(np.abs(d - mu) < 3*sigma))
    iw = N*w
    if nonzero_w:
        # Don't remove low probability data, rise weights above probTH
        # This will deform (rise) the wings of the histogram
        iw[np.logical_and(probTH<iw, iw<1)]=1
    iw = np.round(iw)

    # Weight the data by multiplication of data points
    # The output will be in energy order!
    wd = []
    iwnorm = iw.sum()
    for ww, ii in zip(iw,idx):
        if ww<1:
            continue
        wd += int(ww)*[data[ii]]
    # renumber the samples
    wd = [(n,)+d[1:] for n, d in enumerate(wd)]

    if debug:
        N_bins = max(len(data)//5, 20)
        data_range = 4*sigma
        e = np.fromiter((data[i][-1] for i in idx), float)
        plt.hist(e, weights=w, range=(mu-data_range, mu+data_range), 
                 bins=N_bins, density=True, alpha=0.3,
                 label='Float weights');
        wde = np.fromiter((s[-1] for s in wd), float)
        # h, b, _ = 
        plt.hist(wde, range=(mu-data_range, mu+data_range), 
                 histtype='step', bins=N_bins, density=True, alpha=0.75,
                 label='Integer weights');
        x = np.linspace(mu-data_range, mu+data_range, 300)
        fit = stats.norm.fit(wde)
        plt.plot(x, stats.norm.pdf(x, mu, sigma), '--', 
                 label=f'$\mu$={2*mu/3/un.kB:.1f}; $\sigma$={2*sigma/3/un.kB:.1f} (Target)' )
        plt.plot(x, stats.norm.pdf(x, *fit), 
                 label=f'$\mu$={2*fit[0]/3/un.kB:.1f}; $\sigma$={2*fit[1]/3/un.kB:.1f} (Fit)' )
        plt.title('Generated weighted sample')
        skip = len(data)//2000
        skip = int(max(1, skip))
        # nf = (w[::skip]).max()
        mh = stats.norm.pdf(mu, mu, sigma)
        plt.plot(e[::skip], -0.05*mh*np.ones(e[::skip].shape), '|', color='C1', 
                 alpha=max(0.01, min(1.0, 100/len(e))))
        plt.axhline(lw=1, ls=':')
        plt.xlim(mu-data_range, mu+data_range)
        plt.legend(loc='upper left', bbox_to_anchor=(0.7, 0.95));
    
    return wd
