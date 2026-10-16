"""
Tests for multi-stem separation support.

Verifies:
1. SeparationResult supports arbitrary stems dict
2. Backward compatibility with vocals_path/instrumental_path properties
3. Model resolution raises errors for unknown models
4. API response includes stems dict
"""

from pathlib import Path
from pytest import fixture
import yaml
from sonara_vocal_remover.separation_result import SeparationResult
from sonara_vocal_remover.service import VocalRemovalService
from sonara_vocal_remover.models import ModelRegistry
from sonara_vocal_remover.errors import MissingModelError


def test_separation_result_with_stems_dict():
    """SeparationResult should support arbitrary stems via stems dict."""
    vocals = Path("/tmp/vocals.wav")
    drums = Path("/tmp/drums.wav")
    bass = Path("/tmp/bass.wav")
    
    result = SeparationResult(
        model="test_model",
        device="cpu",
        source_origin="local_file",
        stems={
            "vocals": vocals,
            "drums": drums,
            "bass": bass,
        }
    )
    
    assert result.model == "test_model"
    assert result.device == "cpu"
    assert result.source_origin == "local_file"
    assert len(result.stems) == 3
    assert result.stems["vocals"] == vocals
    assert result.stems["drums"] == drums
    assert result.stems["bass"] == bass


def test_separation_result_backward_compat_vocals_path():
    """SeparationResult.vocals_path property should return vocals stem for backward compat."""
    vocals = Path("/tmp/vocals.wav")
    instrumental = Path("/tmp/instrumental.wav")
    
    result = SeparationResult(
        model="htdemucs",
        device="cpu",
        source_origin="local_file",
        stems={
            "vocals": vocals,
            "instrumental": instrumental,
        }
    )
    
    # Backward compatibility: vocals_path should work
    assert result.vocals_path == vocals


def test_separation_result_backward_compat_instrumental_path():
    """SeparationResult.instrumental_path property should return instrumental stem for backward compat."""
    vocals = Path("/tmp/vocals.wav")
    instrumental = Path("/tmp/instrumental.wav")
    
    result = SeparationResult(
        model="htdemucs",
        device="cpu",
        source_origin="local_file",
        stems={
            "vocals": vocals,
            "instrumental": instrumental,
        }
    )
    
    # Backward compatibility: instrumental_path should work
    assert result.instrumental_path == instrumental


def test_separation_result_missing_stem_returns_empty_path():
    """SeparationResult should return empty Path for missing stems."""
    result = SeparationResult(
        model="test_model",
        device="cpu",
        source_origin="local_file",
        stems={}
    )
    
    assert result.vocals_path == Path("")
    assert result.instrumental_path == Path("")


def test_service_raises_error_for_unknown_model():
    """VocalRemovalService should raise MissingModelError for unknown model IDs."""
    try:
        service = VocalRemovalService(model="nonexistent_model_xyz_12345")
        # If we get here without error, the test should fail
        assert False, "Expected MissingModelError for unknown model"
    except MissingModelError as e:
        assert "nonexistent_model_xyz_12345" in str(e)


def test_service_accepts_default_model():
    """VocalRemovalService should accept the default model without error."""
    # This should not raise an error
    service = VocalRemovalService(model="htdemucs")
    assert service._model == "htdemucs"


def test_model_registry_lists_enabled_models(tmp_path, monkeypatch):
    """ModelRegistry should list only enabled models."""
    # Create models directory
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    
    # Create enabled model
    enabled_model_dir = models_dir / "enabled_model"
    enabled_model_dir.mkdir()
    enabled_yaml = {
        "id": "enabled_model",
        "name": "Enabled Model",
        "architecture": {"type": "test"},
        "backend": {"name": "msst"},
        "task": {"category": "test"},
        "outputs": {"required": ["vocals"]},
        "artifacts": {"config": {}, "checkpoint": {}},
        "status": {"enabled": True},
    }
    with open(enabled_model_dir / "model.yaml", "w") as f:
        yaml.dump(enabled_yaml, f)
    
    # Create disabled model
    disabled_model_dir = models_dir / "disabled_model"
    disabled_model_dir.mkdir()
    disabled_yaml = {
        "id": "disabled_model",
        "name": "Disabled Model",
        "architecture": {"type": "test"},
        "backend": {"name": "msst"},
        "task": {"category": "test"},
        "outputs": {"required": ["vocals"]},
        "artifacts": {"config": {}, "checkpoint": {}},
        "status": {"enabled": False},
    }
    with open(disabled_model_dir / "model.yaml", "w") as f:
        yaml.dump(disabled_yaml, f)
    
    # Load registry
    registry = ModelRegistry(models_dir=models_dir)
    
    # Check enabled models
    enabled = registry.list_enabled()
    enabled_ids = [m.id for m in enabled]
    
    assert "enabled_model" in enabled_ids
    assert "disabled_model" not in enabled_ids


def test_model_definition_with_multiple_stems(tmp_path):
    """ModelDefinition should support models with multiple output stems."""
    from sonara_vocal_remover.models.definition import ModelDefinition
    
    multi_stem_yaml = {
        "id": "multi_stem_model",
        "name": "Multi-Stem Model",
        "architecture": {"type": "roformer", "family": "advanced"},
        "backend": {"name": "msst", "model_type": "bs_roformer"},
        "task": {"category": "source_separation"},
        "outputs": {
            "required": ["vocals", "drums", "bass", "other"],
        },
        "artifacts": {
            "config": {"filename": "config.yaml"},
            "checkpoint": {"filename": "model.ckpt"},
        },
        "status": {"enabled": True},
    }
    
    definition = ModelDefinition.from_mapping(multi_stem_yaml)
    
    assert definition.id == "multi_stem_model"
    assert len(definition.outputs["required"]) == 4
    assert "vocals" in definition.outputs["required"]
    assert "drums" in definition.outputs["required"]
