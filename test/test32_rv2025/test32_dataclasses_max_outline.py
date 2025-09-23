
from enum import Enum
import pycontract as pc


"""
Consider a simple filesystem mechanism that handles several key events. 

create (F)
delete (F)
open(F: str , f : str , m: str , s : int )
read(f: str)
write(f: str, d: str)
close(f: str)

Requirements:
1) A file must be opened in a folder that has been created and not deleted since.
2) If a file is written to, the file must have been opened in write mode, not closed since.
3) A file that is opened must eventually be closed.
4) NOT IMPLEMENTED: The total number of bytes written to all files together must not exceed a specified \texttt{max} value.
5) The number of bytes written to a file must not exceed the \texttt{size} parameter of the open event.
"""

from pycontract import *

class Mode(Enum):
    READ = 'read'
    WRITE = 'write'

@data
class Create(Event):
    folder: str

@data
class Delete(Event):
    folder: str

@data
class Open(Event):
    folder: str
    filename: str
    mode: Mode
    size: int

@data
class Close(Event):
    filename: str

@data
class Write(Event):
    filename: str
    data: str

class FileMon(Monitor):
    def __init__(self, max: int):
        super().__init__()
        self.max = max

    def transition(self, event):
        match event:
            case Create(folder):
                return FileMon.Folder(folder)
            case Open(folder, filename, mode, size):
                self.check(self.exists(FileMon.Folder, folder=folder), f'Folder {folder} not created')
                return FileMon.File(folder, filename, mode, size)
            case Write(filename=f) if not self.exists(FileMon.File, name=f):
                return error('file not opened')

    class Folder(State): ...

    class File(HotState): ...



