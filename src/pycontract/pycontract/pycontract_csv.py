import csv
from typing import Optional, List, Callable
import pandas as pd
# import xlrd

class CSVReader:
    """
    --- DEPRECATED ---
    Class for reading CSV files: https://www.w3schools.com/python/python_iterators.asp.
    Example of use:

        csv =  CSVReader('file.csv', converter)
        for event in csv:
            ...
    """
    def __init__(self, file: str, converter: Callable[[List[str]], object], skip: int = 0):
        """
        The file is the csv file to read, assumed to consist of lines,
        each comma separated.

        :param file: the csv file.
        :param converter: a function that converts one line into an event
        processed by the monitor.
        :param skip: number of lines in CSV file to skip initially (headers usually).

        line_count: the number of lines read from CSV file.
        """
        self.file = file
        self.csv_file = open(file)
        self.csv_reader = csv.reader(self.csv_file)
        self.converter = converter
        self.line_count = 0
        for x in range(skip):
            self.__next__()

    def __iter__(self):
        return self

    def __next__(self):
        self.line_count += 1
        next = self.csv_reader.__next__()
        return self.converter(next)

    def close(self):
        self.csv_file.close()


def get_csv_filename(name: str) -> str:
    """
    Returns the name of a CSV file corresponding to the input file `name`. If `name` is a CSV
    file already (that is: does not have an .xls ending or some extension of this suffix) the
    `name` is returned unchanged. If on the other hand `name` is the name of a
    spreadsheet, that is, it  ends in .xls, .xlsd, ..., the spreadsheet is first converted into
    a CSV file, and the new name for that CSV file is returned. In this case the new name for the CSV
    file is created as follows. If, as an example, the spreadsheet name is `file.xls' the CSV file
    will have the name `__file__.csv`. This file is created from the spreadsheet, and the name
    `__file__.csv` is returned.
    :param name: the name of the file, a CSV file or a spreadsheet where the last suffix after `.`
    starts with `.xls`.
    :return: the name of the corresponding CSV file (which has been created in case the input file
    represented a spreadsheet).
    """
    file_name = name  # e.g.: ../logs/460/sr_EURCSTB1CONTROL_460_eha-limited-ert.xls
    dash_parts = name.split('/')
    last_dash_part = dash_parts[-1]
    dot_parts = last_dash_part.split('.')
    suffix = dot_parts[-1]
    if suffix.startswith('xls'):
        dot_parts.pop()
        csv_file_body = '.'.join(dot_parts)
        file_name = f'__{csv_file_body}__.csv'
        df = pd.concat(pd.read_excel(name, sheet_name=None))
        df.to_csv(file_name, index=None, header=True)
        print(f'\nCSV file stored in {file_name}\n')
    return file_name


class CSVSource:
    '''
    Alternative (newer) class for reading CSV file.
    '''

    def __init__(self, file: str):
        '''
        :param file: name of CSV or XLS file to be read from.
        '''
        self.file = get_csv_filename(file)
        self.csv_file = open(self.file)
        self.csv_reader = None
        self.line_count = 0

    def column_names(self) -> Optional[List[str]]:
        '''
        Returns names of columns in CSV file. By default, None is returned, meaning
        that the first row of the CSV file contains the column names.
        Can be overridden.
        :return: List of column names, or None if CSV file contains them on first row.
        '''
        return None

    def __enter__(self):
        names = self.column_names()
        if names is None:
            self.csv_reader = csv.DictReader(self.csv_file)
        else:
            self.csv_reader = csv.DictReader(self.csv_file, fieldnames=names)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.csv_file.close()

    def __iter__(self):
        return self

    def __next__(self):
        self.line_count += 1
        if self.line_count % 100000 == 0:
            print(f'- {self.line_count}')
        the_next = self.csv_reader.__next__()
        return the_next

