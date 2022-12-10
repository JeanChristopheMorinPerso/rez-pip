import sys
import argparse

import rez_pip.pip
import rez_pip.download


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("package", help="Package to install")
    parser.add_argument("--target", help="Target directory")

    args = parser.parse_args()

    print(args)

    packages = rez_pip.pip.get_packages(args.package)

    # import pdb

    # pdb.set_trace()
    wheels = rez_pip.download.downloadPackages(packages)
    print(f"Downloaded {len(wheels)} wheels")
