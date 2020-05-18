"""Phantom-build command line program."""

from pathlib import Path
from typing import Dict, List, Tuple, Union

import click
from .phantombuild import build_and_setup


@click.command()
@click.option(
    '--run-prefix',
    required=True,
    help='Prefix for Phantom run output. This option sets the Phantom output file '
    'names, e.g. prefix_00000.h5.',
)
@click.option(
    '--run-dir',
    multiple=True,
    required=True,
    help='Path to run directory. Can provide multiple run directories, one per run.',
)
@click.option(
    '--run-setup-file',
    multiple=True,
    required=True,
    help='Path to Phantom .setup file. Can provide multiple .setup files, one per run.',
)
@click.option(
    '--run-in-file',
    multiple=True,
    required=True,
    help='Path to Phantom .in file. Can provide multiple .in files, one per run.',
)
@click.option(
    '--run-job-script',
    required=False,
    help='Path to Slurm job script to schedule run. If this option is set this will '
    'schedule the run as a Slurm job.',
)
@click.option(
    '--phantom-setup',
    required=True,
    help='Phantom Makefile SETUP variable. E.g. disc or shock.',
)
@click.option(
    '--phantom-system',
    required=True,
    help='Phantom Makefile SYSTEM variable. E.g. ifort or gfortran.',
)
@click.option(
    '--phantom-extra-flags',
    required=False,
    help='Additional Phantom Makefile flags. These must be supplied as a '
    'comma-separated list. E.g. --phantom-extra-flags ISOTHERMAL=yes,DUST=yes.',
)
@click.option(
    '--phantom-dir',
    required=False,
    help='Path to Phantom source code. This specifies the location to clone, '
    'checkout, patch, and compile Phantom. Defaults to phantom in the present working '
    'directory.',
)
@click.option(
    '--phantom-version',
    required=False,
    help='Phantom version as git commit hash. Supply either the short or long form of '
    'the hash.',
)
@click.option(
    '--phantom-patch',
    multiple=True,
    required=False,
    help='Path to Phantom patch file. Can specify multiple patch files.',
)
@click.option(
    '--phantom-hdf5-dir',
    required=False,
    help='Location of HDF5 library. This option is required to compile Phantom with '
    'HDF5. This directory must contain both the HDF5 include and lib directories.',
)
def main(
    run_prefix: str,
    run_dir: Tuple[str],
    run_setup_file: Tuple[str],
    run_in_file: Tuple[str],
    phantom_setup: str,
    phantom_system: str,
    phantom_extra_flags: str,
    phantom_dir: str = None,
    phantom_version: str = None,
    phantom_patch: Tuple[str] = None,
    phantom_hdf5_dir: str = None,
    run_job_script: str = None,
):
    """Compile Phantom and setup runs.

    With phantombuild you can build and set up multiple Phantom runs
    with a single program. It allows you to clone Phantom, checkout a
    required version, apply patches, and build Phantom with any
    Makefile options. Then you can set up one or more Phantom runs, and
    optionally schedule then with Slurm.
    """
    if not (len(run_dir) == len(run_setup_file) == len(run_in_file)):
        raise ValueError(
            'must supply the same number of run-dir, run-setup-file, '
            'and run-in-file options'
        )
    if phantom_dir is None:
        phantom_dir = 'phantom'
    if phantom_patch is not None:
        _phantom_patch: List[Union[Path, str]] = list(phantom_patch)
    if phantom_extra_flags is not None:
        _phantom_extra_flags = _convert_make_options_to_dict(phantom_extra_flags)

    # Loop over runs
    for _run_dir, _setup_file, _in_file in zip(run_dir, run_setup_file, run_in_file):

        build_and_setup(
            prefix=run_prefix,
            run_dir=_run_dir,
            setup_file=_setup_file,
            in_file=_in_file,
            job_script=run_job_script,
            phantom_dir=phantom_dir,
            phantom_version=phantom_version,
            phantom_patches=_phantom_patch,
            phantom_setup=phantom_setup,
            phantom_system=phantom_system,
            phantom_extra_flags=_phantom_extra_flags,
            hdf5_dir=phantom_hdf5_dir,
        )


def _convert_make_options_to_dict(string: str) -> Dict[str, str]:
    string = string.replace(' ', '')
    return {_s.split('=')[0]: _s.split('=')[1] for _s in string.split(',')}


if __name__ == '__main__':
    main(prog_name='python -m phantombuild')
