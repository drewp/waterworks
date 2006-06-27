#!/usr/bin/env python
__doc__ = """
tail -f for multiple files written natively in Python

Polls files for appended text.  Can call a callback function with the
changes if you'd like, or you can control when the pollings occur.

Based on a post by Skip Montanaro in comp.lang.python (see http://groups.google.com/groups?hl=en&lr=&ie=UTF-8&oe=UTF-8&threadm=3D4C2C0B.274B0BE9%40alcyone.com&rnum=5&prev=/groups%3Fhl%3Den%26lr%3D%26ie%3DUTF-8%26oe%3DUTF-8%26q%3Dtail%2Bfile%26btnG%3DGoogle%2BSearch%26meta%3Dgroup%253Dcomp.lang.python.*)

Example:
# a callback function
def printer(filename, s):
    if s: print "%s:\t%s" % (filename, s)
t = Tailer(file1, file2) # Tailer takes a list of files
t.pollloop(printer)

See pydoc for the other tailing modes (modes are pollloop, poll,
multipoll) by doing 'pydoc Tailer' in this directory.

Known bugs:
    It doesn't handle the case when a file is alterred in the middle very well.

Please feel free to contact me at dmcc AT bigasterisk DOT com with questions,
feature requests, patches, whatever.
"""

# todo:
#  distutil-ification

__version__ = 2.0
__author__ = 'David McClosky (dmcc@bigasterisk.com)'

from __future__ import generators
import os, sys, time

__all__ = ['TailedFile', 'TailInterface', 'Tailer']

class TailedFile:
    """An object representing an object being tailed and it's current state.
    initial is the offset in the file where we should start.  Setting it to
    None will start us from the end."""
    def __init__(self, filename, initial=None, line_buffered=True):
        """Filename is the name of the file to watch.  initial is the
        size where where should start watching from.  Omitting initial
        will result in watching changes from the end of the file.
        Like Python lists, if initial is less than 0, we will count from
        the current end of the file.  If line_buffered is True, we will
        buffer new bits until we see a newline at the end of a line."""
        self.file = open(filename, 'r')
        self.filename = filename
        if initial is None:
            self.offset = os.path.getsize(filename)
        else:
            if initial < 0:
                self.offset = os.path.getsize(filename) - initial
            else:
                self.offset = initial
        self.size = self.offset
        self.line_buffered = line_buffered
        self._partial_lines = ''
    def __len__(self):
        'Returns the size of the file'
        return self.size
    def __str__(self):
        'Returns the filename of the file'
        return self.filename
    def poll(self):
        """Returns a string of the new text in the file if there is any.
        If there isn't, it returns None.  If the file shrinks (for
        whatever reason), it will start watching from the new end of
        the file."""
        self.size = os.path.getsize(self.filename)
        if self.size > self.offset:
            self.file.seek(self.offset)
            s = self.file.read()
            self.offset = self.size

            if self.line_buffered:
                s = self._partial_lines + s
                if s.endswith('\n'):
                    self._partial_lines = ''
                else:
                    # buffer the partial line
                    s = self._partial_lines + s
                    lines = s.splitlines()
                    if len(lines) > 1:
                        s = '\n'.join(lines[:-1]) + '\n'
                        self._partial_lines = lines[-1]
                    else:
                        self._partial_lines = s
                        s = None

            return s
        # if file shrinks, we will adjust to the new size
        if self.size < self.offset:
            self.offset = self.size
        return None

class TailInterface:
    """An interface for file watching."""
    def __init__(self, *files, **kw):
        """Files is a list of files to watch.  Keyword arguments include:
        interval (for the interval at which the file should be poll()ed
        for pollloop() and initial for the initial end of the file.
        Setting initial to zero will make it read the entire file on
        the first poll() and any subsequent additions for the poll()s
        after that."""
    def poll(self):
        """If any files have grown, return a tuple containing the filename
        and new text.  If no files have changed, we return None"""
    def pollloop(self, callback):
        """Continously watches the files for changes, sleeping for
        'interval' amount of seconds in between (see __init__).  If there
        are any changes, it will call the callback with two arguments:
        the filename and new text."""

class Tailer(TailInterface):
    """An object that watches one or more files for additions.  You can
    either call it whenever you want with poll(), or use pollloop()
    to call it regularly."""
    def __init__(self, *files, **kw):
        """Given a list of files and some keyword arguments, constructs
        an object which will watch the files for additions.  The optional
        keyword 'interval' affects the frequency at which pollloop()
        will check the files.  Keywords arguments will be passed along
        to the TailedFiles."""
        self.interval = kw.get('interval', 0.1)
        self.files = [TailedFile(f, **kw) for f in files]
    def poll(self):
        """If any files have grown, return a tuple containing the
        filename and new text.  If no files have changed, we return None.
        Note that this function is a generator so that it will (try to)
        give each file equal treatment in polling."""
        while 1:
            for f in self.files:
                s = f.poll()
                if s:
                    yield (f, s)
            else:
                yield None
    def multipoll(self):
        """Returns a list of changes in files.  It returns a list of
        (filename, newtext) tuples.  If there are no changes, it will
        return the empty list."""
        changes = []
        for f in self.files:
            s = f.poll()
            if s:
                changes.append((f, s))
        return changes
    def pollloop(self, callback):
        """Continously watches the files for changes, sleeping for
        'interval' amount of seconds in between (see __init__).  If there
        are any changes, it will call the callback with two arguments:
        the filename and new text."""
        while 1:
            changes = self.multipoll()
            for change in changes:
                callback(*change)
            time.sleep(self.interval)

if __name__ == '__main__':
    print "Tailing %s:" % (', '.join(sys.argv[1:]))
    def printer(filename, s):
        if s: 
            print "%s:\t%r" % (filename, s)
            sys.stdout.flush()
    t = Tailer(*sys.argv[1:])
    t.pollloop(printer)