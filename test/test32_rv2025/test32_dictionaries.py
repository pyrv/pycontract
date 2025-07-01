

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

class FileMon(Monitor):
    def transition(self, event):
        match event:
            case {'name': 'Create', 'folder': folder}:
                return FileMon.Folder(folder)
            case {'name': 'Open', 'folder': folder, 'filename': filename, 'mode': mode, 'size': size}:
                self.check(self.exists(FileMon.Folder, folder=folder), f'Folder {folder} not created')
                return FileMon.File(folder, filename, mode, size)
            case {'name': 'Write', 'filename': filename, 'data': data} if not self.exists(FileMon.File, name=filename):
                return error('file not opened')
                
    @data
    class Folder(State):
        folder: str

        def transition(self, event):
            match event:
                case {'name': 'Delete', 'folder': self.folder}:
                    return ok

    @data
    class File(HotState):
        folder: str
        name: str
        mode: str
        size: int

        def transition(self, event):
            match event:
                case {'name': 'Delete', 'folder': self.folder}:
                    return error('folder deleted')  
                case {'name': 'Close', 'filename': self.name}:
                    return ok
                case {'name': 'Write', 'filename': self.name, 'data': data}:
                    self.check(self.mode == 'write', f'File {self.name} not opened in write mode')
                    self.check(len(data) <= self.size, f'File {self.name} size exceeded')
                    return FileMon.File(self.folder, self.name, self.mode, self.size - len(data))


if __name__ == '__main__':
    print('\n' * 10)
    m = FileMon()
    trace = [
        {'name': 'Create', 'folder': 'folder1'},
        {'name': 'Open', 'folder': 'folder1', 'filename': 'file1', 'mode': 'write', 'size': 10},
        {'name': 'Write', 'filename': 'file1', 'data': 'data1'},
        {'name': 'Write', 'filename': 'file1', 'data': 'data2'},
        #{'name': 'Write', 'filename': 'file1', 'data': 'data3'},
        {'name': 'Close', 'filename': 'file1'},
        {'name': 'Delete', 'folder': 'folder1'}  
    ]
    m.verify(trace)
