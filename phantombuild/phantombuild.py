"""Phantom build."""

import logging
import pathlib
import shutil
import subprocess
import sys
from logging import Logger
from pathlib import Path
from typing import Dict, Union


class RepoError(Exception):
    """Exception for dealing with Phantom git repository."""


class PatchError(Exception):
    """Exception for dealing with patching Phantom."""


class CompileError(Exception):
    """Exception for dealing with compiling Phantom."""


class SetupError(Exception):
    """Exception for dealing with setting up a Phantom calculation."""


class HDF5LibraryNotFound(Exception):
    """Cannot find HDF5 library."""


def _setup_logger(filename: Path = None) -> Logger:

    if filename is None:
        filename = pathlib.Path('~/.phantom-build.log').expanduser()

    logger = logging.getLogger('phantom-build')

    console_handler = logging.StreamHandler()
    file_handler = logging.FileHandler(filename, mode='a')

    console_format = logging.Formatter('%(name)s %(levelname)s: %(message)s')
    file_format = logging.Formatter(
        '%(asctime)s %(name)s %(levelname)s: %(message)s', '%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_format)
    file_handler.setFormatter(file_format)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    logger.setLevel(logging.INFO)

    return logger


LOGGER = _setup_logger()


def get_phantom(phantom_dir: Path) -> bool:
    """Get Phantom repository.

    Parameters
    ----------
    phantom_dir
        The path to the Phantom repository.

    Returns
    -------
    bool
        Success or fail as boolean.
    """
    LOGGER.info('------------------------------------------------')
    LOGGER.info('>>> Getting Phantom')
    LOGGER.info('------------------------------------------------')

    _phantom_dir = _resolved_path(phantom_dir)

    if not _phantom_dir.exists():
        LOGGER.info('Cloning fresh copy of Phantom')
        LOGGER.info(f'phantom_dir: {_nice_path(_phantom_dir)}')
        result = subprocess.run(
            [
                'git',
                'clone',
                'https://bitbucket.org/danielprice/phantom.git',
                _phantom_dir.stem,
            ],
            cwd=_phantom_dir.parent,
        )
        if result.returncode != 0:
            LOGGER.info('Phantom clone failed')
            raise RepoError('Fail to clone repo')
        else:
            LOGGER.info('Phantom successfully cloned')
    else:
        if not (
            subprocess.run(
                ['git', 'config', '--local', '--get', 'remote.origin.url'],
                cwd=_phantom_dir,
                stdout=subprocess.PIPE,
                text=True,
            ).stdout.strip()
            in [
                'git@bitbucket.org:danielprice/phantom',
                'git@bitbucket.org:danielprice/phantom.git',
                'https://bitbucket.org/danielprice/phantom',
                'https://bitbucket.org/danielprice/phantom.git',
            ]
        ):
            LOGGER.info('phantom_dir is not Phantom')
            raise RepoError('phantom_dir is not Phantom')
        else:
            LOGGER.info('Phantom already cloned')
            LOGGER.info(f'phantom_dir: {_nice_path(_phantom_dir)}')

    return True


def checkout_phantom_version(
    *, phantom_dir: Path, required_phantom_git_commit_hash: str
) -> bool:
    """Check out a particular Phantom version.

    Parameters
    ----------
    phantom_dir
        The path to the Phantom repository.
    required_phantom_git_commit_hash
        The required Phantom git commit hash.

    Returns
    -------
    bool
        Success or fail as boolean.
    """
    LOGGER.info('------------------------------------------------')
    LOGGER.info('>>> Checking out required Phantom version')
    LOGGER.info('------------------------------------------------')

    _phantom_dir = _resolved_path(phantom_dir)

    # Check git commit hash
    phantom_git_commit_hash = subprocess.run(
        ['git', 'rev-parse', 'HEAD'],
        cwd=_phantom_dir,
        stdout=subprocess.PIPE,
        text=True,
    ).stdout.strip()
    short_hash = subprocess.run(
        ['git', 'rev-parse', '--short', required_phantom_git_commit_hash],
        cwd=_phantom_dir,
        stdout=subprocess.PIPE,
        text=True,
    ).stdout.strip()
    if phantom_git_commit_hash != required_phantom_git_commit_hash:
        LOGGER.info('Checking out required Phantom version')
        LOGGER.info(f'Git commit hash: {short_hash}')
        result = subprocess.run(
            ['git', 'checkout', required_phantom_git_commit_hash], cwd=_phantom_dir
        )
        if result.returncode != 0:
            LOGGER.info('Failed to checkout required version')
            raise RepoError('Failed to checkout required version')
        else:
            LOGGER.info('Successfully checked out required version')
    else:
        LOGGER.info('Required version of Phantom already checked out')
        LOGGER.info(f'Git commit hash: {short_hash}')

    # Check if clean
    git_status = subprocess.run(
        ['git', 'status', '--porcelain'],
        cwd=_phantom_dir,
        stdout=subprocess.PIPE,
        text=True,
    ).stdout.strip()
    if not git_status == '':
        LOGGER.info('Cleaning repository')
        results = list()
        results.append(subprocess.run(['git', 'reset', 'HEAD'], cwd=_phantom_dir))
        results.append(subprocess.run(['git', 'clean', '--force'], cwd=_phantom_dir))
        results.append(subprocess.run(['git', 'checkout', '--', '*'], cwd=_phantom_dir))
        if any(result.returncode != 0 for result in results):
            LOGGER.info('Failed to clean repo')
            raise RepoError('Failed to clean repo')
        else:
            LOGGER.info('Successfully cleaned repo')

    return True


def patch_phantom(*, phantom_dir: Path, phantom_patch: Path) -> bool:
    """Apply patch to Phantom.

    Parameters
    ----------
    phantom_dir
        The path to the Phantom repository.
    phantom_patch
        The path to the patch file, if required.

    Returns
    -------
    bool
        Success or fail as boolean.
    """
    LOGGER.info('------------------------------------------------')
    LOGGER.info('>>> Applying patch to Phantom')
    LOGGER.info('------------------------------------------------')

    _phantom_dir = _resolved_path(phantom_dir)
    _phantom_patch = _resolved_path(phantom_patch)

    LOGGER.info(f'Patch file: {_nice_path(_phantom_patch)}')

    result = subprocess.run(['git', 'apply', _phantom_patch], cwd=_phantom_dir)
    if result.returncode != 0:
        LOGGER.error('Failed to patch Phantom')
        raise PatchError('Fail to patch Phantom')
    else:
        LOGGER.info('Successfully patched Phantom')

    return True


def build_phantom(
    *,
    phantom_dir: Path,
    setup: str,
    system: str,
    hdf5_location: Path = None,
    extra_makefile_options: Dict[str, str] = None,
) -> bool:
    """Build Phantom.

    Parameters
    ----------
    phantom_dir
        The path to the Phantom repository.
    setup
        The Phantom setup, e.g. 'disc', 'dustybox', etc.
    system
        The compiler as specified in the Phantom makefile, e.g.
        'gfortran' or 'ifort'.
    hdf5_location
        The path to the HDF5 installation, or if None, do not compile
        with HDF5.
    extra_makefile_options
        Extra options to pass to make. This values in this dictionary
        should be strings only.

    Returns
    -------
    bool
        Success or fail as boolean.
    """
    LOGGER.info('------------------------------------------------')
    LOGGER.info('>>> Building Phantom')
    LOGGER.info('------------------------------------------------')

    _phantom_dir = _resolved_path(phantom_dir)

    make_command = ['make', 'SETUP=' + setup, 'SYSTEM=' + system, 'phantom', 'setup']

    if hdf5_location is not None:
        _hdf5_location = _resolved_path(hdf5_location)
        if not _hdf5_location.exists():
            raise HDF5LibraryNotFound('Cannot determine HDF5 library location')
        make_command += ['HDF5=yes', 'HDF5ROOT=' + str(_hdf5_location.resolve())]

    if extra_makefile_options is not None:
        make_command += [key + '=' + val for key, val in extra_makefile_options.items()]

    build_log = _phantom_dir / 'build' / 'build_output.log'
    with open(build_log, 'w') as fp:
        result = subprocess.run(make_command, cwd=_phantom_dir, stdout=fp, stderr=fp)

    if result.returncode != 0:
        LOGGER.info('Phantom failed to compile')
        LOGGER.info(f'See "{build_log.name}" in Phantom build dir')
        raise CompileError('Phantom failed to compile')
    else:
        LOGGER.info('Successfully compiled Phantom')
        LOGGER.info(f'See "{build_log.name}" in Phantom build dir')

    return True


def setup_calculation(
    *, prefix: str, run_dir: Path, input_dir: Path, phantom_dir: Path
) -> bool:
    """Set up Phantom calculation.

    Parameters
    ----------
    prefix
        Calculation prefix, i.e. name. E.g. if prefix is 'disc' then
        Phantom snapshots will be names disc_00000.h5, etc.
    run_dir
        The path to the directory in which Phantom will output data.
    input_dir
        The path to the directory containing Phantom prefix.setup and
        prefix.in files. These files must have names corresponding to
        the prefix.
    phantom_dir
        The path to the Phantom repository.

    Returns
    -------
    bool
        Success or fail as boolean.
    """
    _run_dir = _resolved_path(run_dir)
    _input_dir = _resolved_path(input_dir)
    _phantom_dir = _resolved_path(phantom_dir)

    if not _run_dir.exists():
        _run_dir.mkdir(parents=True)

    for file in ['phantom', 'phantomsetup', 'phantom_version']:
        shutil.copy(_phantom_dir / 'bin' / file, _run_dir)

    shutil.copy(_input_dir / f'{prefix}.setup', _run_dir)
    shutil.copy(_input_dir / f'{prefix}.in', _run_dir)

    with open(_run_dir / f'{prefix}00.log', mode='w') as f:
        result = subprocess.Popen(
            ['./phantomsetup', prefix],
            cwd=_run_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
        )
        for line in result.stdout:
            sys.stdout.write(line)
            f.write(line)

    if result.returncode != 0:
        LOGGER.info('Phantom failed to set up calculation')
        raise SetupError('Phantom failed to set up calculation')
    else:
        LOGGER.info('Successfully set up Phantom calculation')

    shutil.copy(_input_dir / f'{prefix}.in', _run_dir)

    return True


def _nice_path(path: Path) -> str:
    """Convert absolute path to a string relative to '~', i.e. $HOME.

    E.g. '/Users/user/dir/file.txt' is converted to '~/dir/file.txt'.

    Parameters
    ----------
    path
        The path to convert.

    Returns
    -------
    str
        The converted path.
    """
    try:
        return '~' + str(path.relative_to(pathlib.Path.home()))
    except ValueError:
        if path.anchor == '/':
            return str(path)
        else:
            return './' + str(path)


def _resolved_path(inp: Union[str, Path]) -> Path:
    return pathlib.Path(inp).expanduser().resolve()
