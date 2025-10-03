import os
import zlib
import fcntl
import queue
import struct
import orjson as json

from os import fsync
from pathlib import Path
from threading import Lock, Event, Thread
from typing import Generator, Union, Tuple, IO

from .exceptions import (
    DuraLogConfigurationError,
    DuraLogCorruptionError,
    DuraLogIOError,
)


class DuraLog:
    _instance = None
    _singleton_lock = Lock()

    def __new__(cls, *args, **kwargs):
        if not kwargs.get("file_path"):
            raise DuraLogConfigurationError(
                "DuraLog must be instantiated with a 'file_path' argument."
            )

        if not cls._instance:
            with cls._singleton_lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        file_path: str,
        commit_interval_seconds: int = 1,
        max_queue_size: int = 100_000,
    ):
        if hasattr(self, "_initialized"):
            return None

        self._TYPE_JSON = 0x01
        self._TYPE_STRING = 0x02

        # < (Little-endian)
        # I (4-byte unsigned int) Payload Size
        # B (1-byte unsigned char) Type Flag
        # I (4-byte unsigned int) Checksum
        self._HEADER_FORMAT = "<IBI"
        self._HEADER_SIZE = struct.calcsize(self._HEADER_FORMAT)

        self.file_path = Path(file_path).resolve()
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

        self.file = None
        self._reopen_file()

        self._commit_interval_seconds = commit_interval_seconds
        self._lock = Lock()
        self._record_queue = queue.Queue(maxsize=max_queue_size)
        self._commit_event = Event()
        self._commit_thread = Thread(target=self._commit_loop)
        self._commit_thread.start()
        self._is_closing = False
        self._initialized = True

    def _reopen_file(self):
        """Opens the log file for appending and caches its inode for rotation checks.

        Raises:
            DuraLogIOError: If the file cannot be opened or its metadata cannot be read.
        """
        try:
            if self.file and not self.file.closed:
                self.file.close()

            self.file = open(self.file_path, "a+b")
            self._inode = os.fstat(self.file.fileno()).st_ino
        except OSError as e:
            raise DuraLogIOError(
                file_path=str(self.file_path),
                message="Failed to open or stat log file.",
                original_error=e,
            ) from e

    def _serialize_payload(self, data: Union[dict, str]) -> Tuple[bytes, int]:
        """Serializes a log record's payload into bytes and determines its type.

        Args:
            data: The user-provided data (dict or str) to serialize.

        Returns:
            A tuple containing the utf-8 encoded payload and the integer type flag.
        """
        if isinstance(data, dict):
            return json.dumps(data), self._TYPE_JSON

        return data.encode("utf-8"), self._TYPE_STRING

    def _format_log_entry(self, data: Union[dict, str]) -> bytes:
        """Creates a packed binary log entry from user data.

        Args:
            data: The user-provided data (dict or str) to format.

        Returns:
            The complete log entry as a bytes object, ready for disk I/O.
        """
        payload_bytes, type_flag = self._serialize_payload(data)
        payload_size = len(payload_bytes)
        checksum = zlib.crc32(payload_bytes)
        header = struct.pack(self._HEADER_FORMAT, payload_size, type_flag, checksum)

        return header + payload_bytes

    def _sync_to_disk(self, records: list):
        """Writes records to disk, handles log rotation, and forces a sync.

        Args:
            records: A list of packed binary log entries to write.

        Raises:
            DuraLogIOError: If any file I/O operation (write, fsync, stat) fails.
        """
        try:
            if self.file.closed:
                return None

            # If the file is gone (FileNotFoundError) or the inode
            # has changed, we need to reopen our file handle.
            reopen_needed = False
            try:
                if os.stat(self.file_path).st_ino != self._inode:
                    reopen_needed = True
            except FileNotFoundError:
                reopen_needed = True

            if reopen_needed:
                self._reopen_file()

            self.file.writelines(records)
            self.file.flush()
            fsync(self.file.fileno())
        except OSError as e:
            raise DuraLogIOError(
                file_path=str(self.file_path),
                message="An OS error occurred during file write, fsync, or rotation check.",
                original_error=e,
            ) from e

    def _commit(self):
        """Flushes all pending records from the in-memory queue to disk."""
        records_to_write = []
        try:
            while True:
                packed_data = self._format_log_entry(self._record_queue.get_nowait())
                records_to_write.append(packed_data)
        except queue.Empty:
            pass

        if not records_to_write:
            return None

        try:
            fcntl.flock(self.file, fcntl.LOCK_EX)
        except OSError as e:
            # An invalid file handle could cause an error here.
            raise DuraLogIOError(
                file_path=str(self.file_path),
                message="Failed to acquire file lock.",
                original_error=e,
            ) from e

        try:
            with self._lock:
                self._sync_to_disk(records_to_write)
        finally:
            fcntl.flock(self.file, fcntl.LOCK_UN)

        return None

    def _commit_loop(self):
        """Periodically flushes queued records to disk."""
        while not self._commit_event.wait(timeout=self._commit_interval_seconds):
            self._commit()

        return None

    def append(self, data: Union[dict, str]):
        """Adds a record.

        Args:
            data: The log record to append, which must be a dict or str.

        Raises:
            TypeError: If the provided data is not a dict or a str.
        """
        self._record_queue.put(data)

        return None

    def close(self):
        """Flushes all pending records and gracefully shuts down the logger."""
        if self._is_closing or not getattr(self, "_initialized", False):
            return None

        self._is_closing = True
        self._commit_event.set()
        self._commit_thread.join()
        try:
            self._commit()
        finally:
            if self.file and not self.file.closed:
                self.file.close()

            self.__class__._instance = None
            if hasattr(self, "_initialized"):
                delattr(self, "_initialized")

    def _parse_log_entry(self, log_file: IO[bytes]) -> Union[dict, str]:
        """Reads and parses a single log entry from the current file position.

        Args:
            f: The binary file handle to read from.

        Returns:
            The deserialized log entry (dict or str).

        Raises:
            DuraLogCorruptionError: If the entry is corrupt in any way (incomplete
                                    data, checksum mismatch, unknown type).
            json.JSONDecodeError: If the payload for a JSON type is invalid.
        """
        current_offset = log_file.tell()
        header_bytes = log_file.read(self._HEADER_SIZE)

        if not header_bytes:
            raise DuraLogCorruptionError(
                file_path=str(self.file_path),
                offset=current_offset,
                reason="Incomplete header found.",
            )

        if len(header_bytes) < self._HEADER_SIZE:
            raise DuraLogCorruptionError(
                file_path=str(self.file_path),
                offset=current_offset,
                reason="Incomplete header found.",
            )

        payload_size, type_flag, expected_checksum = struct.unpack(
            self._HEADER_FORMAT, header_bytes
        )

        payload_bytes = log_file.read(payload_size)
        if len(payload_bytes) < payload_size:
            raise DuraLogCorruptionError(
                file_path=str(self.file_path),
                offset=current_offset,
                reason=f"Expected payload of size {payload_size} but got {len(payload_bytes)}.",
            )

        actual_checksum = zlib.crc32(payload_bytes)
        if actual_checksum != expected_checksum:
            raise DuraLogCorruptionError(
                file_path=str(self.file_path),
                offset=current_offset,
                reason="CRC32 checksum mismatch.",
            )

        if type_flag == self._TYPE_JSON:
            return json.loads(payload_bytes)
        elif type_flag == self._TYPE_STRING:
            return payload_bytes.decode("utf-8")
        else:
            # An unknown type flag is a form of corruption.
            raise DuraLogCorruptionError(
                file_path=str(self.file_path),
                offset=current_offset,
                reason=f"Unknown record type flag: {type_flag}",
            )

    def replay(self) -> Generator[Union[dict, str], None, None]:
        """Reads the log file from the beginning and yields each valid record.

        This method provides a "snapshot" view of the log. It reads the log's
        contents up to the size it was when the method was first called,
        ignoring any data that is subsequently appended by concurrent writes.
        Corrupted or improperly formatted records are automatically skipped.

        Yields:
            A dictionary or string for each successfully read log record.

        Raises:
            DuraLogIOError: If the log file cannot be opened or read.
        """
        try:
            snapshot_size = os.path.getsize(self.file_path)
        except OSError as e:
            raise DuraLogIOError(
                file_path=str(self.file_path),
                message="Failed to get initial size of log file.",
                original_error=e,
            ) from e

        if snapshot_size == 0:
            return None

        try:
            with open(self.file_path, "rb") as log_file:
                while log_file.tell() < snapshot_size:
                    try:
                        # Check if a potential record would read past the snapshot
                        if log_file.tell() + self._HEADER_SIZE > snapshot_size:
                            break

                        record = self._parse_log_entry(log_file)
                        yield record
                    except (DuraLogCorruptionError, json.JSONDecodeError):
                        # A parsing error means the record is corrupt. We skip it
                        # by continuing to the next iteration of the loop.
                        # The file pointer has already been advanced by the failed
                        # read attempt, so we will not get stuck.
                        continue
        except OSError as e:
            raise DuraLogIOError(
                file_path=str(self.file_path),
                message="An OS error occurred during log replay.",
                original_error=e,
            ) from e
