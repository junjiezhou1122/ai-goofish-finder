"""
Finder 规则扩词服务。
"""
from __future__ import annotations

from collections import Counter
import re
from typing import Any

from src.domain.models.direction import Direction
from src.domain.models.direction_candidate import DirectionCandidate
from src.infrastructure.external.ai_client import AIClient
from src.services.ai_response_parser import parse_ai_response_json


RULE_SUFFIXES: dict[str, tuple[str, ...]] = {
    "product": ("教程", "资料", "模板", "脚本", "源码", "合集"),
    "service": ("代搭建", "代配置", "陪跑", "咨询", "代做"),
    "delivery": ("自动发货", "秒发", "永久"),
    "generic": ("副业", "变现", "项目"),
}

COOCCURRENCE_STOPWORDS = {
    "闲鱼", "全新", "二手", "出售", "转让", "低价", "可刀", "包邮", "现货", "正版",
    "急出", "自用", "已测", "无售后", "可拍", "实拍", "同城", "教程", "模板", "源码",
}

LLM_EXPANSION_PROMPT_TEMPLATE = """
你是一个闲鱼关键词扩展助手。你的任务是围绕一个“研究方向”，补充一批值得监控的候选关键词。

要求：
1. 输出必须是 JSON
2. 只输出 JSON，不要输出解释
3. 每个候选词必须短、像闲鱼搜索词，不要写成长句
4. 不要重复已有的种子词或规则扩词结果
5. 优先生成更贴近真实交易意图的词，而不是过度抽象的大词
6. variant_type 只能是: product / service / delivery / generic
7. confidence 范围 0 到 1
8. 最多输出 {max_candidates} 个候选词

方向信息：
- 方向名称: {direction_name}
- 种子主题: {seed_topic}
- 用户目标: {user_goal}
- 优先变体: {preferred_variants}

已有种子词 / 规则扩词结果（不要重复）：
{existing_keywords}

返回 JSON：
{{
  "candidates": [
    {{
      "keyword": "",
      "variant_type": "product",
      "reason": "",
      "confidence": 0.78
    }}
  ]
}}
"""


def _normalize_phrase(value: str) -> str:
    return " ".join(str(value or "").strip().split())


def _build_seed_phrases(direction: Direction) -> list[str]:
    phrases: list[str] = []
    for raw in (direction.seed_topic, direction.name):
        phrase = _normalize_phrase(raw)
        if not phrase or phrase in phrases:
            continue
        phrases.append(phrase)
    return phrases


def _detect_variant_type(token: str) -> str:
    if any(signal in token for signal in RULE_SUFFIXES["product"]):
        return "product"
    if any(signal in token for signal in RULE_SUFFIXES["service"]):
        return "service"
    if any(signal in token for signal in RULE_SUFFIXES["delivery"]):
        return "delivery"
    return "generic"


def _extract_cooccurrence_tokens(title: str, seed_phrases: list[str]) -> list[str]:
    normalized_title = _normalize_phrase(title)
    if not normalized_title:
        return []
    matched = any(seed in normalized_title for seed in seed_phrases)
    if not matched:
        return []

    candidate_text = normalized_title
    for seed in seed_phrases:
        candidate_text = candidate_text.replace(seed, " ")
    candidate_text = re.sub(r"[【】\[\]（）()_\-—|/\\,:：;；.!！?？]+", " ", candidate_text)
    chunks = [chunk.strip() for chunk in candidate_text.split() if chunk.strip()]

    tokens: list[str] = []
    for chunk in chunks:
        if len(chunk) < 2 or len(chunk) > 10:
            continue
        lower_chunk = chunk.lower()
        if lower_chunk in COOCCURRENCE_STOPWORDS:
            continue
        if chunk in tokens:
            continue
        tokens.append(chunk)

    merged = re.findall(r"[\u4e00-\u9fffA-Za-z0-9]{2,8}", candidate_text)
    for token in merged:
        lower_token = token.lower()
        if lower_token in COOCCURRENCE_STOPWORDS:
            continue
        if token in tokens:
            continue
        tokens.append(token)
    return tokens


def build_rule_based_candidates(direction: Direction) -> list[DirectionCandidate]:
    phrases = _build_seed_phrases(direction)
    if not phrases:
        return []

    results: list[DirectionCandidate] = []
    seen_keywords: set[str] = set()

    def _append(keyword: str, *, source_type: str, source_detail: str, lifecycle_status: str, variant_type: str, confidence: float):
        clean_keyword = _normalize_phrase(keyword)
        dedup_key = clean_keyword.lower()
        if not clean_keyword or dedup_key in seen_keywords:
            return
        seen_keywords.add(dedup_key)
        results.append(
            DirectionCandidate(
                direction_id=int(direction.id or 0),
                keyword=clean_keyword,
                source_type=source_type,
                source_detail=source_detail,
                lifecycle_status=lifecycle_status,
                variant_type=variant_type,  # type: ignore[arg-type]
                confidence=confidence,
            )
        )

    for phrase in phrases:
        _append(
            phrase,
            source_type="seed",
            source_detail="seed:direction",
            lifecycle_status="seed",
            variant_type="generic",
            confidence=1.0,
        )

    for phrase in phrases:
        for variant_type in direction.preferred_variants:
            suffixes = RULE_SUFFIXES.get(variant_type, ())
            for suffix in suffixes:
                if suffix in phrase:
                    continue
                _append(
                    f"{phrase} {suffix}",
                    source_type="rule",
                    source_detail=f"rule:{variant_type}",
                    lifecycle_status="candidate",
                    variant_type=variant_type,
                    confidence=0.72 if variant_type != "generic" else 0.6,
                )

    return results


