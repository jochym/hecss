# HECSS Examples

This is a simple example of 3C-SiC crystal to use for testing.
This directory contains all files required to test and learn HECSS.

## Directories:

### VASP_3C-SiC

This directory is for learning/testing with VASP, which is more complicated and requires non-free VASP calculator and proper setup.
- 1x1x1 - crystalographic unit cell for quick tests
- 2x2x2 - 2x2x2 supercell for better quality, but slower, tests

#### Usage

The simplest way to use these examples is to run the CLI interface to HECSS: `hecss_sampler` command.
For more information and examples see the VASP tutorial and the rest of the docs.

1. Copy one of sc directories (sc_1x1x1 recommended for starters) to some directory outside of the source tree.
2. Copy the phon directory to the same place (they should be side-by-side).
3. Create `run-calc` script in the same directory (look into scripts directory for a template)
4. Execute your `run-calc` in the sc directory to make sure it works.
5. Create `T300` directory for results
6. Run `hecss_sampler -W T300 -T 300 -N 5 sc_1x1x1` in the same directory - this should create five samples
   in the `T300/smpl` directory and DFSET file in the `T300` directory


