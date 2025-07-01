

from enum import Enum
import pycontract as pc


"""
Requirements:
Consider a simple filesystem mechanism that handles several key events. 

create (F)
delete (F)
open(F: str , f : str , m: str , s : int )
read(f: str)
write(f: str, d: str)
close(f: str)

1) If data is written to a file, the file must have been opened in write mode, not closed since, 
and must reside in a folder that has been created and not deleted since. 

2) The total number of bytes written to all files together does not exceed a specified max value.

3) There is a limit on how many bytes can be written to each file.
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
    def __init__(self):
        super().__init__()
        self.folders: set[str] = set()

    def transition(self, event):
        match event:
            case Create(folder):
                self.folders.add(folder)
            case Delete(folder):
                self.folders.discard(folder)
            case Open(folder, filename, mode, size):
                self.check(folder in self.folders, f'Folder {folder} not created')
                return FileMon.File(folder, filename, mode, size)
            case Write(filename=f) if not self.exists(FileMon.File, name=f):
                return error('file not opened')

    @data
    class File(HotState):
        folder: str
        name: str
        mode: Mode
        size: int

        def transition(self, event):
            match event:
                case Delete(self.folder):
                    return error('folder deleted')  
                case Close(self.name):
                    return ok
                case Write(self.name, data):
                    self.check(self.mode == Mode.WRITE, f'File {self.name} not opened in write mode')
                    self.check(len(data) <= self.size, f'File {self.name} size exceeded')
                    return FileMon.File(self.folder, self.name, self.mode, self.size - len(data))


if __name__ == '__main__':
    print('\n' * 10)
    m = FileMon()
    trace = [
        Create('folder1'),
        Open('folder1', 'file1', Mode.WRITE, 10),
        Write('file1', 'data1'),
        Write('file1', 'data2'),
        # Write('file1', 'data3'),
        Close('file1'),
        Delete('folder1')
    ]
    m.verify(trace)
