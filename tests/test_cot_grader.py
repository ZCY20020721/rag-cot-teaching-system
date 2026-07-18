"""cot_grader.py 单元测试 - 使用 mock 隔离 LLM API 调用"""
import json
import os
from unittest.mock import MagicMock, patch

import pytest

from cot_grader import (
    AnswerPoint,
    CoTGrader,
    GradingOutput,
    QuestionOutput,
    StepScore,
)


class TestPydanticModels:
    """数据模型验证测试"""

    def test_answer_point_valid(self):
        point = AnswerPoint(point="树的定义", tag="概念理解", max_score=5)
        assert point.point == "树的定义"
        assert point.max_score == 5

    def test_step_score_valid(self):
        score = StepScore(
            point_index=0,
            student_content="学生说树是一种数据结构",
            score=4,
            comment="基本正确",
        )
        assert score.score == 4
        assert 0 <= score.score <= 5

    def test_grading_output_valid(self):
        output = GradingOutput(
            step_scores=[
                StepScore(point_index=0, student_content="...", score=4, comment="好")
            ],
            logic_score=3,
            logic_comment="逻辑基本清晰",
            total_score=7.0,
            feedback="再想想第二点",
            weak_tags=["概念不清"],
        )
        assert output.total_score == 7.0
        assert len(output.step_scores) == 1


class TestCoTGraderInit:
    """初始化测试"""

    @patch.dict(
        "os.environ",
        {"DEEPSEEK_API_KEY": "test_key", "DEEPSEEK_BASE_URL": "https://test.api.com"},
    )
    def test_init_with_env_vars(self):
        grader = CoTGrader()
        assert grader.api_key == "test_key"
        assert grader.base_url == "https://test.api.com"

    def test_question_parser_type(self):
        grader = CoTGrader()
        assert grader.question_parser.pydantic_object == QuestionOutput

    def test_grading_parser_type(self):
        grader = CoTGrader()
        assert grader.grading_parser.pydantic_object == GradingOutput


class TestGenerateQuestion:
    """出题功能测试"""

    @patch("cot_grader.ChatOpenAI")
    def test_generate_success(self, mock_llm):
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "question": "请解释二叉树的三种遍历方式",
            "standard_answer_points": [
                {"point": "前序遍历", "tag": "算法", "max_score": 5},
                {"point": "中序遍历", "tag": "算法", "max_score": 5},
            ],
            "total_max_score": 10,
        })
        mock_llm.return_value.invoke.return_value = mock_response

        grader = CoTGrader()
        grader.llm = mock_llm.return_value
        result = grader.generate_question("教材内容：二叉树章节...")

        assert result is not None
        assert "遍历" in result["question"]
        assert len(result["standard_answer_points"]) == 2
        assert result["total_max_score"] == 10

    @patch("cot_grader.ChatOpenAI")
    def test_generate_json_in_markdown_block(self, mock_llm):
        mock_response = MagicMock()
        mock_response.content = (
            '```json\n'
            '{"question": "测试", "standard_answer_points": [], "total_max_score": 0}\n'
            '```'
        )
        mock_llm.return_value.invoke.return_value = mock_response

        grader = CoTGrader()
        grader.llm = mock_llm.return_value
        result = grader.generate_question("test context")

        assert result is not None
        assert result["question"] == "测试"

    @patch("cot_grader.ChatOpenAI")
    def test_generate_retry_on_json_error(self, mock_llm):
        bad_response = MagicMock()
        bad_response.content = "这不是 JSON，只是一段话..."
        good_response = MagicMock()
        good_response.content = json.dumps({
            "question": "重试成功",
            "standard_answer_points": [],
            "total_max_score": 5,
        })
        mock_llm.return_value.invoke.side_effect = [bad_response, good_response]

        grader = CoTGrader()
        grader.llm = mock_llm.return_value
        result = grader.generate_question("test context")

        assert result is not None
        assert result["question"] == "重试成功"
        assert mock_llm.return_value.invoke.call_count == 2

    @patch("cot_grader.ChatOpenAI")
    def test_generate_returns_none_on_double_failure(self, mock_llm):
        mock_llm.return_value.invoke.return_value.content = "非法内容{}{}{"

        grader = CoTGrader()
        grader.llm = mock_llm.return_value
        result = grader.generate_question("test context")

        assert result is None

    @patch("cot_grader.ChatOpenAI")
    def test_generate_with_code_block_without_json_tag(self, mock_llm):
        mock_response = MagicMock()
        mock_response.content = (
            '```\n'
            '{"question": "无标签代码块", "standard_answer_points": [], "total_max_score": 5}\n'
            '```'
        )
        mock_llm.return_value.invoke.return_value = mock_response

        grader = CoTGrader()
        grader.llm = mock_llm.return_value
        result = grader.generate_question("test")

        assert result is not None
        assert result["question"] == "无标签代码块"


