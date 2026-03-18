from app.offline.ingest_structured import ingest_structured_records


DEMO_RECORDS = [
    {
        "issue_id": "Q2025-001",
        "phenomenon": "液压泵泄漏",
        "component": ["液压泵", "密封圈"],
        "cause": ["密封圈老化"],
        "action": ["更换密封圈", "复测验证"],
        "source_system": "demo",
    },
    {
        "issue_id": "Q2025-002",
        "phenomenon": "轴承过热",
        "component": ["轴承"],
        "cause": ["润滑不足"],
        "action": ["补充润滑脂", "复检温升"],
        "source_system": "demo",
    },
]


if __name__ == "__main__":
    print(ingest_structured_records(DEMO_RECORDS, load_batch_id="demo_batch"))
