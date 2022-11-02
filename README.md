# pySpy

pySpy attempts to re-create the experience of dnSpy, but for Python bytecode.

You can easily view and edit the bytecode, names, and constants. All with a relatively intuitive GUI.

## Version support
Currently, the editor doesn't aim for cross-version support. You can only edit the bytecode of the version that you're running the program on.
It uses [dearpygui](https://github.com/hoffstadt/DearPyGui) for the GUI, which can only run on Python versions 3.7 - 3.10

It uses an internal module to edit the bytecode, which handles all the converting from and to native code objects. It also ensures all jump arguments are up-to-date.

## How to use
`pip install -r requirements.txt`

`python3 pyspy`

## Missing features
There are a lot of opportunities to make this better, for example:
- A debugger
- Create new code objects
- ~~Add constants~~ Added
- ~~Add names~~ Added
- Add new instructions
- Plugin support

In other words, contributing is appreciated.

## Showcase
![image](https://user-images.githubusercontent.com/40274381/196053131-55e755da-ac18-4daa-8546-2c21a16491e5.png)

## License
Using the [GNU General Public License v3.0](https://github.com/Svenskithesource/pySpy/blob/main/LICENSE) license.
