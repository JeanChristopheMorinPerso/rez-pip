import sys
import typing
import logging
import dataclasses

if sys.version_info >= (3, 10):
    import importlib.metadata as importlib_metadata
else:
    import importlib_metadata

import rez.system
import packaging.version
import packaging.specifiers
import packaging.requirements
import rez.vendor.version.version
import rez.vendor.version.requirement

_LOG = logging.getLogger(__name__)


@dataclasses.dataclass
class RequirementsDict:
    requires: typing.List[str]
    variant_requires: typing.List[str]
    metadata: typing.Dict[str, typing.Any]


def pythontDistributionNameToRez(name: str) -> str:
    """Convert a distribution name to a rez compatible name.

    The rez package name can't be simply set to the dist name, because some
    pip packages have hyphen in the name. In rez this is not a valid package
    name (it would be interpreted as the start of the version).
    Example: my-pkg-1.2 is 'my', version 'pkg-1.2'.

    :param name: Distribution name to convert.
    :returns: Rez-compatible package name.
    """
    return name.replace("-", "_")


def pythonDistributionVersionToRez(version: str) -> str:
    """Convert a distribution version to a rez compatible version.

    The python version schema specification isn't 100% compatible with rez.

    1: version epochs (they make no sense to rez, so they'd just get stripped
       of the leading N!;
    2: python versions are case insensitive, so they should probably be
       lowercased when converted to a rez version.
    3: local versions are also not compatible with rez

    The canonical public version identifiers MUST comply with the following scheme:
    [N!]N(.N)*[{a|b|rc}N][.postN][.devN]

    Epoch segment: N! - skip
    Release segment: N(.N)* 0 as is
    Pre-release segment: {a|b|c|rc|alpha|beta|pre|preview}N - always lowercase
    Post-release segment: .{post|rev|r}N - always lowercase
    Development release segment: .devN - always lowercase

    Local version identifiers MUST comply with the following scheme:
    <public version identifier>[+<local version label>] - use - instead of +

    :param version: The distribution version to be converted.
    :returns: Rez-compatible equivalent version string.
    :raises packaging.version.InvalidVersion: when a PEP440 incompatible version is detected.

    .. _Core utilities for Python packages:
        https://packaging.pypa.io/en/latest/version/
    """
    pkgVersion = packaging.version.parse(version)

    # the components of the release segment excluding epoch or any
    # prerelease/development/postrelease suffixes
    rezVersion = ".".join(str(i) for i in pkgVersion.release)

    if pkgVersion.is_prerelease and pkgVersion.pre:
        # Additional check is necessary because dev releases are also considered
        # prereleases pair of the prerelease phase (the string "a", "b", or "rc")
        # and the prerelease number the following conversions take place:
        # * a --> a
        # * alpha --> a
        # * b --> b
        # * beta --> b
        # * c --> c
        # * rc --> rc
        # * pre --> rc
        # * preview --> rc
        #
        phase, number = pkgVersion.pre
        rezVersion += "." + phase + str(number)

    if pkgVersion.is_postrelease:
        # this attribute will be the postrelease number (an integer)
        # the following conversions take place:
        # * post --> post
        # * rev --> post
        # * r --> post
        #
        rezVersion += ".post" + str(pkgVersion.post)

    if pkgVersion.is_devrelease:
        # this attribute will be the development release number (an integer)
        rezVersion += ".dev" + str(pkgVersion.dev)

    if pkgVersion.local:
        # representation of the local version portion is any
        # the following conversions take place:
        # 1.0[+ubuntu-1] --> 1.0[-ubuntu.1]
        rezVersion += "-" + pkgVersion.local

    return rezVersion


