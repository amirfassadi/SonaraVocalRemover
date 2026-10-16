import sys
from pathlib import Path

import pytest

from sonara_vocal_remover.errors import MissingModelError, SonaraError
from sonara_vocal_remover.models import ModelDefinition, ModelRegistry
from sonara_vocal_remover.separation.msst_engine import MSSTSeparationEngine
from sonara_vocal_remover.service import VocalRemovalService


@pytest.fixture
def sample_model_yaml() -> str:
    return """
id: bs_roformer_viperx_12975
name: "BS-RoFormer viperx 12.9755"
provenance:
  author: "viperx"
  repository: "ZFTurbo/Music-Source-Separation-Training"
architecture:
  family: "roformer"
  type: "bs_roformer"
backend:
  name: "msst"
  model_type: "bs_roformer"
task:
  category: "vocal_separation"
  target: "vocals"
outputs:
  required:
    - "vocals"
  optional:
    - "instrumental"
audio:
  sample_rate: 44100
  channels: 2
artifacts:
  config:
    filename: "model_bs_roformer_ep_317_sdr_12.9755.yaml"
  checkpoint:
    filename: "model_bs_roformer_ep_317_sdr_12.9755.ckpt"
resources:
  inference:
    estimated_vram_gb: null
runtime:
  chunk_size: null
  overlap: null
  tta: null
benchmark:
  external: []
status:
  enabled: false
  verified: unknown
notes:
  - "Reference model for the Sonara model registry."
"""


def test_registry_discovers_model_from_models_dir(tmp_path, monkeypatch, sample_model_yaml):
    model_dir = tmp_path / "Models" / "bs_roformer_viperx_12975"
    model_dir.mkdir(parents=True)
    (model_dir / "model.yaml").write_text(sample_model_yaml, encoding="utf-8")

    registry = ModelRegistry(models_dir=tmp_path / "Models")
    found = registry.list_all()

    assert [model.id for model in found] == ["bs_roformer_viperx_12975"]


def test_registry_parses_expected_fields(sample_model_yaml):
    parsed = ModelDefinition.from_yaml_text(sample_model_yaml)

    assert parsed.name == "BS-RoFormer viperx 12.9755"
    assert parsed.architecture["type"] == "bs_roformer"
    assert parsed.backend["name"] == "msst"
    assert parsed.task["category"] == "vocal_separation"
    assert parsed.outputs["required"] == ["vocals"]
    assert parsed.artifacts["config"]["filename"] == "model_bs_roformer_ep_317_sdr_12.9755.yaml"


def test_disabled_model_is_not_listed_as_enabled(tmp_path, sample_model_yaml):
    model_dir = tmp_path / "Models" / "bs_roformer_viperx_12975"
    model_dir.mkdir(parents=True)
    (model_dir / "model.yaml").write_text(sample_model_yaml, encoding="utf-8")

    registry = ModelRegistry(models_dir=tmp_path / "Models")

    assert registry.get("bs_roformer_viperx_12975").id == "bs_roformer_viperx_12975"
    assert registry.list_enabled() == []


def test_duplicate_model_ids_raise_clear_error(tmp_path, sample_model_yaml):
    model_dir_a = tmp_path / "Models" / "a"
    model_dir_b = tmp_path / "Models" / "b"
    model_dir_a.mkdir(parents=True)
    model_dir_b.mkdir(parents=True)
    (model_dir_a / "model.yaml").write_text(sample_model_yaml, encoding="utf-8")
    (model_dir_b / "model.yaml").write_text(sample_model_yaml, encoding="utf-8")

    with pytest.raises(SonaraError, match="Duplicate model ID"):
        ModelRegistry(models_dir=tmp_path / "Models")


def test_invalid_yaml_raises_clear_error(tmp_path):
    model_dir = tmp_path / "Models" / "broken"
    model_dir.mkdir(parents=True)
    file_path = model_dir / "model.yaml"
    file_path.write_text("id: [broken\n", encoding="utf-8")

    with pytest.raises(SonaraError, match="model.yaml"):
        ModelRegistry(models_dir=tmp_path / "Models")


def test_missing_required_field_raises_clear_error(tmp_path):
    model_dir = tmp_path / "Models" / "missing"
    model_dir.mkdir(parents=True)
    (model_dir / "model.yaml").write_text(
        "id: missing_model\nname: Missing\nbackend:\n  name: msst\n",
        encoding="utf-8",
    )

    with pytest.raises(SonaraError, match="missing.*architecture"):
        ModelRegistry(models_dir=tmp_path / "Models")


