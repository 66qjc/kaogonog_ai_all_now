import openai
import json
import logging
import time
from prompt_builder import build_prompt

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

# 设置API密钥（建议从环境变量读取）
openai.api_key = "你的API密钥"
# 如果使用DeepSeek，需要修改base_url
# openai.base_url = "https://api.deepseek.com/v1/"

def call_llm(prompt, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",  # 或 "deepseek-chat"
                messages=[
                    {"role": "system", "content": "你是一个严格的评分员，只会输出JSON。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,  # 确定性输出
                max_tokens=2000,
                response_format={ "type": "json_object" }  # 如果模型支持，可强制JSON
            )
            content = response.choices[0].message.content
            # 尝试解析JSON
            result = json.loads(content)
            return result
        except json.JSONDecodeError:
            logger.warning(
                "LLM scorer returned invalid JSON",
                extra={"event": "legacy_llm.invalid_json", "attempt": attempt + 1},
            )
            time.sleep(1)
        except Exception:
            logger.exception(
                "LLM scorer call failed",
                extra={"event": "legacy_llm.call_failed", "attempt": attempt + 1},
            )
            time.sleep(2)
    return None

def score_answer(answer, question_data):
    prompt = build_prompt(answer, question_data)
    result = call_llm(prompt)
    return result


def extract_json(text):
    # 尝试提取```json ... ``` 之间的内容
    import re
    pattern = r'```json\s*(\{.*?\})\s*```'
    match = re.search(pattern, text, re.DOTALL)
    if match:
        json_str = match.group(1)
    else:
        # 直接尝试解析整个文本
        json_str = text
    try:
        return json.loads(json_str)
    except:
        return None
