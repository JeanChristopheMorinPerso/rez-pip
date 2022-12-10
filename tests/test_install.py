import installer.utils


def test_installer_schemes():
    # Make sure we support all schemes and also future prrof in case installer adds
    # new schesm to its supported list of schemes.
    assert installer.utils.SCHEME_NAMES == (
        "purelib",
        "platlib",
        "headers",
        "scripts",
        "data",
    )
