import time
from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class EvidenceStatus(str, Enum):
    KNOWN = "KNOWN"
    VERIFIED = "VERIFIED"
    INFERRED = "INFERRED"
    UNCERTAIN = "UNCERTAIN"
    NOT_TESTED = "NOT_TESTED"

class EvidenceItem(BaseModel):
    id: str
    claim: str
    status: EvidenceStatus = EvidenceStatus.UNCERTAIN
    source: str
    source_type: str = "local"
    data: Any = None
    timestamp: float = Field(default_factory=time.time)
    verified: bool = False

class CodeDiffItem(BaseModel):
    file_path: str
    diff_text: str
    old_hash: Optional[str] = None
    new_hash: Optional[str] = None
    applied: bool = False

class TestRunRecord(BaseModel):
    test_name: str
    command: str
    passed: bool
    stdout: str = ""
    stderr: str = ""
    duration_ms: float = 0.0

class EvidenceStore:
    """
    Session-level and task-level evidence & state store.
    Ensures that assertions made by K-Jocker are strictly grounded in verified facts.
    """
    def __init__(self):
        self.evidence_items: List[EvidenceItem] = []
        self.code_diffs: List[CodeDiffItem] = []
        self.test_runs: List[TestRunRecord] = []
        self.inspected_files: List[str] = []

    def clear(self):
        self.evidence_items.clear()
        self.code_diffs.clear()
        self.test_runs.clear()
        self.inspected_files.clear()

    def record_evidence(
        self,
        claim: str,
        status: EvidenceStatus,
        source: str,
        source_type: str = "tool",
        data: Any = None
    ) -> EvidenceItem:
        item = EvidenceItem(
            id=f"ev_{len(self.evidence_items) + 1}",
            claim=claim,
            status=status,
            source=source,
            source_type=source_type,
            data=data,
            verified=(status == EvidenceStatus.VERIFIED)
        )
        self.evidence_items.append(item)
        return item

    def record_diff(self, file_path: str, diff_text: str, old_hash: str = None, new_hash: str = None, applied: bool = True):
        diff = CodeDiffItem(
            file_path=file_path,
            diff_text=diff_text,
            old_hash=old_hash,
            new_hash=new_hash,
            applied=applied
        )
        self.code_diffs.append(diff)
        return diff

    def record_test_run(self, test_name: str, command: str, passed: bool, stdout: str = "", stderr: str = "", duration_ms: float = 0.0):
        rec = TestRunRecord(
            test_name=test_name,
            command=command,
            passed=passed,
            stdout=stdout,
            stderr=stderr,
            duration_ms=duration_ms
        )
        self.test_runs.append(rec)
        return rec

    def record_file_inspection(self, file_path: str):
        if file_path not in self.inspected_files:
            self.inspected_files.append(file_path)

    def get_summary(self) -> Dict[str, Any]:
        return {
            "evidence_count": len(self.evidence_items),
            "verified_count": sum(1 for e in self.evidence_items if e.status == EvidenceStatus.VERIFIED),
            "uncertain_count": sum(1 for e in self.evidence_items if e.status == EvidenceStatus.UNCERTAIN),
            "diffs_count": len(self.code_diffs),
            "tests_run": len(self.test_runs),
            "tests_passed": sum(1 for t in self.test_runs if t.passed),
            "inspected_files": self.inspected_files
        }

evidence_store = EvidenceStore()
