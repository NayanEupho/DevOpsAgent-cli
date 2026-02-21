import os
import fnmatch
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from loguru import logger
import re

class SkillSet(BaseModel):
    name: str
    auto_execute: List[str] = Field(default_factory=list)
    requires_approval: List[str] = Field(default_factory=list)
    destructive: List[str] = Field(default_factory=list)
    timeout: str = "30s"
    streaming_commands: List[str] = Field(default_factory=list)

class PermissionClassifier:
    def __init__(self, skills_dir: str):
        self.skills_dir = skills_dir
        self.skills: Dict[str, SkillSet] = {}
        self.load_skills()

    def load_skills(self):
        if not os.path.exists(self.skills_dir):
            logger.warning(f"Skills directory {self.skills_dir} does not exist.")
            return

        for root, dirs, files in os.walk(self.skills_dir):
            if "SKILL.md" in files:
                skill_path = os.path.join(root, "SKILL.md")
                skill_name = os.path.basename(root)
                try:
                    self.skills[skill_name] = self.parse_skill_file(skill_path, skill_name)
                    logger.info(f"Loaded skill: {skill_name}")
                except Exception as e:
                    logger.error(f"Failed to parse {skill_path}: {e}")

    def parse_skill_file(self, path: str, name: str) -> SkillSet:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        skill = SkillSet(name=name)
        
        # Simple markdown section parsing
        current_section = None
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith('# '):
                continue
            
            if line.startswith('## '):
                current_section = line[3:].lower()
                continue
            
            if line.startswith('- '):
                rule = line[2:].strip()
                if current_section == 'auto_execute':
                    skill.auto_execute.append(rule)
                elif current_section == 'requires_approval':
                    skill.requires_approval.append(rule)
                elif current_section == 'destructive':
                    skill.destructive.append(rule)
            
            elif ':' in line and current_section == 'timeout':
                # Simplified timeout parsing
                pass # TODO: implementation

        return skill

    def classify(self, command: str) -> str:
        command = command.strip()
        
        # Check all skills
        for skill_name, skill in self.skills.items():
            # Check destructive first (highest priority)
            if self._matches_any(command, skill.destructive):
                return "destructive"
            
            # Then requires_approval
            if self._matches_any(command, skill.requires_approval):
                return "requires_approval"
            
            # Then auto_execute
            if self._matches_any(command, skill.auto_execute):
                return "auto_execute"
        
        # Default fallback
        return "requires_approval"

    def _matches_any(self, command: str, patterns: List[str]) -> bool:
        command = command.strip()
        for pattern in patterns:
            pattern = pattern.strip()
            # 1. Exact match
            if command == pattern:
                return True
            # 2. Glob match
            if fnmatch.fnmatch(command, pattern):
                return True
            # 3. Intelligent "Base Command" match for trailing wildcards
            # Pattern "docker ps *" should match "docker ps"
            if pattern.endswith(" *"):
                base = pattern[:-2].strip()
                if command == base:
                    return True
            # Pattern "docker ps*" (no space) should match "docker ps"
            if pattern.endswith("*"):
                base = pattern[:-1].strip()
                if command == base:
                    return True
        return False
