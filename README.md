# HECSS

## High Efficiency Configuration Space Sampler

This is a Markow-Chain Metropolis-Hastings configuration space sampler.

The main sampler is in the `hecss.py` module. The calculation monitoring
functions are in the `calc_monitor.py` module. The examples are in:

* `run_sampler.py` - jupyter notebook with full sampler run example
* `monitor_stats.py` - sampling statistics notebook
* `monitor_phonons.py` - phonon convergence monitoring notebook
* `example` - directory with input data files with 3C-SiC 2x2x2 supercell

The notebooks should be opened with `open as -> notebook` in JupyterLab.

----
The whole project is Copyright (C) 2020 by Paweł T. Jochym <jochym@gmail.com>

This project is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.