class TestGradeAnswer:
    """批改功能测试"""

    @patch("cot_grader.ChatOpenAI")
    def test_grade_success(self, mock_llm):
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "step_scores": [
                {"point_index": 0, "student_content": "理解了定义", "score": 4, "comment": "好"}
            ],
            "logic_score": 3,
            "logic_comment": "基本合理",
            "total_score": 7.0,
            "feedback": "你对定义理解不错，请思考...",
            "weak_tags": ["概念理解"],
        })
        mock_llm.return_value.invoke.return_value = mock_response

        grader = CoTGrader()
        grader.llm = mock_llm.return_value
        result = grader.grade_answer(
            rag_context="教材内容...",
            standard_answer_points='[{"point": "定义", "tag": "概念", "max_score": 5}]',
            student_answer="二叉树是一种树形数据结构",
        )

        assert result is not None
        assert "total_score" in result
        assert "step_scores" in result
        assert result["logic_score"] == 3

    @patch("cot_grader.ChatOpenAI")
    def test_grade_with_markdown_json(self, mock_llm):
        json_str = json.dumps({
            "step_scores": [],
            "logic_score": 2,
            "logic_comment": "...",
            "total_score": 2,
            "feedback": "...",
            "weak_tags": [],
        })
        mock_response = MagicMock()
        mock_response.content = f"```json\n{json_str}\n```"
        mock_llm.return_value.invoke.return_value = mock_response

        grader = CoTGrader()
        grader.llm = mock_llm.return_value
        result = grader.grade_answer("ctx", "[]", "answer")

        assert result is not None

    @patch("cot_grader.ChatOpenAI")
    def test_grade_retry_and_fail(self, mock_llm):
        mock_llm.return_value.invoke.return_value.content = "not json"

        grader = CoTGrader()
        grader.llm = mock_llm.return_value
        result = grader.grade_answer("ctx", "[]", "answer")

        assert result is None

    @patch("cot_grader.ChatOpenAI")
    def test_grade_extracts_multiple_steps(self, mock_llm):
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "step_scores": [
                {"point_index": 0, "student_content": "要点1", "score": 5, "comment": "正确"},
                {"point_index": 1, "student_content": "要点2", "score": 2, "comment": "不完整"},
            ],
            "logic_score": 4,
            "logic_comment": "逻辑清晰",
            "total_score": 11.0,
            "feedback": "继续保持",
            "weak_tags": ["要点2"],
        })
        mock_llm.return_value.invoke.return_value = mock_response

        grader = CoTGrader()
        grader.llm = mock_llm.return_value
        result = grader.grade_answer("ctx", "[]", "answer")

        assert result is not None
        assert len(result["step_scores"]) == 2
        assert result["total_score"] == 11.0
        assert result["weak_tags"] == ["要点2"]


class TestErrorHandling:
    """异常处理测试"""

    @patch("cot_grader.ChatOpenAI")
    def test_generate_handles_exception(self, mock_llm):
        mock_llm.return_value.invoke.side_effect = Exception("API error")

        grader = CoTGrader()
        grader.llm = mock_llm.return_value
        result = grader.generate_question("test")

        assert result is None

    @patch("cot_grader.ChatOpenAI")
    def test_grade_handles_exception(self, mock_llm):
        mock_llm.return_value.invoke.side_effect = Exception("API error")

        grader = CoTGrader()
        grader.llm = mock_llm.return_value
        result = grader.grade_answer("ctx", "[]", "answer")

        assert result is None
