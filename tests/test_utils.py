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
    """ """
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


# def test_get_marker_sys_requirements(self):
#     """ """

#     def assertSysRequirements(req_str, sys_reqs):
#         self.assertEqual(rez.utils.pip.get_marker_sys_requirements(req_str), sys_reqs)

#     assertSysRequirements('implementation_name == "cpython"', ["python"])
#     assertSysRequirements('implementation_version == "3.4.0"', ["python"])
#     assertSysRequirements('platform_python_implementation == "Jython"', ["python"])
#     assertSysRequirements('platform.python_implementation == "Jython"', ["python"])
#     assertSysRequirements('python_implementation == "Jython"', ["python"])
#     assertSysRequirements('sys_platform == "linux2"', ["platform"])
#     assertSysRequirements('sys.platform == "linux2"', ["platform"])
#     assertSysRequirements('os_name == "linux2"', ["platform"])
#     assertSysRequirements('os.name == "linux2"', ["platform"])
#     assertSysRequirements('platform_machine == "x86_64"', ["arch"])
#     assertSysRequirements('platform.machine == "x86_64"', ["arch"])
#     assertSysRequirements(
#         'platform_version == "#1 SMP Fri Apr 25 13:07:35 EDT 2014"', ["platform"]
#     )
#     assertSysRequirements(
#         'platform.version == "#1 SMP Fri Apr 25 13:07:35 EDT 2014"', ["platform"]
#     )
#     assertSysRequirements('platform_system == "Linux"', ["platform"])
#     assertSysRequirements('platform_release == "5.2.8-arch1-1-ARCH"', ["platform"])
#     assertSysRequirements('python_version == "3.7"', ["python"])
#     assertSysRequirements('python_full_version == "3.7.4"', ["python"])


# def test_normalize_requirement(self):
#     """ """

#     def assertRequirements(requirement, expected, conditional_extras):
#         """ """
#         result = rez.utils.pip.normalize_requirement(requirement)
#         self.assertEqual([str(req) for req in result], [str(req) for req in expected])
#         for index, req in enumerate(result):
#             self.assertEqual(req.conditional_extras, conditional_extras[index])

#     assertRequirements("packageA", [packaging_Requirement("packageA")], [None])
#     assertRequirements(
#         "mypkg ; extra == 'dev'", [packaging_Requirement("mypkg")], [set(["dev"])]
#     )
#     assertRequirements(
#         'win-inet-pton ; (sys_platform == "win32" and python_version == "2.7") and extra == \'socks\'',
#         [
#             packaging_Requirement(
#                 'win-inet-pton; (sys_platform == "win32" and python_version == "2.7")'
#             )
#         ],
#         [set(["socks"])],
#     )

#     # PySocks (!=1.5.7,<2.0,>=1.5.6) ; extra == 'socks'
#     assertRequirements(
#         "PySocks (!=1.5.7,<2.0,>=1.5.6) ; extra == 'socks'",
#         [packaging_Requirement("PySocks!=1.5.7,<2.0,>=1.5.6")],
#         [set(["socks"])],
#     )
#     # certifi ; extra == 'secure'
#     assertRequirements(
#         "certifi ; extra == 'secure'",
#         [packaging_Requirement("certifi")],
#         [set(["secure"])],
#     )
#     # coverage (>=4.4)
#     assertRequirements(
#         "coverage (>=4.4)", [packaging_Requirement("coverage (>=4.4)")], [None]
#     )
#     # colorama ; sys_platform == "win32"
#     assertRequirements(
#         'colorama ; sys_platform == "win32"',
#         [packaging_Requirement('colorama ; sys_platform == "win32"')],
#         [None],
#     )
#     # pathlib2-2.3.4: {u'environment': u'python_version<"3.5"', u'requires': [u'scandir']}, {u'requires': [u'six']}
#     assertRequirements(
#         {"environment": 'python_version<"3.5"', "requires": ["scandir"]},
#         [packaging_Requirement('scandir; python_version < "3.5"')],
#         [None],
#     )

#     # bleach-3.1.0: {u'requires': [u'six (>=1.9.0)', u'webencodings']}
#     assertRequirements(
#         {"requires": ["six (>=1.9.0)", "webencodings"]},
#         [
#             packaging_Requirement("six (>=1.9.0)"),
#             packaging_Requirement("webencodings"),
#         ],
#         [None, None],
#     )

#     assertRequirements(
#         {"requires": ["six (>=1.9.0)", 'webencodings; sys_platform == "win32"']},
#         [
#             packaging_Requirement("six (>=1.9.0)"),
#             packaging_Requirement('webencodings; sys_platform == "win32"'),
#         ],
#         [None, None],
#     )

#     assertRequirements(
#         {"requires": ["packageA"], "extra": "doc"},
#         [packaging_Requirement("packageA")],
#         [set(["doc"])],
#     )

#     assertRequirements(
#         "mypkg ; extra == 'dev' or extra == 'doc'",
#         [packaging_Requirement("mypkg")],
#         [set(["dev", "doc"])],
#     )

#     assertRequirements(
#         'mypkg ; extra == "dev" and sys_platform == "win32"',
#         [packaging_Requirement('mypkg; sys_platform == "win32"')],
#         [set(["dev"])],
#     )

#     assertRequirements(
#         'mypkg ; sys_platform == "win32" and extra == "test"',
#         [packaging_Requirement('mypkg; sys_platform == "win32"')],
#         [set(["test"])],
#     )