def pythonSpecifierToRezRequirement(
    specifier: packaging.specifiers.SpecifierSet,
) -> rez.vendor.version.version.VersionRange:
    """Convert PEP440 version specifier to rez equivalent.

    See https://www.python.org/dev/peps/pep-0440/#version-specifiers

    Note that version numbers in the specifier are converted to rez equivalents
    at the same time. Thus a specifier like '<1.ALPHA2' becomes '<1.a2'.

    Note that the conversion is not necessarily exact - there are cases in
    PEP440 that have no equivalent in rez versioning. Most of these are
    specifiers that involve pre/post releases, which don't exist in rez (or
    rather, they do exist in the sense that '1.0.post1' is a valid rez version
    number, but it has no special meaning).

    Note also that the specifier is being converted into rez format, but in a
    way that still expresses how _pip_ interprets the specifier. For example,
    '==1' is a valid version range in rez, but '==1' has a different meaning to
    pip than it does to rez ('1.0' matches '==1' in pip, but not in rez). This
    is why '==1' is converted to '1+<1.1' in rez, rather than '==1'.

    Example conversions:

        |   PEP440    |     rez     |
        |-------------|-------------|
        | ==1         | 1+<1.1      |
        | ==1.*       | 1           |
        | >1          | 1.1+        |
        | <1          | <1          |
        | >=1         | 1+          |
        | <=1         | <1.1        |
        | ~=1.2       | 1.2+<2      |
        | ~=1.2.3     | 1.2.3+<1.3  |
        | !=1         | <1|1.1+     |
        | !=1.2       | <1.2|1.2.1+ |
        | !=1.*       | <1|2+       |
        | !=1.2.*     | <1.2|1.3+   |

    :param specifier: Pip specifier.

    `VersionRange`: Equivalent rez version range.
    """

    def is_release(rezVer: str) -> bool:
        parts = rezVer.split(".")
        try:
            _ = int(parts[-1])  # noqa
            return True
        except:
            return False

    # 1 --> 2; 1.2 --> 1.3; 1.a2 -> 1.0
    def next_ver(rezVer: str) -> str:
        parts = rezVer.split(".")
        if is_release(rezVer):
            parts = parts[:-1] + [str(int(parts[-1]) + 1)]
        else:
            parts = parts[:-1] + ["0"]
        return ".".join(parts)

    # 1 --> 1.1; 1.2 --> 1.2.1; 1.a2 --> 1.0
    def adjacent_ver(rezVer: str) -> str:
        if is_release(rezVer):
            return rezVer + ".1"
        else:
            parts = rezVer.split(".")
            parts = parts[:-1] + ["0"]
            return ".".join(parts)

    def convert_spec(spec: packaging.specifiers.Specifier) -> str:
        def parsed_rez_ver() -> str:
            v = spec.version.replace(".*", "")
            return pythonDistributionVersionToRez(v)

        def fmt(txt: str) -> str:
            v = parsed_rez_ver()
            vnext = next_ver(v)
            vadj = adjacent_ver(v)
            return txt.format(V=v, VNEXT=vnext, VADJ=vadj)

        # ==1.* --> 1
        if spec.operator == "==" and spec.version.endswith(".*"):
            return fmt("{V}")

        # ==1 --> 1+<1.1
        if spec.operator == "==":
            return fmt("{V}+<{VADJ}")

        # >=1 --> 1+
        if spec.operator == ">=":
            return fmt("{V}+")

        # >1 --> 1.1+
        if spec.operator == ">":
            return fmt("{VADJ}+")

        # <= 1 --> <1.1
        if spec.operator == "<=":
            return fmt("<{VADJ}")

        # <1 --> <1
        if spec.operator == "<":
            return fmt("<{V}")

        # ~=1.2 --> 1.2+<2; ~=1.2.3 --> 1.2.3+<1.3
        if spec.operator == "~=":
            v = rez.vendor.version.version.Version(parsed_rez_ver())
            v = v.trim(len(v) - 1)
            v_next = next_ver(str(v))
            return fmt("{V}+<" + v_next)

        # !=1.* --> <1|2+; !=1.2.* --> <1.2|1.3+
        if spec.operator == "!=" and spec.version.endswith(".*"):
            return fmt("<{V}|{VNEXT}+")

        # !=1 --> <1|1.1+; !=1.2 --> <1.2|1.2.1+
        if spec.operator == "!=":
            return fmt("<{V}|{VADJ}+")

        raise ValueError(
            f"Don't know how to convert PEP440 specifier {specifier!r} "
            "into rez equivalent"
        )

    # convert each spec into rez equivalent
    ranges = list(map(convert_spec, specifier))

    # AND together ranges
    total_range = rez.vendor.version.version.VersionRange(ranges[0])

    for range_ in ranges[1:]:
        range_ = rez.vendor.version.version.VersionRange(range_)
        total_range = total_range.intersection(range_)

        if total_range is None:
            raise ValueError(
                f"PEP440 specifier {specifier} converts to a non-intersecting rez "
                "version range"
            )

    return total_range


