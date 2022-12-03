# General idea

* Wheels only
* Only support Python 3 rez installs, but must support installing Python 2 wheels
* Use [standalone pip](https://pip.pypa.io/en/stable/installation/#standalone-zip-application) (and make sure we have an automatic update mechanism). It will be bundled I guess?
  Or we have a bootstrap command that would create a rez package for the pip zipapp.
* We need to fix the "scripts wrapper" shebang problem once and for all. This could be solved by using https://pypi.org/project/installer/.

Using pip zipapp, we can have a standalone pip that will work across multiple python versions and installs.
This simplifies the process quite a lot. No more "shared" pip install, no more "where is pip and which one
to use?" and no more "which python will be used?".

Latest pip version has a `--dry-run` flag that can be used in combination with `--report` to
outout a JSON of the packages that would be installed.

For example,

```
python pip.pyz install -q requests --dry-run --ignore-installed --python-version 2.7 --only-binary=:all: --target /tmp/asd --report -
```

outputs something like:

<details>
    <summary>Output</summary>
    
```json
{
    "version": "0",
    "pip_version": "22.3.1",
    "install": [
        {
        "download_info": {
            "url": "https://files.pythonhosted.org/packages/29/c1/24814557f1d22c56d50280771a17307e6bf87b70727d975fd6b2ce6b014a/requests-2.25.1-py2.py3-none-any.whl",
            "archive_info": {
            "hash": "sha256=c210084e36a42ae6b9219e00e48287def368a26d03a048ddad7bfee44f75871e"
            }
        },
        "is_direct": false,
        "requested": true,
        "metadata": {
            "metadata_version": "2.1",
            "name": "requests",
            "version": "2.25.1",
            "platform": [
            "UNKNOWN"
            ],
            "summary": "Python HTTP for Humans.",
            "description_content_type": "text/markdown",
            "home_page": "https://requests.readthedocs.io",
            "author": "Kenneth Reitz",
            "author_email": "me@kennethreitz.org",
            "license": "Apache 2.0",
            "classifier": [
            "Development Status :: 5 - Production/Stable",
            "Intended Audience :: Developers",
            "Natural Language :: English",
            "License :: OSI Approved :: Apache Software License",
            "Programming Language :: Python",
            "Programming Language :: Python :: 2",
            "Programming Language :: Python :: 2.7",
            "Programming Language :: Python :: 3",
            "Programming Language :: Python :: 3.5",
            "Programming Language :: Python :: 3.6",
            "Programming Language :: Python :: 3.7",
            "Programming Language :: Python :: 3.8",
            "Programming Language :: Python :: 3.9",
            "Programming Language :: Python :: Implementation :: CPython",
            "Programming Language :: Python :: Implementation :: PyPy"
            ],
            "requires_dist": [
            "chardet (<5,>=3.0.2)",
            "idna (<3,>=2.5)",
            "urllib3 (<1.27,>=1.21.1)",
            "certifi (>=2017.4.17)",
            "pyOpenSSL (>=0.14) ; extra == 'security'",
            "cryptography (>=1.3.4) ; extra == 'security'",
            "PySocks (!=1.5.7,>=1.5.6) ; extra == 'socks'",
            "win-inet-pton ; (sys_platform == \"win32\" and python_version == \"2.7\") and extra == 'socks'"
            ],
            "requires_python": ">=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, !=3.4.*",
            "project_url": [
            "Documentation, https://requests.readthedocs.io",
            "Source, https://github.com/psf/requests"
            ],
            "provides_extra": [
            "security",
            "socks"
            ],
            "description": ""
        }
        },
        {
        "download_info": {
            "url": "https://files.pythonhosted.org/packages/37/45/946c02767aabb873146011e665728b680884cd8fe70dde973c640e45b775/certifi-2021.10.8-py2.py3-none-any.whl",
            "archive_info": {
            "hash": "sha256=d62a0163eb4c2344ac042ab2bdf75399a71a2d8c7d47eac2e2ee91b9d6339569"
            }
        },
        "is_direct": false,
        "requested": false,
        "metadata": {
            "metadata_version": "2.1",
            "name": "certifi",
            "version": "2021.10.8",
            "platform": [
            "UNKNOWN"
            ],
            "summary": "Python package for providing Mozilla's CA Bundle.",
            "home_page": "https://certifiio.readthedocs.io/en/latest/",
            "author": "Kenneth Reitz",
            "author_email": "me@kennethreitz.com",
            "license": "MPL-2.0",
            "classifier": [
            "Development Status :: 5 - Production/Stable",
            "Intended Audience :: Developers",
            "License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)",
            "Natural Language :: English",
            "Programming Language :: Python",
            "Programming Language :: Python :: 3",
            "Programming Language :: Python :: 3.3",
            "Programming Language :: Python :: 3.4",
            "Programming Language :: Python :: 3.5",
            "Programming Language :: Python :: 3.6",
            "Programming Language :: Python :: 3.7",
            "Programming Language :: Python :: 3.8",
            "Programming Language :: Python :: 3.9"
            ],
            "project_url": [
            "Documentation, https://certifiio.readthedocs.io/en/latest/",
            "Source, https://github.com/certifi/python-certifi"
            ],
            "description": ""
        }
        },
        {
        "download_info": {
            "url": "https://files.pythonhosted.org/packages/19/c7/fa589626997dd07bd87d9269342ccb74b1720384a4d739a1872bd84fbe68/chardet-4.0.0-py2.py3-none-any.whl",
            "archive_info": {
            "hash": "sha256=f864054d66fd9118f2e67044ac8981a54775ec5b67aed0441892edb553d21da5"
            }
        },
        "is_direct": false,
        "requested": false,
        "metadata": {
            "metadata_version": "2.1",
            "name": "chardet",
            "version": "4.0.0",
            "platform": [
            "UNKNOWN"
            ],
            "summary": "Universal encoding detector for Python 2 and 3",
            "keywords": [
            "encoding",
            "i18n",
            "xml"
            ],
            "home_page": "https://github.com/chardet/chardet",
            "author": "Mark Pilgrim",
            "author_email": "mark@diveintomark.org",
            "maintainer": "Daniel Blanchard",
            "maintainer_email": "dan.blanchard@gmail.com",
            "license": "LGPL",
            "classifier": [
            "Development Status :: 5 - Production/Stable",
            "Intended Audience :: Developers",
            "License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)",
            "Operating System :: OS Independent",
            "Programming Language :: Python",
            "Programming Language :: Python :: 2",
            "Programming Language :: Python :: 2.7",
            "Programming Language :: Python :: 3",
            "Programming Language :: Python :: 3.5",
            "Programming Language :: Python :: 3.6",
            "Programming Language :: Python :: 3.7",
            "Programming Language :: Python :: 3.8",
            "Programming Language :: Python :: 3.9",
            "Programming Language :: Python :: Implementation :: CPython",
            "Programming Language :: Python :: Implementation :: PyPy",
            "Topic :: Software Development :: Libraries :: Python Modules",
            "Topic :: Text Processing :: Linguistic"
            ],
            "requires_python": ">=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, !=3.4.*",
            "description": ""
        }
        },
        {
        "download_info": {
            "url": "https://files.pythonhosted.org/packages/a2/38/928ddce2273eaa564f6f50de919327bf3a00f091b5baba8dfa9460f3a8a8/idna-2.10-py2.py3-none-any.whl",
            "archive_info": {
            "hash": "sha256=b97d804b1e9b523befed77c48dacec60e6dcb0b5391d57af6a65a312a90648c0"
            }
        },
        "is_direct": false,
        "requested": false,
        "metadata": {
            "metadata_version": "2.1",
            "name": "idna",
            "version": "2.10",
            "platform": [
            "UNKNOWN"
            ],
            "summary": "Internationalized Domain Names in Applications (IDNA)",
            "home_page": "https://github.com/kjd/idna",
            "author": "Kim Davies",
            "author_email": "kim@cynosure.com.au",
            "license": "BSD-like",
            "classifier": [
            "Development Status :: 5 - Production/Stable",
            "Intended Audience :: Developers",
            "Intended Audience :: System Administrators",
            "License :: OSI Approved :: BSD License",
            "Operating System :: OS Independent",
            "Programming Language :: Python",
            "Programming Language :: Python :: 2",
            "Programming Language :: Python :: 2.7",
            "Programming Language :: Python :: 3",
            "Programming Language :: Python :: 3.4",
            "Programming Language :: Python :: 3.5",
            "Programming Language :: Python :: 3.6",
            "Programming Language :: Python :: 3.7",
            "Programming Language :: Python :: 3.8",
            "Programming Language :: Python :: Implementation :: CPython",
            "Programming Language :: Python :: Implementation :: PyPy",
            "Topic :: Internet :: Name Service (DNS)",
            "Topic :: Software Development :: Libraries :: Python Modules",
            "Topic :: Utilities"
            ],
            "requires_python": ">=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*",
            "description": ""
        }
        },
        {
        "download_info": {
            "url": "https://files.pythonhosted.org/packages/65/0c/cc6644eaa594585e5875f46f3c83ee8762b647b51fc5b0fb253a242df2dc/urllib3-1.26.13-py2.py3-none-any.whl",
            "archive_info": {
            "hash": "sha256=47cc05d99aaa09c9e72ed5809b60e7ba354e64b59c9c173ac3018642d8bb41fc"
            }
        },
        "is_direct": false,
        "requested": false,
        "metadata": {
            "metadata_version": "2.1",
            "name": "urllib3",
            "version": "1.26.13",
            "summary": "HTTP library with thread-safe connection pooling, file post, and more.",
            "description_content_type": "text/x-rst",
            "keywords": [
            "urllib",
            "httplib",
            "threadsafe",
            "filepost",
            "http",
            "https",
            "ssl",
            "pooling"
            ],
            "home_page": "https://urllib3.readthedocs.io/",
            "author": "Andrey Petrov",
            "author_email": "andrey.petrov@shazow.net",
            "license": "MIT",
            "classifier": [
            "Environment :: Web Environment",
            "Intended Audience :: Developers",
            "License :: OSI Approved :: MIT License",
            "Operating System :: OS Independent",
            "Programming Language :: Python",
            "Programming Language :: Python :: 2",
            "Programming Language :: Python :: 2.7",
            "Programming Language :: Python :: 3",
            "Programming Language :: Python :: 3.6",
            "Programming Language :: Python :: 3.7",
            "Programming Language :: Python :: 3.8",
            "Programming Language :: Python :: 3.9",
            "Programming Language :: Python :: 3.10",
            "Programming Language :: Python :: 3.11",
            "Programming Language :: Python :: Implementation :: CPython",
            "Programming Language :: Python :: Implementation :: PyPy",
            "Topic :: Internet :: WWW/HTTP",
            "Topic :: Software Development :: Libraries"
            ],
            "requires_dist": [
            "brotlicffi (>=0.8.0) ; ((os_name != \"nt\" or python_version >= \"3\") and platform_python_implementation != \"CPython\") and extra == 'brotli'",
            "brotli (>=1.0.9) ; ((os_name != \"nt\" or python_version >= \"3\") and platform_python_implementation == \"CPython\") and extra == 'brotli'",
            "brotlipy (>=0.6.0) ; (os_name == \"nt\" and python_version < \"3\") and extra == 'brotli'",
            "pyOpenSSL (>=0.14) ; extra == 'secure'",
            "cryptography (>=1.3.4) ; extra == 'secure'",
            "idna (>=2.0.0) ; extra == 'secure'",
            "certifi ; extra == 'secure'",
            "urllib3-secure-extra ; extra == 'secure'",
            "ipaddress ; (python_version == \"2.7\") and extra == 'secure'",
            "PySocks (!=1.5.7,<2.0,>=1.5.6) ; extra == 'socks'"
            ],
            "requires_python": ">=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, !=3.4.*, !=3.5.*",
            "project_url": [
            "Documentation, https://urllib3.readthedocs.io/",
            "Code, https://github.com/urllib3/urllib3",
            "Issue tracker, https://github.com/urllib3/urllib3/issues"
            ],
            "provides_extra": [
            "brotli",
            "secure",
            "socks"
            ],
            "description": ""
        }
        }
    ],
    "environment": {
        "implementation_name": "cpython",
        "implementation_version": "3.10.8",
        "os_name": "posix",
        "platform_machine": "x86_64",
        "platform_release": "6.0.8-arch1-1",
        "platform_system": "Linux",
        "platform_version": "#1 SMP PREEMPT_DYNAMIC Thu, 10 Nov 2022 21:14:24 +0000",
        "python_full_version": "3.10.8",
        "platform_python_implementation": "CPython",
        "python_version": "3.10",
        "sys_platform": "linux"
    }
}
```
</details>

I'm still not sure if we should use `--dry-run` and manually download the wheels + install them using https://pypi.org/project/installer/
or if we shuold just `pip isntall --target`. Using `installer` would allow us to control
how the "scripts wrapper" are constructed and managed.