def test_registry_path_is_independent_of_cwd(tmp_path, monkeypatch, sample_model_yaml):
    model_dir = tmp_path / "Models" / "bs_roformer_viperx_12975"
    model_dir.mkdir(parents=True)
    (model_dir / "model.yaml").write_text(sample_model_yaml, encoding="utf-8")

    other_dir = tmp_path / "elsewhere"
    other_dir.mkdir()
    monkeypatch.chdir(other_dir)

    registry = ModelRegistry()
    assert registry.get("bs_roformer_viperx_12975").name == "BS-RoFormer viperx 12.9755"


def test_msst_engine_uses_model_definition_values(tmp_path, sample_model_yaml):
    definition = ModelDefinition.from_yaml_text(sample_model_yaml)
    model_dir = tmp_path / "model_cache"
    model_dir.mkdir()
    (model_dir / "model_bs_roformer_ep_317_sdr_12.9755.yaml").write_text("config: ok", encoding="utf-8")
    (model_dir / "model_bs_roformer_ep_317_sdr_12.9755.ckpt").write_bytes(b"checkpoint")

    engine = MSSTSeparationEngine(model_definition=definition, device="cuda", timeout_seconds=1.5)
    engine._model_cache_dir = model_dir

    class FakeProcess:
        def __init__(self):
            self.pid = 111
            self.stdout = type("Std", (), {"close": lambda self: None})()
            self.stderr = type("Std", (), {"close": lambda self: None})()
            self.returncode = 0
            self._closed = False

        def communicate(self, timeout=None):
            return ("", "")

        def poll(self):
            return 0

        def wait(self, timeout=None):
            return 0

    def fake_popen(cmd, **kwargs):
        output_dir = Path(cmd[cmd.index("--output") + 1])
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "vocals.wav").write_bytes(b"vocals")
        (output_dir / "instrumental.wav").write_bytes(b"instrumental")
        return FakeProcess()

    import sonara_vocal_remover.separation.msst_engine as msst_module

    msst_module.subprocess.Popen = fake_popen
    msst_module.shutil.which = lambda *args, **kwargs: "/tmp/msst"

    input_audio = tmp_path / "song.wav"
    input_audio.write_bytes(b"RIFF....WAVE")
    output_dir = tmp_path / "out"

    result = engine.separate(input_audio, output_dir)

    assert result.vocals_path.name == "vocals.wav"
    assert result.instrumental_path.name == "instrumental.wav"
    command = engine._build_command(input_audio, output_dir)
    assert command[:4] == [str(Path(sys.executable)), "-m", "msst", "inference"]


def test_service_selects_engine_by_backend_type(tmp_path, monkeypatch):
    service = VocalRemovalService(model="htdemucs")
    assert service._engine.__class__.__name__ == "DemucsSeparationEngine"

    registry = ModelRegistry(models_dir=tmp_path / "Models")
    model_def = ModelDefinition(
        id="msst_test_model",
        name="MSST Test Model",
        provenance={"author": "test"},
        architecture={"type": "bs_roformer"},
        backend={"name": "msst", "model_type": "bs_roformer"},
        task={"category": "vocal_separation", "target": "vocals"},
        outputs={"required": ["vocals"], "optional": ["instrumental"]},
        audio={"sample_rate": 44100, "channels": 2},
        artifacts={"config": {"filename": "config.yaml"}, "checkpoint": {"filename": "checkpoint.ckpt"}},
        resources={"inference": {"estimated_vram_gb": None}},
        runtime={"chunk_size": None, "overlap": None, "tta": None},
        benchmark={"external": []},
        status={"enabled": True},
        notes=[],
    )
    registry._definitions[model_def.id] = model_def
    monkeypatch.setattr("sonara_vocal_remover.service.ModelRegistry", lambda: registry)
    service_2 = VocalRemovalService(model=model_def.id)
    service_2._registry = registry
    service_2._engine = None
    service_2._resolve_engine(model_def)
    assert service_2._engine.__class__.__name__ == "MSSTSeparationEngine"


def test_service_preserves_explicit_engine_injection():
    class FakeEngine:
        pass

    service = VocalRemovalService(model="htdemucs", engine=FakeEngine())
    assert isinstance(service._engine, FakeEngine)


def test_model_definition_missing_artifact_is_raised_as_missing_model_error(tmp_path, sample_model_yaml):
    definition = ModelDefinition.from_yaml_text(sample_model_yaml)
    engine = MSSTSeparationEngine(model_definition=definition, device="cpu")
    missing_model = tmp_path / "model_cache"
    missing_model.mkdir()
    engine._model_cache_dir = missing_model

    with pytest.raises(MissingModelError):
        engine._resolve_model_artifacts()
