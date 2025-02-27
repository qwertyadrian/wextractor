import io
from dataclasses import dataclass, field
from pathlib import Path
from typing import BinaryIO, List, Union


@dataclass
class File:
    name: str
    offset: int
    size: int
    data: bytes = field(repr=False, init=False)


class Package:
    def __init__(self, filename: Union[str, Path]):
        self.filename = filename
        self.filecount: int = 0
        self.files: List[File] = list()
        self.version: str = ""
        self._fd: BinaryIO
        self._ds_ptr: int = 0
        self._prepare_file()
        self._read_files()

    def _prepare_file(self):
        self._fd = open(self.filename, "r+b")
        self._fd.seek(0, io.SEEK_SET)
        self._read_header()

    def _read_header(self):
        self.version = self._read_str()
        self.filecount = int.from_bytes(self._fd.read(4), "little", signed=False)

    def _read_str(self) -> str:
        size = int.from_bytes(self._fd.read(4), "little", signed=False)
        buf = self._fd.read(size).decode()
        return buf

    def _read_files(self):
        for i in range(self.filecount):
            self.files.append(
                File(
                    name=self._read_str(),
                    offset=int.from_bytes(self._fd.read(4), "little", signed=False),
                    size=int.from_bytes(self._fd.read(4), "little", signed=False),
                )
            )
            self._ds_ptr = self._fd.tell()  # data structure pointer

        for file in self.files:
            self._fd.seek(self._ds_ptr + file.offset, io.SEEK_SET)
            file.data = self._fd.read(file.size)

    @staticmethod
    def save_file(file: File):
        path = Path(file.name)
        if path.match("*/*.*"):
            path.parent.mkdir(parents=True, exist_ok=True)

        with path.open("wb"):
            path.write_bytes(file.data)
