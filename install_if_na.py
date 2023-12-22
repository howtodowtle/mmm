import subprocess
import sys


def check_if_package_installed(package_name):
    """Checks if a package is installed in the current environment."""
    try:
        __import__(package_name)
    except ImportError:
        return False
    else:
        return True


def install_package(package_name):
    """Installs a package in the current environment."""
    subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])


def install_packages_if_not_installed(package_list, debug=False):
    """For each package in a list of packages,
    checks if a package is installed in the current environment and installs it if not.
    """
    if debug:
        print(f"Trying to install {package_list}")
    if isinstance(package_list, str):
        package_list = [package_list]
    for package_name in package_list:
        if not check_if_package_installed(package_name):
            print(f"Package '{package_name}' not installed. Installing...")
            install_package(package_name)


# def import_packages(package_list, debug=False):
#     """Imports each packet in a list of packages."""
#     if debug:
#         print(f"Trying to import {package_list}")
#     if isinstance(package_list, str):
#         package_list = [package_list]
#     for package_name in package_list:
# try:
#     globals()[package_name] = __import__(package_name)
# except ImportError:
#     print(f"Package '{package_name}' not installed. Please install it first.")
#     sys.exit()


# def install_and_import_packages(package_list, debug=False):
#     """Installs and imports each packet in a list of packages."""
#     install_packages_if_not_installed(package_list, debug=debug)
#     import_packages(package_list, debug=debug)
