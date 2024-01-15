# Python Redlines

[![PyPI - Version](https://img.shields.io/pypi/v/python-redlines.svg)](https://pypi.org/project/python-redlines)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/python-redlines.svg)](https://pypi.org/project/python-redlines)

-----

**Table of Contents**

- [Installation](#installation)
- [License](#license)

## Installation

```console
pip install python-redlines
```

## License

`python-redlines` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.

Usage:

Setup project and create .net project in dir
```
dotnet new console
```

Build app

```
dotnet build
```

Run via dotnet console
```
dotnet run scrudato@umich.edu "/home/jman/Downloads/NVCA-Model-Document-Certificate-of-Incorporation.docx" "/home/jman/Downloads/Modified.docx" "/home/jman/Downloads/redline.docx"
```

Package for linux
```
dotnet publish -c release -r linux-x64 --self-contained
```

Package for windows
```
dotnet public -c release -r win-x64 --self-contained
```

"Install" on Linux

1. Install .net for Linux (whatever distro you're using)
2. Copy the Release contents from linux-x64 folder
3. run `chmod 777 ./redlines`
4. Then you can run `./redlines original_path.docx modified_path.docx`

More complete package and install directions: 

https://ttu.github.io/dotnet-core-self-contained-deployments/

Archive and zip the release folder contents as .tar.gz, then distribute the archive. User install instructions would be:

```commandline
$ mkdir redlines && cd redlines
$ wget <github release url>
$ tar -zxvf redlines-linux-x64.tar.gz
$ chmod +x redlines
$ ./redlines <author_tag> <original_path.docx> <modified_path.docx> <redline_path.docx>
```

"Install" on Windows

TODO - run through this and document
