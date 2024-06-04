# Python-Redlines Quickstart

As discussed in the main README, the initial version is a wrapper for the C# api provided by Open-XML-PowerTools and
`WmlComparer`. This readme will show you how to use the XmlPowerToolsEngine to run a redline. 

### Step 1: Import and Initialize the Wrapper

In your Python script or interactive session, import and initialize the wrapper:

```python
from python_redlines.engines import XmlPowerToolsEngine

wrapper = XmlPowerToolsEngine()
```

### Step 2: Run Redlines

Use the `run_redline` method to compare documents. You can pass the paths of the `.docx` files or their byte content:

```python
# Example with file paths
output = wrapper.run_redline('AuthorTag', '/path/to/original.docx', '/path/to/modified.docx')

# Example with byte content
with open('/path/to/original.docx', 'rb') as f:
    original_bytes = f.read()
with open('/path/to/modified.docx', 'rb') as f:
    modified_bytes = f.read()

# This is a tuple, bytes @ element 0
output = wrapper.run_redline('AuthorTag', original_bytes, modified_bytes)
```

In both cases, `output` will contain the byte content of the resulting redline - a .docx with changes in tracked 
changes.

### Step 3: Handle the Output

Process or save the output as needed. For example, to save the redline output to a file:

```python
with open('/path/to/redline_output.docx', 'wb') as f:
    f.write(output[0])
```
