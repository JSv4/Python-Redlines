# Developer Guide for RedlinesWrapper

## Prerequisites

- Python 3.7 or higher installed
- .NET SDK for building C# binaries or .NET Runtime to run them
- Hatch for Python environment and package management

## Setting Up the Project

### Step 1: Clone the Repository

Clone the Python-Docx-Redlines repository to your local

machine. Use Git to clone the repository using the following command:

```bash
git clone https://github.com/JSv4/Python-Docx-Redlines
cd python-docx-redlines
```

### Step 2: Install Hatch

If Hatch is not already installed, install it using pip:

```bash
pip install hatch hatchling
```

### Step 3: Create and Activate the Virtual Environment

Inside the project directory, create a virtual environment using Hatch:

```bash
hatch env create
```

Activate the virtual environment:

```bash
hatch shell
```

### Step 4: Install Dependencies

Install the necessary Python dependencies:

```bash
pip install .[dev]
```

## Building the C# Binaries

You can use the binaries distributed with the project, or, if you want to build new binaries for some reason, you can
use our build script, integrated as a hatch tool. 

```bash
hatch run build
```

### Under the Hood

We're just using dotnet to build binaries for [Program.cs](csproj/Program.cs), a command line utility that exposes 
`WmlComparer's` redlining capabilities. We are currently target win-x64 and linux-x64 builds, but any runtime
[supported by .NET](https://learn.microsoft.com/en-us/dotnet/core/rid-catalog) is theoretically supported. 

**Our build script does the following:**

1. Build a binary for Linux:

```bash
dotnet publish -c Release -r linux-x64 --self-contained
```

2. Build a binary for Windows:

```bash
dotnet publish -c Release -r win-x64 --self-contained
```

3. Build a binary for MacOS:

```bash
dotnet publish -c Release -r osx-x64 --self-contained
```

4. Archive and package binaries into `./dist/`:


## Running Tests

To ensure everything is set up correctly and working as expected, run the tests included in the `tests/` directory.
Execute the tests using pytest:

```bash
pytest
```

This will run all the test cases defined in your test files.

## Conclusion

You've now set up the Python-Docx-Redlines project, built the necessary C# binaries, and learned how to use the Python wrapper to compare `.docx` files. Running the tests ensures that your setup is correct and the wrapper functions as expected.
