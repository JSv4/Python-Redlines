# Python-Redlines: Docx Redlines (Tracked Changes) for the Python Ecosystem

## Project Goal - Democratizing DOCX Comparisons

The main goal of this project is to address the significant gap in the open-source ecosystem around `.docx` document
comparison tools. Currently, the process of comparing and generating redline documents (documents that highlight 
changes between versions) is complex and largely dominated by commercial software. These 
tools, while effective, often come with cost barriers and limitations in terms of accessibility and integration 
flexibility.

`Python-redlines` aims to democratize the ability to run tracked change redlines for .docx, providing the 
open-source community with a tool to create `.docx` redlines without the need for commercial software. This will let
more legal hackers and hobbyist innovators experiment and create tooling for enterprise and legal.

## Project Roadmap

### Step 1. Open-XML-PowerTools `WmlComparer` Wrapper

The [Open-XML-PowerTools](https://github.com/OpenXmlDev/Open-Xml-PowerTools) project historically offered a solid 
foundation for working with `.docx` files and has an excellent (if imperfect) comparison engine in its `WmlComparer` 
class. However, Microsoft archived the repository almost five years ago, and a forked repo is not being actively 
maintained, as its most recent commits dates from 2 years ago and the repo issues list is disabled.

As a first step, our project aims to bring the existing capabilities of WmlCompare into the Python world. Thankfully, 
XML Power Tools is full cross-platform as it is written in .NET and compiles with the still-maintained .NET 8. The
resulting binaries can be compiled for the latest versions of Windows, OSX and Linux (Ubuntu specifically, though other
distributions should work fine too). We have included an OSX build but do not have an OSX machine to test on. Please 
report an issues by opening a new Issue.

The initial release has a single engine `XmlPowerToolsEngine`, which is just a Python wrapper for a simple C# utility
written to leverage WmlComparer for 1-to-1 redlines. We hope this provides a stop-gap capability to Python developers 
seeking .docx redline capabilities. 

**Note**, we don't plan to fork or maintain Open-XML-PowerTools. [Version 4.4.0](https://www.nuget.org/packages/Open-Xml-PowerTools/), 
which appears to only be compatible with [Open XML SDK < 3.0.0](https://www.nuget.org/packages/DocumentFormat.OpenXml) works
for now, it needs to be made compatible with the latest versions of the Open XML SDK to extend its life. **There are 
also some [issues](https://github.com/dotnet/Open-XML-SDK/issues/1634)**, and it seems the only maintainer of 
Open-XML-PowerTools probably won't fix, and understanding the existing code base is no small task. Please be aware that
**Open XML PowerTools is not a perfect comparison engine, but it will work for many purposes. Use at your own risk.**

### Step 2. Pure Python Comparison Engine

Looking towards the future, rather than reverse engineer `WmlComparer` and maintain a C# codebase, we envision a 
comparison engine written in python. We've done some experimentation with [`xmldiff`](https://github.com/Shoobx/xmldiff)
as the engine to compare the underlying xml of docx files. Specifically, we've built a prototype to unzip `.docx` files, 
execute an xml comparison using `xmldiff`, and then reconstructed a tracked changes docx with the proper Open XML
(ooxml) tracked change tags. Preliminary experimentation with this approach has shown promise, indicating its 
feasibility for handling modifications such as simple span inserts and deletes.

However, this ambitious endeavor is not without its challenges. The intricacies of `.docx` files and the potential for 
complex, corner-case scenarios necessitate a thoughtful and thorough development process. In the interim, `WmlComparer`
is a great solution as it has clearly been built to account for many such corner cases, through a development process
that clearly was influenced by issues discovered by a large user base. The XMLDiff engine will take some time to reach
a level of maturity similar to WmlComparer. At the moment it is NOT included.

## Getting started

### Install .NET Core 8

The Open-XML-PowerTools engine we're using in the initial releases requires .NET to run (don't worry, this is very 
well-supported cross-platform at the moment). Our builds are targeting x86-64 Linux and Windows, however, so you'll 
need to modify the build script and build new binaries if you want to target another runtime / architecture.

#### On Linux

You can follow [Microsoft's instructions for your Linux distribution](https://learn.microsoft.com/en-us/dotnet/core/install/linux)

#### On Windows

You can follow [Microsoft's instructions for your Windows vesrion](https://learn.microsoft.com/en-us/dotnet/core/install/windows?tabs=net80)

### Install the Library

At the moment, we are not distributing via pypi. You can easily install directly from this repo, however. 

```commandline
pip install git+https://github.com/JSv4/Python-Redlines
```

You can add this as a dependency like so

```requirements
python_redlines @ git+https://github.com/JSv4/Python-Redlines@v0.0.1
```

### Use the Library

If you just want to use the tool, jump into our [quickstart guide](docs/quickstart.md).

## Architecture Overview

`XmlPowerToolsEngine` is a Python wrapper class for the `redlines` C# command-line tool, source of which is available in 
[./csproj/Program.cs](./csproj/Program.cs). The redlines utility and wrapper let you compare two docx files and 
show the differences in tracked changes (a "redline" document).

### C# Functionality

The `redlines` C# utility is a command line tool that requires four arguments:
1. `author_tag` - A tag to identify the author of the changes.
2. `original_path.docx` - Path to the original document.
3. `modified_path.docx` - Path to the modified document.
4. `redline_path.docx` - Path where the redlined document will be saved.

The Python wrapper, `XmlPowerToolsEngine` and its main method `run_redline()`, simplifies the use of `redlines` by 
orchestrating its execution with Python and letting you pass in bytes or file paths for the original and modified 
documents.

### Packaging

The project is structured as follows:
```
python-redlines/
│
├── csproj/
│   ├── bin/
│   ├── obj/
│   ├── Program.cs
│   ├── redlines.csproj
│   └── redlines.sln
│
├── docs/
│   ├── developer-guide.md
│   └── quickstart.md
│
├── src/
│   └── python_redlines/
│       ├── bin/
│       │   └── .gitignore
│       ├── dist/
│       │   ├── .gitignore
│       │   ├── linux-x64-0.0.1.tar.gz
│       │   └── win-x64-0.0.1.zip
│       ├── __about__.py
│       ├── __init__.py
│       └── engines.py
│
├── tests/
|   ├── fixtures/
|   ├── test_openxml_differ.py
|   └── __init__.py
|
├── .gitignore
├── build_differ.py
├── extract_version.py
├── License.md
├── pyproject.toml
└── README.md
```

- `src/your_package/`: Contains the Python wrapper code.
- `dist/`: Contains the zipped C# binaries for different platforms.
- `bin/`: Target directory for extracted binaries.
- `tests/`: Contains test cases and fixtures for the wrapper.

### Detailed Explanation and Dev Setup

If you want to contribute to the library or want to dive into some of the C# packaging architecture, go to our
[developer guide](docs/developer-guide.md).

## Additional Information

- **Contributing**: Contributions to the project should follow the established coding and documentation standards.
- **Issues and Support**: For issues, feature requests, or support, please use the project's issue tracker on GitHub.

## License

MIT
