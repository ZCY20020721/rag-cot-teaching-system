"""
CoT 智能批改引擎 - 基于思维链的分步评分
支持结构化 Prompt、强制 JSON 解析、自动重试
"""

import json
import os
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

from typing import List

from langchain_core.output_parsers import PydanticOutputParser
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from prompts import COT_GRADING_PROMPT, QUESTION_GENERATION_PROMPT


# ============================================================
# Pydantic 数据模型 - 强制 JSON 格式校验
# ============================================================
class AnswerPoint(BaseModel):
    point: str = Field(description="得分点描述")
    tag: str = Field(description="知识点标签")
    max_score: float = Field(description="该得分点满分")


class QuestionOutput(BaseModel):
    question: str = Field(description="生成的题目")
    standard_answer_points: List[AnswerPoint] = Field(description="标准答案要点列表")
    total_max_score: float = Field(description="总分")


class StepScore(BaseModel):
    point_index: int = Field(description="得分点序号")
    student_content: str = Field(description="学生答案中相关表述")
    score: float = Field(description="该得分点得分")
    comment: str = Field(description="简短评语")


class GradingOutput(BaseModel):
    step_scores: List[StepScore] = Field(description="各得分点评分")
    logic_score: float = Field(description="逻辑得分 0-5")
    logic_comment: str = Field(description="逻辑评估说明")
    total_score: float = Field(description="总分")
    feedback: str = Field(description="苏格拉底式引导反馈")
    weak_tags: List[str] = Field(description="薄弱知识点标签列表")


class CoTGrader:
    """基于 CoT 的智能批改引擎"""

    def __init__(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

        self.llm = ChatOpenAI(
            model="deepseek-chat",
            api_key=self.api_key,
            base_url=self.base_url,
            temperature=0.1,
            max_tokens=4096,
        )

        self.question_parser = PydanticOutputParser(pydantic_object=QuestionOutput)
        self.grading_parser = PydanticOutputParser(pydantic_object=GradingOutput)

    def generate_question(self, rag_context: str, requirement: str = None) -> Optional[dict]:
        """基于教材内容生成考题和标准答案"""
        req_text = requirement if requirement and requirement.strip() else ""
        if req_text:
            req_text = f"\n\n【额外出题要求】\n{req_text}\n请严格按照以上要求设计题目。"
        prompt = QUESTION_GENERATION_PROMPT.format(rag_context=rag_context + req_text)

        try:
            response = self.llm.invoke(prompt)
            content = response.content.strip()

            # 尝试提取 JSON（处理可能的 markdown 代码块包裹）
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            result = json.loads(content)
            return result
        except json.JSONDecodeError:
            # 重试：要求严格遵守格式
            retry_prompt = (
                prompt + "\n\n【重要提醒】请只输出合法的 JSON，不要包裹在 markdown 代码块中。"
            )
            try:
                response = self.llm.invoke(retry_prompt)
                content = response.content.strip()
                if "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                    if content.startswith("json"):
                        content = content[4:].strip()
                return json.loads(content)
            except Exception:
                return None
        except Exception:
            return None

    def grade_answer(
        self, rag_context: str, standard_answer_points: str, student_answer: str
    ) -> Optional[dict]:
        """使用 CoT 思维链对学生答案进行分步批改"""
        prompt = COT_GRADING_PROMPT.format(
            rag_context=rag_context,
            standard_answer_points=standard_answer_points,
            student_answer=student_answer,
            max_per_point=5,
        )

        try:
            response = self.llm.invoke(prompt)
            content = response.content.strip()

            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            result = json.loads(content)
            return result
        except json.JSONDecodeError:
            retry_prompt = (
                prompt + "\n\n【重要提醒】请只输出合法的 JSON，不要包裹在 markdown 代码块中。"
            )
            try:
                response = self.llm.invoke(retry_prompt)
                content = response.content.strip()
                if "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                    if content.startswith("json"):
                        content = content[4:].strip()
                return json.loads(content)
            except Exception:
                return None
        except Exception:
            return None
