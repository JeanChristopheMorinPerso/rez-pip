import typing

import pytest
import packaging.version
import packaging.specifiers
import packaging.requirements
import rez.vendor.version.version
import rez.vendor.version.requirement

import rez_pip.utils


# @pytest.fixture
# def distPath():
#     cls.settings = {}
#     cls.dist_path = cls.data_path("pip", "installed_distributions")


def test_pythontDistributionNameToRez():
    """ """
    assert rez_pip.utils.pythontDistributionNameToRez("asd") == "asd"
    assert rez_pip.utils.pythontDistributionNameToRez("package-name") == "package_name"


@pytest.mark.parametrize(
    "version,expected",
    [
        ["1.0.0", "1.0.0"],
        ["0.9", "0.9"],
        ["1.0a1", "1.0.a1"],
        ["1.0.post1", "1.0.post1"],
        ["1.0.dev1", "1.0.dev1"],
        ["1.0+abc.7", "1.0-abc.7"],
        ["1!2.3.4", "2.3.4"],
    ],
)
def test_pythonDistributionVersionToRez(version: str, expected: str):
    assert rez_pip.utils.pythonDistributionVersionToRez(version) == expected


def test_test_pythonDistributionVersionToRez_raises():
    with pytest.raises(packaging.version.InvalidVersion):
        rez_pip.utils.pythonDistributionVersionToRez("2.0b1pl0")


@pytest.mark.parametrize(
    "pythonSpec,rezReq",
    [
        ["==1", "1+<1.1"],
        [">1", "1.1+"],
        ["<1", "<1"],
        [">=1", "1+"],
        ["<=1", "<1.1"],
        ["~=1.2", "1.2+<2"],
        ["~=1.2.3", "1.2.3+<1.3"],
        ["!=1", "<1|1.1+"],
        ["!=1.2", "<1.2|1.2.1+"],
        ["!=1.*", "<1|2+"],
        ["!=1.2.*", "<1.2|1.3+"],
        [">=1.2.a1", "1.2.a1+"],
        ["==1.*", "1"],
        [">=2.6, !=3.0.*, !=3.1.*, !=3.2.*, <4", "2.6+<3.0|3.3+<4"],
    ],
)
def test_pythonSpecifierToRezRequirement(pythonSpec: str, rezReq: str):
    pythonSpecObj = packaging.specifiers.SpecifierSet(pythonSpec)
    assert rez_pip.utils.pythonSpecifierToRezRequirement(
        pythonSpecObj
    ) == rez.vendor.version.version.VersionRange(rezReq)


def test_pythonSpecifierToRezRequirement_raises():
    with pytest.raises(ValueError):
        rez_pip.utils.pythonSpecifierToRezRequirement(
            packaging.specifiers.SpecifierSet("<2,>3")
        )


@pytest.mark.parametrize(
    "pythonReq,rezReq",
    [
        ["package>1", "package-1.1+"],
        ["package", "package"],
        ["package[extra]", "package"],
    ],
)
def test_packaging_req_to_rez_req(pythonReq: str, rezReq: str):
    assert rez_pip.utils.pythonReqToRezReq(
        packaging.requirements.Requirement(pythonReq)
    ) == rez.vendor.version.requirement.Requirement(rezReq)


# def test_is_pure_python_package(self):
#     """ """
#     dpath = rez.vendor.distlib.database.DistributionPath([self.dist_path])
#     dist = list(dpath.get_distributions())[0]

#     self.assertTrue(rez.utils.pip.is_pure_python_package(dist))


# def test_is_entry_points_scripts_package(self):
#     """ """
#     dpath = rez.vendor.distlib.database.DistributionPath([self.dist_path])
#     dist = list(dpath.get_distributions())[0]
#     self.assertFalse(rez.utils.pip.is_entry_points_scripts_package(dist))


# def test_convert_distlib_to_setuptools_wrong(self):
#     """ """
#     dpath = rez.vendor.distlib.database.DistributionPath([self.dist_path])
#     dist = list(dpath.get_distributions())[0]
#     dist.key = "random-unexisting-package"

#     self.assertEqual(rez.utils.pip.convert_distlib_to_setuptools(dist), None)