def pythonReqToRezReq(
    pythonReq: packaging.requirements.Requirement,
) -> rez.vendor.version.requirement.Requirement:
    """Convert packaging requirement object to equivalent rez requirement.

    Note that environment markers are ignored.

    :param pythonReq: Python requirement.
    :returns: Equivalent rez requirement object.
    """
    if pythonReq.extras:
        _LOG.warning(
            f"Ignoring extras requested on {pythonReq!r} - this is not yet supported"
        )

    req = pythontDistributionNameToRez(pythonReq.name)

    if pythonReq.specifier:
        range_ = pythonSpecifierToRezRequirement(pythonReq.specifier)
        req += "-" + str(range_)

    return rez.vendor.version.requirement.Requirement(req)


class CustomPyPackagingRequirement(packaging.requirements.Requirement):
    conditional_extras: typing.Optional[typing.Set[str]]


def normalizeRequirement(
    requirement: typing.Union[str, typing.Dict[typing.Any, typing.Any]]
) -> typing.List[CustomPyPackagingRequirement]:
    """Normalize a package requirement.

    Requirements from distlib packages can be a mix of string- or dict- based
    formats, as shown here:
    * https://www.python.org/dev/peps/pep-0508/#environment-markers
    * https://legacy.python.org/dev/peps/pep-0426/#environment-markers

    There's another confusing case that this code deals with. Consider these two requirements:

        # means: reportlab is a requirement of this package when the 'pdf' extra is requested
        Requires-Dist: reportlab; extra == 'pdf'
        means: this package requires libexample, with its 'test' extras
        Requires-Dist: libexample[test]

    See https://packaging.python.org/specifications/core-metadata/#provides-extra-multiple-use

    The packaging lib doesn't do a good job of expressing this - the first form
    of extras use just gets embedded in the environment marker. This function
    parses the extra from the marker, and stores it onto the resulting
    `packaging.requirements.Requirement` object in a 'conditional_extras' attribute. It also
    removes the extra from the marker (otherwise the marker cannot evaluate).
    Even though you can specify `environment` in `packaging.markers.Marker.evaluate`,
    you can only supply a single 'extra' key in the env, so this can't be used
    to correctly evaluate if multiple extras were requested.

    :param requirement: Requirement, for eg from `importlib.metadata.Distribution.requires`.
    :returns: Normalized requirements. Note that a list is returned, because the PEP426 format can define
        multiple requirements.
    """

    def reconstruct(
        req: CustomPyPackagingRequirement,
        marker_str: typing.Optional[str] = None,
        conditional_extras: typing.Union[typing.Set[str], None] = None,
    ) -> CustomPyPackagingRequirement:
        new_req_str = req.name

        if req.specifier:
            new_req_str += " (%s)" % str(req.specifier)

        if marker_str is None and req.marker:
            marker_str = str(req.marker)

        if marker_str:
            new_req_str += " ; " + marker_str

        new_req = CustomPyPackagingRequirement(new_req_str)
        new_req.conditional_extras = conditional_extras
        return new_req

    # PEP426 dict syntax
    # So only metadata that are of version 2.0 will be in dict. The other versions
    # (1.0, 1.1, 1.2, 2.1) will be strings.
    if isinstance(requirement, dict):
        result: typing.List[CustomPyPackagingRequirement] = []
        requires = requirement["requires"]
        extra = requirement.get("extra")
        marker_str = requirement.get("environment")

        # conditional extra, equivalent to: 'foo ; extra = "doc"'
        if extra:
            conditional_extras1 = set([extra])
        else:
            conditional_extras1 = None

        for req_str in requires:
            req = CustomPyPackagingRequirement(req_str)
            new_req = reconstruct(req, marker_str, conditional_extras1)
            result.append(new_req)

        return result

    # string-based syntax
    req = CustomPyPackagingRequirement(requirement)

    # detect case: "mypkg ; extra == 'dev'"
    # note: packaging lib already delimits with whitespace
    marker_str = str(req.marker)
    marker_parts = marker_str.split()

    # already in PEP508, packaging lib- friendly format
    if "extra" not in marker_parts:
        req.conditional_extras = None
        return [req]

    # Parse conditional extras out of marker
    conditional_extras: typing.Set[str] = set()
    marker_str = marker_str.replace(" and ", " \nand ")
    marker_str = marker_str.replace(" or ", " \nor ")
    lines = marker_str.split("\n")
    lines = [x.strip() for x in lines]
    new_marker_lines: typing.List[str] = []

    for line in lines:
        if "extra" in line.split():
            extra = line.split()[-1]
            extra = extra.replace('"', "")
            extra = extra.replace("'", "")
            conditional_extras.add(extra)
        else:
            new_marker_lines.append(line)

    # reconstruct requirement in new syntax
    if new_marker_lines:
        new_marker_parts = " ".join(new_marker_lines).split()
        if new_marker_parts[0] in ("and", "or"):
            new_marker_parts = new_marker_parts[1:]
        new_marker_str = " ".join(new_marker_parts)
    else:
        new_marker_str = ""

    new_req = reconstruct(req, new_marker_str, conditional_extras)
    return [new_req]


