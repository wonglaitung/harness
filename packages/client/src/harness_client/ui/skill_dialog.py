"""
Skill edit dialog for creating and editing skills.
"""

from pathlib import Path

from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
)

from harness_client.themes import get_theme
from harness_client.ui.dialog_styles import (
    DIALOG_MARGINS,
    DIALOG_MIN_WIDTH,
    DIALOG_SPACING,
    create_standard_form_layout,
    get_dialog_stylesheet,
    get_muted_label_stylesheet,
)


class SkillEditDialog(QDialog):
    """Dialog for creating and editing skill files."""

    def __init__(self, parent=None, skill_path: Path = None):
        super().__init__(parent)
        self.setWindowTitle("编辑技能")
        self.setMinimumSize(DIALOG_MIN_WIDTH, 500)
        self.setStyleSheet(get_dialog_stylesheet())
        self.skill_path = skill_path
        self._setup_ui()

        if skill_path and skill_path.exists():
            self._load_skill(skill_path)

    def _setup_ui(self):
        """Setup UI components."""
        theme = get_theme()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(*DIALOG_MARGINS)
        layout.setSpacing(DIALOG_SPACING)

        # Basic info
        form = create_standard_form_layout()

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("例如: code-review")
        form.addRow("名称:", self.name_edit)

        self.version_edit = QLineEdit()
        self.version_edit.setText("1.0.0")
        form.addRow("版本:", self.version_edit)

        self.author_edit = QLineEdit()
        self.author_edit.setPlaceholderText("作者名称")
        form.addRow("作者:", self.author_edit)

        self.description_edit = QLineEdit()
        self.description_edit.setPlaceholderText("技能描述")
        form.addRow("描述:", self.description_edit)

        layout.addLayout(form)

        # Triggers
        trigger_group = QGroupBox("触发条件")
        trigger_layout = QVBoxLayout(trigger_group)

        self.keywords_edit = QLineEdit()
        self.keywords_edit.setPlaceholderText("关键词，逗号分隔 (例如: review, 审查, 检查代码)")
        trigger_layout.addWidget(QLabel("关键词:"))
        trigger_layout.addWidget(self.keywords_edit)

        self.patterns_edit = QLineEdit()
        self.patterns_edit.setPlaceholderText("正则表达式，逗号分隔")
        trigger_layout.addWidget(QLabel("正则表达式:"))
        trigger_layout.addWidget(self.patterns_edit)

        layout.addWidget(trigger_group)

        # Content
        content_group = QGroupBox("技能内容 (Markdown)")
        content_layout = QVBoxLayout(content_group)

        self.content_edit = QTextEdit()
        self.content_edit.setPlaceholderText(
            """
你是一个专业的...

当用户请求时，请：

1. **第一步**: ...
2. **第二步**: ...
""".strip()
        )
        self.content_edit.setMinimumHeight(200)
        content_layout.addWidget(self.content_edit)

        layout.addWidget(content_group)

        # Enabled
        self.enabled_check = QCheckBox("启用此技能")
        self.enabled_check.setChecked(True)
        layout.addWidget(self.enabled_check)

        # Preset save location info
        self.save_location_label = QLabel()
        self.save_location_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.TEXT_MUTED};
                font-size: {theme.FONT_SIZE_XS};
                padding: 4px;
            }}
        """)
        self.save_location_label.setWordWrap(True)
        layout.addWidget(self.save_location_label)
        self._update_save_location()

        # Connect name change to update save location
        self.name_edit.textChanged.connect(self._update_save_location)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # Set up focus chain for keyboard navigation
        self._setup_focus_chain()

    def _setup_focus_chain(self):
        """Set up tab order for keyboard navigation."""
        self.setTabOrder(self.name_edit, self.version_edit)
        self.setTabOrder(self.version_edit, self.author_edit)
        self.setTabOrder(self.author_edit, self.description_edit)
        self.setTabOrder(self.description_edit, self.keywords_edit)
        self.setTabOrder(self.keywords_edit, self.patterns_edit)
        self.setTabOrder(self.patterns_edit, self.content_edit)
        self.setTabOrder(self.content_edit, self.enabled_check)

    def _load_skill(self, path: Path):
        """Load skill from file."""
        try:
            from harness import Skill

            skill = Skill.from_file(path)

            self.name_edit.setText(skill.name)
            self.version_edit.setText(skill.version)
            self.description_edit.setText(skill.description)
            self.content_edit.setPlainText(skill.content)

            if skill.triggers:
                if skill.triggers.keywords:
                    self.keywords_edit.setText(", ".join(skill.triggers.keywords))
                if skill.triggers.patterns:
                    self.patterns_edit.setText(", ".join(skill.triggers.patterns))

            if hasattr(skill, "author"):
                self.author_edit.setText(skill.author or "")

        except Exception as e:
            print(f"Error loading skill: {e}")

    def _update_save_location(self):
        """Update the save location label."""
        from harness_client.utils.settings import get_config_dir

        config_dir = get_config_dir()
        name = self.name_edit.text().strip()
        if name:
            save_path = config_dir / "skills" / f"{name}.md"
            self.save_location_label.setText(f"保存位置: {save_path}")
        else:
            self.save_location_label.setText(f"保存位置: {config_dir / 'skills'}/{{技能名称}}.md")

    def get_skill_data(self) -> dict:
        """Get skill data from form."""
        return {
            "name": self.name_edit.text().strip(),
            "version": self.version_edit.text().strip() or "1.0.0",
            "author": self.author_edit.text().strip(),
            "description": self.description_edit.text().strip(),
            "content": self.content_edit.toPlainText(),
            "keywords": [k.strip() for k in self.keywords_edit.text().split(",") if k.strip()],
            "patterns": [p.strip() for p in self.patterns_edit.text().split(",") if p.strip()],
            "enabled": self.enabled_check.isChecked(),
        }

    def save_to_file(self, path: Path) -> bool:
        """Save skill to file."""
        data = self.get_skill_data()
        if not data["name"]:
            return False

        try:
            from harness import Skill, SkillTrigger

            skill = Skill(
                name=data["name"],
                version=data["version"],
                description=data["description"],
                content=data["content"],
                triggers=SkillTrigger(
                    keywords=data["keywords"],
                    patterns=data["patterns"],
                ),
            )

            skill.to_file(path)
            return True

        except Exception as e:
            print(f"Error saving skill: {e}")
            return False