@pytest.mark.parametrize(
    "marker,expected",
    [
        ['implementation_name == "cpython"', ["python"]],
        ['implementation_version == "3.4.0"', ["python"]],
        ['platform_python_implementation == "Jython"', ["python"]],
        ['platform.python_implementation == "Jython"', ["python"]],
        ['python_implementation == "Jython"', ["python"]],
        ['sys_platform == "linux2"', ["platform"]],
        ['sys.platform == "linux2"', ["platform"]],
        ['os_name == "linux2"', ["platform"]],
        ['os.name == "linux2"', ["platform"]],
        ['platform_machine == "x86_64"', ["arch"]],
        ['platform.machine == "x86_64"', ["arch"]],
        ['platform_version == "#1 SMP Fri Apr 25 13:07:35 EDT 2014"', ["platform"]],
        ['platform.version == "#1 SMP Fri Apr 25 13:07:35 EDT 2014"', ["platform"]],
        ['platform_system == "Linux"', ["platform"]],
        ['platform_release == "5.2.8-arch1-1-ARCH"', ["platform"]],
        ['python_version == "3.7"', ["python"]],
        ['python_full_version == "3.7.4"', ["python"]],
    ],
)
def test_convertMarker(marker: str, expected: typing.List[str]):
    assert rez_pip.utils.convertMarker(marker) == expected


@pytest.mark.parametrize(
    "requirement,expected,conditional_extras",
    [
        ["packageA", [packaging.requirements.Requirement("packageA")], [None]],
        [
            "mypkg ; extra == 'dev'",
            [packaging.requirements.Requirement("mypkg")],
            [set(["dev"])],
        ],
        [
            'win-inet-pton ; (sys_platform == "win32" and python_version == "2.7") and extra == \'socks\'',
            [
                packaging.requirements.Requirement(
                    'win-inet-pton; (sys_platform == "win32" and python_version == "2.7")'
                )
            ],
            [set(["socks"])],
        ],
        # PySocks (!=1.5.7,<2.0,>=1.5.6) ; extra == 'socks'
        [
            "PySocks (!=1.5.7,<2.0,>=1.5.6) ; extra == 'socks'",
            [packaging.requirements.Requirement("PySocks!=1.5.7,<2.0,>=1.5.6")],
            [set(["socks"])],
        ],
        # certifi ; extra == 'secure'
        [
            "certifi ; extra == 'secure'",
            [packaging.requirements.Requirement("certifi")],
            [set(["secure"])],
        ],
        # coverage (>=4.4)
        [
            "coverage (>=4.4)",
            [packaging.requirements.Requirement("coverage (>=4.4)")],
            [None],
        ],
        # colorama ; sys_platform == "win32"
        [
            'colorama ; sys_platform == "win32"',
            [packaging.requirements.Requirement('colorama ; sys_platform == "win32"')],
            [None],
        ],
        # pathlib2-2.3.4: {u'environment': u'python_version<"3.5"', u'requires': [u'scandir']}, {u'requires': [u'six']}
        [
            {"environment": 'python_version<"3.5"', "requires": ["scandir"]},
            [packaging.requirements.Requirement('scandir; python_version < "3.5"')],
            [None],
        ],
        # bleach-3.1.0: {u'requires': [u'six (>=1.9.0)', u'webencodings']}
        [
            {"requires": ["six (>=1.9.0)", "webencodings"]},
            [
                packaging.requirements.Requirement("six (>=1.9.0)"),
                packaging.requirements.Requirement("webencodings"),
            ],
            [None, None],
        ],
        [
            {"requires": ["six (>=1.9.0)", 'webencodings; sys_platform == "win32"']},
            [
                packaging.requirements.Requirement("six (>=1.9.0)"),
                packaging.requirements.Requirement(
                    'webencodings; sys_platform == "win32"'
                ),
            ],
            [None, None],
        ],
        [
            {"requires": ["packageA"], "extra": "doc"},
            [packaging.requirements.Requirement("packageA")],
            [set(["doc"])],
        ],
        [
            "mypkg ; extra == 'dev' or extra == 'doc'",
            [packaging.requirements.Requirement("mypkg")],
            [set(["dev", "doc"])],
        ],
        [
            'mypkg ; extra == "dev" and sys_platform == "win32"',
            [packaging.requirements.Requirement('mypkg; sys_platform == "win32"')],
            [set(["dev"])],
        ],
        [
            'mypkg ; sys_platform == "win32" and extra == "test"',
            [packaging.requirements.Requirement('mypkg; sys_platform == "win32"')],
            [set(["test"])],
        ],
    ],
)
def test_normalizeRequirement(
    requirement: typing.Union[str, typing.Dict[str, typing.Any]],
    expected: typing.List[packaging.requirements.Requirement],
    conditional_extras: typing.List[typing.Optional[typing.Set[str]]],
):
    result = rez_pip.utils.normalizeRequirement(requirement)
    assert [str(req) for req in result] == [str(req) for req in expected]
    for index, req in enumerate(result):
        assert req.conditional_extras == conditional_extras[index]
