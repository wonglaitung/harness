"""客户端治理接入的纯逻辑测试（不启动 GUI）。

覆盖：
- `AppSettings` 的 strict / governance_agent_id 持久化
- 技能编辑器保存时**保留治理块**与工具声明（设计稿 §9.4 / §10.4）
"""

from __future__ import annotations

from harness_client.ui.skill_dialog import apply_form_data
from harness_client.utils.settings import AppSettings


def test_app_settings_persist_governance_fields():
    settings = AppSettings(strict=True, governance_agent_id="credit-paper-assembler")
    restored = AppSettings.from_dict(settings.to_dict())
    assert restored.strict is True
    assert restored.governance_agent_id == "credit-paper-assembler"


def test_app_settings_defaults_governance_off():
    settings = AppSettings()
    assert settings.strict is False
    assert settings.governance_agent_id == ""


def test_skill_editor_preserves_governance_and_tools():
    from harness import Skill, SkillTools

    governance = {"agent_id": "credit-paper-assembler", "version": "1.2.0"}
    source = Skill(
        name="old-name",
        description="old",
        content="old body",
        governance=governance,
        tools=SkillTools(allowed=["core_banking_api:read_only"]),
        version="1.0.0",
        author="alice",
    )

    data = {
        "name": "new-name",
        "version": "2.0.0",
        "description": "new",
        "content": "new body",
        "enabled": True,
        "author": "alice",
        "keywords": ["k1"],
        "patterns": ["p.*"],
    }
    updated = apply_form_data(source, data)

    # 表单字段被更新
    assert updated.name == "new-name"
    assert updated.version == "2.0.0"
    assert updated.description == "new"
    assert updated.content == "new body"
    # 治理块与工具声明必须保留（否则保存一次即抹掉授权书）
    assert updated.governance == governance
    assert updated.tools.allowed == ["core_banking_api:read_only"]
    assert updated.author == "alice"


def test_skill_editor_new_skill_has_no_governance():
    data = {
        "name": "fresh",
        "version": "1.0.0",
        "description": "",
        "content": "body",
        "enabled": True,
        "author": "",
        "keywords": [],
        "patterns": [],
    }
    skill = apply_form_data(None, data)
    assert skill.name == "fresh"
    assert skill.governance is None
