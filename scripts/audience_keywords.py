"""行业/模式 -> 受众搜索关键词词库。

可 import，也可命令行调用：
    python audience_keywords.py --industry "包装袋/包材" --mode b2b [--extra 自定义词1,自定义词2]

输出逗号分隔的关键词列表，直接传给 audience_search.py --keywords。
"""

import argparse

# 行业关键词映射：key -> (别名列表, 兴趣关键词, 身份关键词)
INDUSTRY_KEYWORDS = {
    "packaging": {
        "aliases": ["包", "包装", "包材", "packag", "pouch", "bag"],
        "interests": [
            "packaging",
            "packaging bags",
            "plastic packaging",
            "flexible packaging",
            "stand up pouch",
            "packaging industry",
            "food packaging",
            "cosmetic packaging",
            "design",
        ],
        "identity": [
            "packaging",
            "packaging and labeling",
            "manufacturing",
            "wholesale",
        ],
    },
    "food": {
        "aliases": ["食品", "零食", "食物", "饮料", "food", "snack", "beverage"],
        "interests": [
            "food",
            "food packaging",
            "food industry",
            "snacks",
            "beverage",
            "health food",
            "organic food",
            "fast food",
            "foodie",
        ],
        "identity": [
            "food industry",
            "food processing",
            "foodservice",
            "wholesale",
            "e-commerce",
            "online shopping",
        ],
    },
    "daily_chemical": {
        "aliases": [
            "日化",
            "化妆",
            "护肤",
            "洗护",
            "美妆",
            "cosmetic",
            "skincare",
            "beauty",
            "personal care",
            "shampoo",
            "toiletries",
        ],
        "interests": [
            "cosmetics",
            "skincare",
            "personal care",
            "beauty products",
            "shampoo",
            "toiletries",
            "makeup",
            "cosmetics brands",
            "skin care brands",
        ],
        "identity": [
            "cosmetics industry",
            "personal care",
            "beauty stores",
            "e-commerce",
            "wholesale",
        ],
    },
    "apparel": {
        "aliases": ["服装", "服饰", "鞋", "apparel", "clothing", "fashion", "shoe"],
        "interests": [
            "clothing",
            "fashion",
            "shoes",
            "sportswear",
            "streetwear",
            "luxury fashion",
        ],
        "identity": [
            "apparel",
            "wholesale",
            "e-commerce",
            "online shopping",
        ],
    },
    "electronics": {
        "aliases": ["电子", "数码", "3c", "electronics", "gadget", "phone case"],
        "interests": [
            "electronics",
            "smartphones",
            "gadgets",
            "computer accessories",
            "mobile accessories",
        ],
        "identity": [
            "electronics",
            "consumer electronics",
            "wholesale",
            "e-commerce",
        ],
    },
}

# 通用 B2B 身份关键词（任何行业都适用：职业/行为/行业分类）
B2B_IDENTITY_KEYWORDS = [
    "small business owners",
    "business page admins",
    "instagram business profile admins",
    "new active business",
    "e-commerce",
    "online shopping",
    "wholesale",
    "entrepreneurship",
    "startup",
    "founder",
    "ceo",
    "purchasing manager",
    "procurement",
    "procurement manager",
    "supply chain",
    "supply chain manager",
    "product manager",
    "operations manager",
    "marketing manager",
    "business decision makers",
]

# 通用 B2C 兴趣补充
B2C_EXTRA_KEYWORDS = [
    "online shopping",
    "shopping",
    "e-commerce",
]


def resolve_industry(text):
    """根据用户输入的行业描述，返回匹配的行业 key 列表（按映射顺序）。"""
    text = (text or "").lower()
    matched = []
    for key, item in INDUSTRY_KEYWORDS.items():
        for alias in item["aliases"]:
            if alias.lower() in text:
                matched.append(key)
                break
    return matched


def expand_keywords(industry_keys, mode="b2b", extra=None):
    """按行业 + B2B/B2C 模式展开关键词列表。"""
    keywords = []
    for key in industry_keys:
        item = INDUSTRY_KEYWORDS.get(key)
        if not item:
            continue
        keywords.extend(item["interests"])
        if mode in ("b2b", "both"):
            keywords.extend(item["identity"])
    if mode == "b2b":
        keywords.extend(B2B_IDENTITY_KEYWORDS)
    elif mode == "b2c":
        keywords.extend(B2C_EXTRA_KEYWORDS)
    elif mode == "both":
        keywords.extend(B2B_IDENTITY_KEYWORDS)
        keywords.extend(B2C_EXTRA_KEYWORDS)
    keywords.extend(extra or [])
    # 去重并保持顺序
    seen = set()
    result = []
    for kw in keywords:
        kw = kw.strip()
        if kw and kw.lower() not in seen:
            seen.add(kw.lower())
            result.append(kw)
    return result


def main():
    parser = argparse.ArgumentParser(description="生成受众搜索关键词")
    parser.add_argument("--industry", required=True, help="行业描述，例如 包装袋/包材、食品、日化")
    parser.add_argument("--mode", choices=["b2b", "b2c", "both"], default="b2b")
    parser.add_argument("--extra", help="逗号分隔的补充关键词")
    args = parser.parse_args()

    keys = resolve_industry(args.industry)
    if not keys:
        print(f"未识别行业: {args.industry}，可用: {', '.join(INDUSTRY_KEYWORDS)}")
        return
    extra = [k.strip() for k in args.extra.split(",") if k.strip()] if args.extra else None
    keywords = expand_keywords(keys, args.mode, extra)
    print(",".join(keywords))


if __name__ == "__main__":
    main()
