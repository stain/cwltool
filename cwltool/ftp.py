from __future__ import absolute_import

import fnmatch
from ftplib import FTP
import glob
import os
import sys
from io import open
from urllib import urlopen
from typing import (IO, BinaryIO, List,  # pylint: disable=unused-import
                    Text, Union, overload)

import six
from six.moves import urllib
from schema_salad.ref_resolver import file_uri, uri_file_path

from .utils import onWindows
from .stdfsaccess import StdFsAccess

if sys.version_info < (3, 4):
    from pathlib2 import PosixPath
else:
    from pathlib import PosixPath

def abspath(src, basedir):  # type: (Text, Text) -> Text
    if src.startswith(u"file://"):
        ab = six.text_type(uri_file_path(str(src)))
    elif urllib.parse.urlsplit(src).scheme in ['http','https', 'ftp']:
        return src
    else:
        if basedir.startswith(u"file://"):
            ab = src if os.path.isabs(src) else basedir+ '/'+ src
        else:
            ab = src if os.path.isabs(src) else os.path.join(basedir, src)
    return ab

class FtpFsAccess(StdFsAccess):
    def __init__(self, host, user, passwd, port=21):  # type: (Text) -> None
        self.host = host
        self.user = user
        self.passwd = passwd
        self.port = port
        self.ftp = None

    def _connect(self): # type: () -> None
            self.ftp = FTP(self.host, self.user, self.passwd)

    def _abs(self, p):  # type: (Text) -> Text
        return abspath(p, self.basedir)

    def glob(self, pattern):  # type: (Text) -> List[Text]  
        return self._glob(pattern)

    def _glob0(self, basename, basepath):
        if basename == '':
            if self.isdir(basepath):
                return [basename]
        else:
            if self.isfile(self.join(basepath, basename)):
                return [basename]
        return []

    def _glob1(self, pattern, basepath=None):
        try:
            names = self.listdir(basepath)
        except Exception:
            return []
        if pattern[0] != '.':
            names = filter(lambda x: x[0] != '.', names)
        return fnmatch.filter(names, pattern)

    def _glob(self, pattern, basepath=None):  # type: (Text) -> List[Text]  
        if not self.ftp:
            self._connect()
        dirname, basename = pattern.rsplit('/', 1)
        if not glob.has_magic(pattern):
            if basename:
                if not pattern.endswith('/') and \
                        self.isfile(self.join(basepath, pattern)):
                    return [pattern]
            else:  # Patterns ending in slash should match only directories
                if self.isdir(self.join(basepath, dirname)):
                    return [pattern]
            return []
        if not dirname:
            return self._glob1(basename)

        dirs = self._glob(dirname)
        if glob.has_magic(basename):
            glob_in_dir = self._glob1
        else:
            glob_in_dir = self._glob0
        results = []
        for dirname in dirs:
            results.extend(glob_in_dir(dirname, basename))
        return results


    # overload is related to mypy type checking and in no way
    # modifies the behaviour of the function.
    @overload
    def open(self, fn, mode='rb'):  # type: (Text, str) -> IO[bytes]
        pass

    @overload
    def open(self, fn, mode='r'):  # type: (Text, str) -> IO[str]
        pass

    def open(self, fn, mode):
        if 'r' in mode:
            return urlopen("ftp://{}:{}@{}/{}".format(
                self.user, self.passwd, self.host, fn))

    def exists(self, fn):  # type: (Text) -> bool
        return os.path.exists(self._abs(fn))

    def isfile(self, fn):  # type: (Text) -> bool
        return bool(self.ftp.size(fn))

    def isdir(self, fn):  # type: (Text) -> bool
       return bool(self.listdir(fn))

    def listdir(self, fn):  # type: (Text) -> List[Text]
        return self.ftp.nlst(fn)

    def join(self, path, *paths):  # type: (Text, *Text) -> Text
        return PosixPath.join(path, *paths)

    def realpath(self, path):  # type: (Text) -> Text
        return os.path.realpath(path)

    # On windows os.path.realpath appends unecessary Drive, here we would avoid that
    def docker_compatible_realpath(self, path):  # type: (Text) -> Text
        if onWindows():
            if path.startswith('/'):
                return path
            return '/'+path
        return self.realpath(path)
