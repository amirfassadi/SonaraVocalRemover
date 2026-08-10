import pytest

from sonara_vocal_remover.errors import InvalidLocalFileError, UnsupportedAudioFormatError
from sonara_vocal_remover.sources.local_file import LocalFileSource


def test_missing_file_raises(tmp_path):
    missing = tmp_path / "nope.wav"
    with pytest.raises(InvalidLocalFileError):
        LocalFileSource(str(missing)).acquire()


def test_unsupported_extension_raises(tmp_path):
    bad = tmp_path / "song.xyz"
    bad.write_bytes(b"not audio")
    with pytest.raises(UnsupportedAudioFormatError):
        LocalFileSource(str(bad)).acquire()


def test_valid_wav_file_acquires(tmp_path):
    good = tmp_path / "song.wav"
    good.write_bytes(b"RIFF....WAVEfmt ")
    resource = LocalFileSource(str(good)).acquire()
    assert resource.path == good
    assert resource.origin == "local_file"
    assert resource.is_temporary is False
