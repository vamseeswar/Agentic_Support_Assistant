import re
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from app.config import settings
from app.models import PolicyChunk, PolicySearchResult

logger = logging.getLogger(__name__)

# Keyword mappings for policy sections
SECTION_KEYWORDS: Dict[str, List[str]] = {
    "1.1": ["dispatch", "same day", "cutoff", "2pm", "business day"],
    "1.2": ["delivery", "estimate", "metro", "non-metro", "days"],
    "1.3": ["shipping", "charge", "fee", "free", "express", "1499", "99"],
    "1.4": ["partial", "backorder", "backordered"],
    "1.5": ["delayed", "delay", "late", "credit", "250", "store credit"],
    "1.6": ["lost", "missing", "no tracking", "lost in transit", "claim"],
    "1.7": ["address", "change", "redirect"],
    "2.1": ["return window", "30 days", "30 calendar", "return period", "when can i return"],
    "2.2": ["condition", "tags", "unworn", "unwashed", "original packaging"],
    "2.3": ["non-returnable", "not returnable", "jewellery", "innerwear", "socks", "beauty", "fragrance", "face mask", "gift card", "hygiene"],
    "2.4": ["final sale", "final_sale", "no refund", "size exchange only"],
    "2.5": ["footwear", "shoe box", "shoes", "sneakers", "box", "300 deduction"],
    "2.6": ["cancelled", "cancel", "cancellation refund"],
    "3.1": ["refund", "timeline", "credit card", "upi", "cash on delivery", "cod", "how long", "when refund"],
    "3.2": ["shipping fee", "99 refund", "trendly error", "wrong item", "damaged", "defective"],
    "3.3": ["bank", "bank details", "bank account", "cod refund", "cash on delivery refund"],
    "3.4": ["partial refund", "partial return"],
    "4.1": ["exchange", "size exchange", "colour", "color", "style", "swap"],
    "4.2": ["exchange window", "30 day exchange"],
    "4.3": ["unavailable", "size unavailable", "out of stock"],
    "4.4": ["second exchange", "one exchange", "limit", "human approval"],
    "5.1": ["pickup", "reverse pickup", "schedule pickup"],
    "5.2": ["non-serviceable", "self-ship", "warehouse", "150 reimbursement"],
    "5.3": ["failed pickup", "2 attempts", "re-raise"],
    "6.1": ["damaged", "defective", "wrong", "incorrect", "48 hours", "photograph"],
    "6.2": ["replacement", "damaged resolution"],
    "7": ["assistant must not", "prohibited", "discount", "coupon", "bank number", "system prompt"],
}


class PolicyRepository:
    """Repository for lexical retrieval from the Trendly policy document."""

    def __init__(self, policy_file_path: Optional[Path] = None):
        self.file_path = policy_file_path or settings.POLICY_FILE
        self._raw_text: str = ""
        self._chunks: List[PolicyChunk] = []
        self._load_and_chunk()

    def _load_and_chunk(self):
        if not self.file_path.exists():
            raise FileNotFoundError(f"Policy file not found at {self.file_path}")
        with open(self.file_path, "r", encoding="utf-8") as f:
            self._raw_text = f.read()
        self._chunks = self._parse_chunks(self._raw_text)
        logger.info(f"Loaded policy with {len(self._chunks)} sections.")

    def _parse_chunks(self, text: str) -> List[PolicyChunk]:
        """Split policy markdown into numbered section chunks."""
        chunks: List[PolicyChunk] = []
        # Match lines like **1.1 Dispatch times.**
        pattern = re.compile(r"\*\*(\d+\.\d+)\s+([^*]+?)\.\*\*\s*(.+?)(?=\*\*\d+\.\d+|\Z)", re.DOTALL)
        for match in pattern.finditer(text):
            sec_num = match.group(1).strip()
            sec_title = match.group(2).strip()
            content = match.group(3).strip()
            keywords = SECTION_KEYWORDS.get(sec_num, [])
            chunks.append(PolicyChunk(
                section_number=sec_num,
                section_title=sec_title,
                content=content,
                keywords=keywords,
            ))

        # Also parse top-level H2 sections (## 1. Shipping etc.)
        h2_pattern = re.compile(r"^## (\d+)\.\s+(.+)$", re.MULTILINE)
        for m in h2_pattern.finditer(text):
            sec_num = m.group(1)
            sec_title = m.group(2).strip()
            kws = SECTION_KEYWORDS.get(sec_num, [])
            if not any(c.section_number == sec_num for c in chunks):
                chunks.append(PolicyChunk(
                    section_number=sec_num,
                    section_title=sec_title,
                    content="",
                    keywords=kws,
                ))

        return chunks

    def search(self, query: str, top_k: int = 3) -> PolicySearchResult:
        """Lexical search over policy chunks. Returns relevant sections with source citations."""
        query_lower = query.lower()
        scored: List[tuple] = []

        for chunk in self._chunks:
            score = 0
            # Keyword match
            for kw in chunk.keywords:
                if kw in query_lower:
                    score += 3
            # Title match
            if chunk.section_title.lower() in query_lower:
                score += 2
            # Content token match
            query_tokens = re.findall(r"\w+", query_lower)
            for token in query_tokens:
                if len(token) > 3 and token in chunk.content.lower():
                    score += 1
            if score > 0:
                scored.append((score, chunk))

        scored.sort(key=lambda x: x[0], reverse=True)
        top_chunks = [c for _, c in scored[:top_k]]

        if not top_chunks:
            return PolicySearchResult(
                found=False,
                query=query,
                matched_sections=[],
                snippet="Policy information not found for this query.",
                source="trendly_policy.md",
            )

        matched_sections = [
            {
                "section_number": c.section_number,
                "section_title": c.section_title,
                "content": c.content[:800],
            }
            for c in top_chunks
        ]
        snippet = "\n\n".join(
            f"[Policy §{c.section_number} – {c.section_title}]\n{c.content[:600]}"
            for c in top_chunks
        )
        return PolicySearchResult(
            found=True,
            query=query,
            matched_sections=matched_sections,
            snippet=snippet,
            source="trendly_policy.md",
        )

    def get_full_text(self) -> str:
        return self._raw_text


policy_repository = PolicyRepository()
