"""
大众点评内容工厂 — AI 文案生成模块
使用 DeepSeek API 生成探店评价文案
"""
import json
import os
import time
import random
from openai import OpenAI

# DeepSeek API 配置（兼容 OpenAI SDK）
DEEPSEEK_API_KEY = os.environ.get("SILICONFLOW_API_KEY", os.environ.get("DEEPSEEK_API_KEY", ""))
DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.siliconflow.cn/v1")
MODEL_NAME = os.environ.get("DP_MODEL", "deepseek-ai/DeepSeek-V4-Flash")

# 文案模板
TEMPLATES = {
    "food": {
        "system": "你是一个资深吃货，经常在大众点评写探店评价。你的评价口语化、有细节、像真实用户写的。",
        "prompt_template": """请为【{shop_name}】写一条探店评价，要求：
- 口语化，像真实用户写的，不要太书面
- 200-400字
- 提到{dish_count}个具体菜品，描述味道/口感
- 提到环境或服务的一个细节
- 不要用"最"、"绝对"、"第一"等绝对化用语
- 结尾给个总体感受（推荐/不推荐/会再来等）
- 不要出现明显的AI痕迹（比如"总的来说"、"综上所述"）
- 城市风格：{city}本地人口吻

请直接输出评价内容，不要加标题、不要加标签。"""
    },
    "cafe": {
        "system": "你是一个咖啡/奶茶爱好者，经常在大众点评写探店评价。风格轻松活泼。",
        "prompt_template": """请为【{shop_name}】写一条咖啡/奶茶店评价，要求：
- 口语化，轻松活泼的风格
- 150-300字
- 提到1-2个饮品的口味描述
- 提到店面氛围或拍照打卡点
- 不要用绝对化用语
- 结尾给个总体评价
- 城市风格：{city}本地人口吻

请直接输出评价内容，不要加标题。"""
    },
    "scenic": {
        "system": "你是一个喜欢探索城市好玩地方的年轻人，经常在大众点评分享打卡体验。",
        "prompt_template": """请为【{spot_name}】写一条打卡点评价，要求：
- 口语化，像年轻人写的
- 150-300字
- 描述环境/景色/体验感受
- 提到适合什么类型的人去（拍照/遛娃/约会等）
- 不要用绝对化用语
- 结尾给个总体推荐

请直接输出评价内容，不要加标题。"""
    }
}

# 爆款标题模板
TITLE_TEMPLATES = [
    "终于吃到了！{shop_name}{dish}",
    "{city}宝藏{category}，人均{price}吃到撑",
    "被朋友安利了{shop_name}，真的绝了",
    "藏在{area}的{category}，本地人都爱去",
    "{shop_name}拔草记录，{dish}必点！",
    "人均{price}的{category}，性价比超高",
    "周末探店{shop_name}，{dish}太惊艳了",
    "跟着点评来{shop_name}，没踩雷！",
]


class ContentGenerator:
    def __init__(self, api_key=None):
        key = api_key or DEEPSEEK_API_KEY
        if not key:
            raise ValueError("DEEPSEEK_API_KEY 未设置")
        self.client = OpenAI(api_key=key, base_url=DEEPSEEK_BASE_URL)

    def generate_review(self, shop_name, category="food", city="深圳",
                        dish_count=3, price="", area="", dish=""):
        """生成一条探店评价"""
        template = TEMPLATES.get(category, TEMPLATES["food"])

        prompt = template["prompt_template"].format(
            shop_name=shop_name,
            spot_name=shop_name,  # scenic 类型用同一个
            dish_count=dish_count,
            city=city,
            price=price or str(random.randint(30, 120)),
            area=area or "街角",
            dish=dish or "招牌菜",
        )

        try:
            response = self.client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": template["system"]},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.9,  # 高一点增加多样性
            )
            content = response.choices[0].message.content.strip()
            return {
                "success": True,
                "content": content,
                "shop_name": shop_name,
                "category": category,
                "char_count": len(content),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def generate_title(self, shop_name, category="food", city="深圳",
                       price="", area="", dish=""):
        """生成一个爆款标题"""
        title_template = random.choice(TITLE_TEMPLATES)
        category_map = {"food": "小店", "cafe": "咖啡店", "scenic": "打卡点"}
        return title_template.format(
            shop_name=shop_name,
            dish=dish or "招牌菜",
            city=city,
            price=price or str(random.randint(30, 120)),
            area=area or "附近",
            category=category_map.get(category, "店"),
        )

    def generate_batch(self, shops, count=10, **kwargs):
        """批量生成评价"""
        results = []
        for i in range(count):
            shop = random.choice(shops) if isinstance(shops, list) else shops
            shop_name = shop if isinstance(shop, str) else shop.get("name", "未知店铺")
            category = kwargs.get("category", "food")
            if isinstance(shop, dict):
                category = shop.get("category", category)

            result = self.generate_review(shop_name, category=category, **kwargs)
            if result["success"]:
                title = self.generate_title(shop_name, category=category, **kwargs)
                result["title"] = title
                results.append(result)

            # 避免请求太快
            time.sleep(0.5)

        return results


if __name__ == "__main__":
    # 测试
    gen = ContentGenerator()

    # 测试美食评价
    test_shops = ["老四川火锅", "茶百道(海岸城店)", "渔人码头海鲜", "瑞幸咖啡(科技园店)"]
    for shop in test_shops:
        category = "cafe" if any(k in shop for k in ["咖啡", "茶", "瑞幸"]) else "food"
        result = gen.generate_review(shop, category=category)
        title = gen.generate_title(shop, category=category)
        if result["success"]:
            print(f"\n{'='*50}")
            print(f"标题：{title}")
            print(f"店铺：{shop}")
            print(f"字数：{result['char_count']}")
            print(f"内容：{result['content'][:200]}...")
        else:
            print(f"生成失败: {result['error']}")