def convertMarker(marker: str) -> typing.List[str]:
    """Get the system requirements that an environment marker introduces.

    Consider:
        'foo (>1.2) ; python_version == "3" and platform_machine == "x86_64"'

    This example would cause a requirement on python, platform, and arch
    (platform as a consequence of requirement on arch).

    See:
    * vendor/packaging/markers.py:line=76
    * https://www.python.org/dev/peps/pep-0508/#id23

    :param marker: Environment marker string, eg 'python_version == "3"'.
    :returns: System requirements (unversioned).
    """
    _py = "python"
    _plat = "platform"
    _arch = "arch"

    sys_requires_lookup = {
        # TODO There is no way to associate a python version with its implementation
        # currently (ie CPython etc). When we have "package features", we may be
        # able to manage this; ignore for now
        "implementation_name": [_py],  # PEP-0508
        "implementation_version": [_py],  # PEP-0508
        "platform_python_implementation": [_py],  # PEP-0508
        "platform.python_implementation": [_py],  # PEP-0345
        "python_implementation": [
            _py
        ],  # setuptools legacy. Same as platform_python_implementation
        "sys.platform": [_plat],  # PEP-0345
        "sys_platform": [_plat],  # PEP-0508
        # note that this maps to python's os.name, which does not mean distro
        # (as 'os' does in rez). See https://docs.python.org/2/library/os.html#os.name
        "os.name": [_plat],  # PEP-0345
        "os_name": [_plat],  # PEP-0508
        "platform.machine": [_arch],  # PEP-0345
        "platform_machine": [_arch],  # PEP-0508
        # TODO hmm, we never variant on plat version, let's leave this for now...
        "platform.version": [_plat],  # PEP-0345
        "platform_version": [_plat],  # PEP-0508
        # somewhat ambiguous cases
        "platform_system": [_plat],  # PEP-0508
        "platform_release": [_plat],  # PEP-0508
        "python_version": [_py],  # PEP-0508
        "python_full_version": [_py],  # PEP-0508
    }

    sys_requires: typing.Set[str] = set()

    # note: packaging lib already delimits with whitespace
    marker_parts = marker.split()

    for varname, sys_reqs in sys_requires_lookup.items():
        if varname in marker_parts:
            sys_requires.update(sys_reqs)

    return list(sys_requires)


