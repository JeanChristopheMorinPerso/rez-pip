import os
import typing
import shutil

import rez.config
import rez.package_maker
import importlib.metadata

import rez_pip.pip
import rez_pip.utils


def make_root(variant, path):
    """Using distlib to iterate over all installed files of the current
    distribution to copy files to the target directory of the rez package
    variant
    """
    for rel_src, rel_dest in src_dst_lut.items():
        src = os.path.join(targetpath, rel_src)
        dest = os.path.join(path, rel_dest)

        if not os.path.exists(os.path.dirname(dest)):
            os.makedirs(os.path.dirname(dest))

        shutil.copyfile(src, dest)

        # if _is_exe(src):
        #     shutil.copystat(src, dest)


def createPackage(
    dist: importlib.metadata.Distribution,
    isPure: bool,
    files: list[str],
    pythonVersion: str,
    nameCasings: list[str],
    installPath: typing.Optional[str] = None,
):
    name = rez_pip.utils.pythontDistributionNameToRez(dist.name)
    version = rez_pip.utils.pythonDistributionVersionToRez(dist.version)

    requirements = rez_pip.utils.getRezRequirements(dist, pythonVersion, isPure, [])
    requires = requirements["requires"]
    variant_requires = requirements["variant_requires"]
    metadata = requirements["metadata"]

    if installPath:
        packagesPath = installPath
    else:
        packagesPath = (
            rez.config.config.release_packages_path
            if True
            else config.local_packages_path
        )

    print(f"Creating rez package for {dist.name}")
    # with rez.package_maker.make_package(name, packagesPath, make_root=make_root) as pkg:
    #     pass
