

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

class FileMon(Monitor):
    def __init__(self):
        super().__init__()
        self.folders: set[str] = set()
    
    def transition(self, event):
        match event:
            case {'name': 'Create', 'folder': folder}:
                self.folders.add(folder)
            case {'name': 'Delete', 'folder': folder}:
                self.folders.discard(folder)
            case {'name': 'Open', 'folder': folder, 'filename': filename, 'mode': mode, 'size': size}:
                self.check(folder in self.folders, f'Folder {folder} not created')
                return FileMon.File(folder, filename, mode, size)
            case {'name': 'Write', 'filename': filename, 'data': data} if not self.exists(FileMon.File, name=filename):
                return error('file not opened')
                
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
