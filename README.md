# PyTraverser

PyTraverser is a Python library for text based traversing of MDSplus trees. It provides both a command line callable interfaces.

This package uses mdsthin to access MDSplus information.  Define MDS_HOST environment to be the server to use.  For example:
```
export MDS_HOST=alcdata
```
## Features

- Traverse trees and graphs with customizable strategies
- Depth-first and breadth-first traversal support
- Node filtering and transformation utilities
- Easy integration with existing Python data structures

## Installation

```bash
pip install pytraverser
```
## Key Bindings
    "[b]click[/b]/[b]⏎[/b] Expand/Collapse + select   "
    "[b]⇥[/b] Decompile  "
    "[b]⇧⇥[/b] Show Data  " 
    "[b]←[/b] Collapse Parent   "
    "[b]→[/b] Expand   "
    "[b]↓[/b] Move Down + expand   "
    "[b]↑[/b] move Up"

## Usage Shell
```
usage: pytraverser [-h] [-d | -l] tree [shot]

Tree, optional shot, dark flag

positional arguments:
  tree         Tree string
  shot         Optional shot number (default -1)

options:
  -h, --help   show this help message and exit
  -d, --dark   Enable dark mode
  -l, --light  Enable light mode
```

## Python Usage

```
$ python
Python 3.10.12 (main, Aug 15 2025, 14:32:43) [GCC 11.4.0] on linux
Type "help", "copyright", "credits" or "license" for more information.
>>> from pytraverser import traverse
>>> node = traverse("cmod", -1) #type 'q' to exit 
>>> node
.EDGE.CRYOPUMP
>>> 
```

#
## Contributing

Contributions are welcome! Please open issues or submit pull requests on GitHub.

## License

This project is licensed under the MIT License.