def _normalize_llm_candidate_item(
    item: dict[str, Any],
    *,
    direction_id: int,
    seen_keywords: set[str],
) -> DirectionCandidate | None:
    keyword = _normalize_phrase(str(item.get("keyword") or ""))
    dedup_key = keyword.lower()
    if not keyword or dedup_key in seen_keywords:
        return None

    variant_type = str(item.get("variant_type") or "generic").strip().lower()
    if variant_type not in RULE_SUFFIXES:
        variant_type = "generic"

    confidence_raw = item.get("confidence", 0.68)
    try:
        confidence = max(0.0, min(1.0, float(confidence_raw)))
    except (TypeError, ValueError):
        confidence = 0.68

    reason = _normalize_phrase(str(item.get("reason") or ""))
    seen_keywords.add(dedup_key)
    return DirectionCandidate(
        direction_id=direction_id,
        keyword=keyword,
        source_type="llm",
        source_detail=reason or "llm:semantic-expansion",
        lifecycle_status="candidate",
        variant_type=variant_type,  # type: ignore[arg-type]
        confidence=confidence,
    )


async def build_llm_candidates(
    direction: Direction,
    existing_candidates: list[DirectionCandidate],
    *,
    max_candidates: int = 12,
) -> list[DirectionCandidate]:
    ai_client = AIClient()
    active_error: BaseException | None = None
    try:
        if not ai_client.is_available():
            ai_client.refresh()
        if not ai_client.is_available():
            return []

        existing_keywords = sorted({candidate.keyword for candidate in existing_candidates})
        prompt = LLM_EXPANSION_PROMPT_TEMPLATE.format(
            max_candidates=max(1, min(max_candidates, 20)),
            direction_name=direction.name,
            seed_topic=direction.seed_topic,
            user_goal=direction.user_goal or "未填写",
            preferred_variants=", ".join(direction.preferred_variants),
            existing_keywords="\n".join(f"- {keyword}" for keyword in existing_keywords) or "- 无",
        )

        response_text = await ai_client._call_ai(
            [{"role": "user", "content": prompt}],
            temperature=0.4,
            max_output_tokens=1000,
            enable_json_output=True,
        )
        payload = parse_ai_response_json(response_text)
        raw_candidates = payload.get("candidates") if isinstance(payload, dict) else None
        if not isinstance(raw_candidates, list):
            return []

        seen_keywords = {candidate.keyword.lower() for candidate in existing_candidates}
        normalized: list[DirectionCandidate] = []
        for item in raw_candidates:
            if not isinstance(item, dict):
                continue
            candidate = _normalize_llm_candidate_item(
                item,
                direction_id=int(direction.id or 0),
                seen_keywords=seen_keywords,
            )
            if candidate:
                normalized.append(candidate)
        return normalized
    except Exception as exc:
        active_error = exc
        print(f"LLM 扩词失败，降级到规则扩词: {exc}")
        # 真正回退：复用规则扩词（已有种子词部分，避免重复）
        fallback = build_rule_based_candidates(direction)
        # 只返回非种子候选，避免和已有 seed 重复
        return [c for c in fallback if c.source_type != "seed"]
    finally:
        try:
            await ai_client.close()
        except Exception as close_error:
            if active_error is None:
                raise close_error


def build_cooccurrence_candidates(
    direction: Direction,
    titles: list[str],
    existing_candidates: list[DirectionCandidate],
    *,
    max_candidates: int = 10,
) -> list[DirectionCandidate]:
    seed_phrases = _build_seed_phrases(direction)
    if not seed_phrases or not titles:
        return []

    seen_keywords = {candidate.keyword.lower() for candidate in existing_candidates}
    counter: Counter[str] = Counter()
    token_variant_map: dict[str, str] = {}

    for title in titles:
        for token in _extract_cooccurrence_tokens(title, seed_phrases):
            counter[token] += 1
            token_variant_map.setdefault(token, _detect_variant_type(token))

    results: list[DirectionCandidate] = []
    for token, count in counter.most_common(max_candidates * 2):
        variant_type = token_variant_map.get(token, "generic")
        candidate_keyword = _normalize_phrase(f"{seed_phrases[0]} {token}")
        dedup_key = candidate_keyword.lower()
        if dedup_key in seen_keywords:
            continue
        seen_keywords.add(dedup_key)
        confidence = min(0.9, 0.55 + count * 0.08)
        results.append(
            DirectionCandidate(
                direction_id=int(direction.id or 0),
                keyword=candidate_keyword,
                source_type="cooccurrence",
                source_detail=f"cooccurrence:{token}",
                lifecycle_status="candidate",
                variant_type=variant_type,  # type: ignore[arg-type]
                confidence=confidence,
            )
        )
        if len(results) >= max_candidates:
            break
    return results