def getRezRequirements(
    installedDist: importlib_metadata.Distribution,
    pythonVersion: rez.vendor.version.version.Version,
    isPure: bool,
    nameCasings: typing.Optional[typing.List[str]] = None,
) -> RequirementsDict:
    """Get requirements of the given dist, in rez-compatible format.

    Example result:
        {
            "requires": ["foo-1.2+<2"],
            "variant_requires": ["future", "python-2.7"],
            "metadata": {
                # metadata pertinent to rez
                ...
            }
        }

    Each requirement has had its package name converted to the rez equivalent.

    The 'variant_requires' key contains requirements specific to the current
    variant.

    TODO: Currently there is no way to reflect extras that may have been chosen

    for this pip package. We need to wait for rez "package features" before this
    will be possible. You probably shouldn't use extras presently.

    :param installedDist: Distribution to convert.
    :param pythonVersion: Python version used to perform the installation.
    :param nameCasings: A list of pip package names in their correct
        casings (eg, 'Foo' rather than 'foo'). Any requirement whose name
        case-insensitive-matches a name in this list, is set to that name.
        This is needed because pip package names are case insensitive, but
        rez is case-sensitive. So a package may list a requirement for package
        'foo', when in fact the package that pip has downloaded is called 'Foo'.
        Be sure to provide names in PIP format, not REZ format (the pip package
        'foo-bah' will be converted to 'foo_bah' in rez).
    :returns: See example above.
    """
    _system = rez.system.System()
    result_requires: typing.List[str] = []
    result_variant_requires: typing.List[str] = []

    # create cased names lookup
    name_mapping = dict((x.lower(), x) for x in (nameCasings or []))

    # requirements such as platform, arch, os, and python
    sys_requires: typing.Set[str] = set()

    # entry_points scripts are platform and arch specific executables generated by
    # python build frontends during install
    has_entry_points_scripts = bool(installedDist.entry_points)

    # assume package is platform- and arch- specific if it isn't pure python
    if not isPure or has_entry_points_scripts:
        sys_requires.update(["platform", "arch"])

    # evaluate wrt python version, which may not be the current interpreter version

    # JC: TODO: Use rez to resolve the ful npython version based on the provided version?
    marker_env = {
        "python_full_version": str(pythonVersion),
        "python_version": str(pythonVersion.trim(2)),
        "implementation_version": str(pythonVersion),
    }

    # Note: This is supposed to give a requirements list that has already been
    # filtered down based on the extras requested at install time, and on any
    # environment markers present. However, this is not working in distlib. The
    # package gets assigned a LegacyMetadata metadata object (only if a package metadata
    # version is not equal to 2.0) and in that code path, this filtering
    # doesn't happen.
    #
    # See: vendor/distlib/metadata.py#line-892
    #
    requires = installedDist.requires

    # filter requirements
    for req_ in requires or []:
        reqs = normalizeRequirement(req_)

        for req in reqs:
            # skip if env marker is present and doesn't evaluate
            if req.marker and not req.marker.evaluate(environment=marker_env):
                continue

            # skip if req is conditional on extras that weren't requested
            if req.conditional_extras and not (
                set(installedDist.metadata["Provides-Extra"] or [])
                & req.conditional_extras
            ):
                continue

            if req.conditional_extras:
                _LOG.warning(
                    f"Skipping requirement {req!r} - conditional requirements are "
                    "not yet supported"
                )
                continue

            # Inspect marker(s) to see if this requirement should be varianted.
            # Markers may also cause other system requirements to be added to
            # the variant.
            #
            to_variant = False

            if req.marker:
                marker_reqs = convertMarker(str(req.marker))

                if marker_reqs:
                    sys_requires.update(marker_reqs)
                    to_variant = True

            # remap the requirement name
            remapped = name_mapping.get(req.name.lower())
            if remapped:
                req.name = remapped

            # convert the requirement to rez equivalent
            rez_req = str(pythonReqToRezReq(req))

            if to_variant:
                result_variant_requires.append(rez_req)
            else:
                result_requires.append(rez_req)

    # prefix variant with system requirements
    sys_variant_requires: typing.List[str] = []

    if "platform" in sys_requires:
        sys_variant_requires.append(f"platform-{_system.platform}")

    # TODO: Support wheel tags. This is important to avoid having to rez-pip
    # for when isnt' not necessary.
    # https://packaging.python.org/en/latest/specifications/platform-compatibility-tags/
    # So basically support manylinux and friends.
    if "arch" in sys_requires:
        sys_variant_requires.append(f"arch-{_system.arch}")

    if "os" in sys_requires:
        sys_variant_requires.append(f"os-{_system.os}")

    # JC: TODO: This is a modified version based on rez. It needs to be verified.
    if not isPure:
        # Add python variant requirement. Note that this is always MAJOR.MINOR,
        # because to do otherwise would mean analysing any present env markers.
        # This could become quite complicated, and could also result in strange
        # python version ranges in the variants.
        #
        sys_variant_requires.append("python-%s" % str(pythonVersion.trim(2)))
    else:
        requiresPython = installedDist.metadata["Requires-Python"]
        if requiresPython:
            result_requires.append(
                f"python-{pythonSpecifierToRezRequirement(packaging.specifiers.SpecifierSet(requiresPython))}"
            )
        else:
            # Some packages still don't provide Requires-Python. So make sure we
            # add python.
            # TODO: This is not not necessary for packages that don't have any python code...
            #       Thinking about cmake, ninja, etc. Though these are usually only requyired
            #       for building packages.
            result_requires.append("python")

    variant_requires = sys_variant_requires + result_variant_requires

    translation = {
        "python": requires,
        "rez": {"requires": result_requires, "variant": variant_requires},
    }
    _LOG.debug(f"{installedDist.name} requirements translation: {translation}")

    return RequirementsDict(
        requires=result_requires,
        variant_requires=variant_requires,
        metadata={"is_pure_python": isPure},  # TODO: This is probably useless.
    )
