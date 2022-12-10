import argparse
import tempfile

import rez_pip.pip
import rez_pip.install
import rez_pip.download


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("package", help="Package to install")
    parser.add_argument("--target", help="Target directory")

    args = parser.parse_args()

    print(args)

    with tempfile.TemporaryDirectory(prefix="rez-pip") as tempDir:
        packages = rez_pip.pip.get_packages(args.package)

        wheels = rez_pip.download.downloadPackages(packages, tempDir)
        print(f"Downloaded {len(wheels)} wheels")

        for package, wheel in zip(packages, wheels):
            print(f"Installing {package.name}-{package.version}")
            rez_pip.install.install(package, wheel, args.target)
