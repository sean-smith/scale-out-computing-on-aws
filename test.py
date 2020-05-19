import random
import re
import uuid
import string
import datetime
from itertools import islice
import boto3
import ast

def read_lines_from_file_as_data_chunks(file_name, chunk_size, callback, return_whole_chunk=False):
    def read_in_chunks(file_obj, chunk_size=5000):
        """
        https://stackoverflow.com/a/519653/5130720
        Lazy function to read a file
        Default chunk size: 5000.
        """
        while True:
            data = file_obj.read(chunk_size)
            if not data:
                break
            yield data

    fp = open(file_name)
    data_left_over = None

    # loop through characters
    for chunk in read_in_chunks(fp):
        # if uncompleted data exists
        if data_left_over:
            # print('\n left over found')
            current_chunk = data_left_over + chunk
        else:
            current_chunk = chunk

        # split chunk by new line
        lines = current_chunk.splitlines()

        # check if line is complete
        if current_chunk.endswith('\n'):
            data_left_over = None
        else:
            data_left_over = lines.pop()

        if return_whole_chunk:
            callback(data=lines, eof=False, file_name=file_name)

        else:
            for line in lines:
                callback(data=line, eof=False, file_name=file_name)
                pass

    if data_left_over:
        current_chunk = data_left_over
        if current_chunk is not None:
            lines = current_chunk.splitlines()
            if return_whole_chunk:
                callback(data=lines, eof=False, file_name=file_name)
            else:
                for line in lines:
                    callback(data=line, eof=False, file_name=file_name)
                    pass
    callback(data=None, eof=True, file_name=file_name)


print("SOCA Test - Web Based - Read large file > 250mb and display content ")
print("test1 - default")
file_to_read = "/Users/mcrozes/Downloads/20180819"
import time
start = time.time()
with open(file_to_read) as input_file:
    data = input_file.read()

end = time.time()
print(end - start)


print("test2 - chunk of lines")
start_slice = time.time()
number_of_lines = 100
file_content = []
with open(file_to_read) as input_file:
    while True:
        next_n_lines = islice(input_file, number_of_lines)
        if not next_n_lines:
            break
        else:
            for current_line in next_n_lines:
                for content in current_line.split("\n"):
                    if content != "":
                        file_content.append(content)

end_slice = time.time()
print(len(file_content))
print(end_slice - start_slice)

