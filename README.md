# PyTraverser

PyTraverser is a Python library for traversing and manipulating data structures such as trees and graphs. It provides flexible APIs for walking, searching, and transforming nested data, making it easier to implement algorithms and data processing workflows.

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
$ export MDS_HOST=alcdata
$ pytraverser tree-name [shot-numer] [-d --dark | -l --light]
```gh
## Usage Python

```
$ export MDS_HOST=alcdata
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
