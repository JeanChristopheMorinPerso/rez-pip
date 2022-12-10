import sys
import argparse
import tempfile

import rez_pip.pip
import rez_pip.install
import rez_pip.download


def run():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("package", help="Package to install")
    parser.add_argument(
        "--target", required=True, metavar="path", help="Target directory"
    )
    parser.add_argument(
        "--python-version",
        default=f"{sys.version_info[0]}.{sys.version_info[1]}",
        metavar="version",
        help="Python version of the package",
    )
    parser.add_argument(
        "--pip",
        default="/home/jcmorin/jcmenv/aswf/rez-pip/pip.pyz",
        metavar="path",
        help="Standalone pip (https://pip.pypa.io/en/stable/installation/#standalone-zip-application)",
    )

    args = parser.parse_args()

    print(args)

    with tempfile.TemporaryDirectory(prefix="rez-pip") as tempDir:
        packages = rez_pip.pip.get_packages(args.package, args.pip, args.python_version)

        wheels = rez_pip.download.downloadPackages(packages, tempDir)
        print(f"Downloaded {len(wheels)} wheels")

        for package, wheel in zip(packages, wheels):
            print(f"Installing {package.name}-{package.version}")
            files = rez_pip.install.install(package, wheel, args.target)
            print(files)
