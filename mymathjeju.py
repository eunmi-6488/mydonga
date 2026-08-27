import os
import sys
import json
import math
from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_core.tools import tool

# ── 0. 환경 설정 (Windows 콘솔 UTF-8 & 환경변수 로드) ─────────────────
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

# .env 환경 변수 로드 및 LangSmith 경고 비활성화
load_dotenv()
os.environ["LANGSMITH_TRACING"] = "false"

# OpenRouter API 키 확인
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    print("⚠️ 경고: .env 파일에 OPENROUTER_API_KEY 가 설정되어 있지 않습니다.")


# =========================================================
# ── AgentExecutor & create_tool_calling_agent 안전 임포트 ──
# =========================================================
CLASSIC_AGENT_AVAILABLE = False
try:
    from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
    CLASSIC_AGENT_AVAILABLE = True
except ImportError:
    try:
        from langchain.agents import AgentExecutor, create_tool_calling_agent
        CLASSIC_AGENT_AVAILABLE = True
    except ImportError:
        CLASSIC_AGENT_AVAILABLE = False
        AgentExecutor = None
        create_tool_calling_agent = None


# =========================================================
# 0. data2/jejumath.json 파일 저장 함수
# =========================================================
DATA_DIR = "data2"
JSON_FILE_PATH = os.path.join(DATA_DIR, "jejumath.json")


def save_to_jejumath_json(user_query: str, ai_response: str, tools_executed: Optional[List[Dict[str, Any]]] = None) -> str:
    """
    처리 결과 내용(질문, 답변, 도구 실행 정보, 타임스탬프)을 data2/jejumath.json 파일에 저장합니다.
    """
    os.makedirs(DATA_DIR, exist_ok=True)

    history_list = []
    if os.path.exists(JSON_FILE_PATH):
        try:
            with open(JSON_FILE_PATH, "r", encoding="utf-8") as f:
                history_list = json.load(f)
                if not isinstance(history_list, list):
                    history_list = [history_list]
        except Exception:
            history_list = []

    record = {
        "id": len(history_list) + 1,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "user_query": user_query,
        "ai_response": ai_response,
        "tools_executed": tools_executed or []
    }

    history_list.append(record)
    with open(JSON_FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(history_list, f, ensure_ascii=False, indent=2)

    return JSON_FILE_PATH


# =========================================================
# 1. 수학 내장함수 맵핑 & Pydantic BaseModel 스키마 정의
# =========================================================

# 파이썬 내장 함수 및 math 모듈 함수 참조 딕셔너리
MATH_BUILTIN_FUNCS = {
    'abs': abs,             # 절댓값: abs(num1) 또는 abs(num1 - num2)
    'round': round,         # 반올림: round(num1, int(num2))
    'sqrt': math.sqrt,      # 제곱근(루트): math.sqrt(num1)
    'pow': math.pow,        # 거듭제곱: math.pow(num1, num2)
    'add': lambda a, b: a + b,
    'subtract': lambda a, b: a - b,
    'multiply': lambda a, b: a * b,
    'divide': lambda a, b: a / b if b != 0 else "0으로 나눌 수 없습니다."
}


class MathQuery(BaseModel):
    """
    수학 연산 및 내장함수(abs, round, sqrt, pow 등)를 적용하기 위한 입력 스키마
    """
    operation: Literal['add', 'subtract', 'multiply', 'divide', 'abs', 'round', 'sqrt', 'pow'] = Field(
        ...,
        description=(
            "수행할 수학 연산 또는 내장함수 종류:\n"
            "- 'abs': 절댓값 계산 (abs(num1 - num2) 또는 abs(num1))\n"
            "- 'round': 반올림 (round(num1, 자릿수 num2))\n"
            "- 'sqrt': 제곱근/루트 (math.sqrt(num1))\n"
            "- 'pow': 거듭제곱 (math.pow(num1, num2))\n"
            "- 'add', 'subtract', 'multiply', 'divide': 기본 사칙연산"
        )
    )
    num1: float = Field(..., description="첫 번째 숫자 (피연산자 A, sqrt/abs/round 대상)")
    num2: Optional[float] = Field(default=0.0, description="두 번째 숫자 (피연산자 B, pow 지수, round 자릿수, 차이 연산 시 사용)")

    def calculate(self) -> str:
        """내장함수 딕셔너리를 참조하여 연산을 수행하고 결과를 반환합니다."""
        op = self.operation

        # 1) 절댓값 (abs)
        if op == 'abs':
            func = MATH_BUILTIN_FUNCS['abs']
            if self.num2 != 0:
                diff = self.num1 - self.num2
                res = func(diff)
                return f"[내장함수 abs 연산] abs({self.num1} - {self.num2}) = abs({diff}) = {res}"
            else:
                res = func(self.num1)
                return f"[내장함수 abs 연산] abs({self.num1}) = {res}"

        # 2) 반올림 (round)
        elif op == 'round':
            func = MATH_BUILTIN_FUNCS['round']
            decimals = int(self.num2) if self.num2 != 0 else None
            if decimals is not None:
                res = func(self.num1, decimals)
                return f"[내장함수 round 연산] round({self.num1}, {decimals}) = {res}"
            else:
                res = func(self.num1)
                return f"[내장함수 round 연산] round({self.num1}) = {res}"

        # 3) 제곱근 / 루트 (math.sqrt)
        elif op == 'sqrt':
            if self.num1 < 0:
                return "[오류] 음수의 제곱근은 실수 범위에서 계산할 수 없습니다."
            func = MATH_BUILTIN_FUNCS['sqrt']
            res = func(self.num1)
            return f"[내장함수 math.sqrt 연산] math.sqrt({self.num1}) = {res}"

        # 4) 거듭제곱 (math.pow)
        elif op == 'pow':
            func = MATH_BUILTIN_FUNCS['pow']
            res = func(self.num1, self.num2)
            return f"[내장함수 math.pow 연산] math.pow({self.num1}, {self.num2}) = {self.num1} ^ {self.num2} = {res}"

        # 5) 사칙연산 (add, subtract, multiply, divide)
        elif op in ['add', 'subtract', 'multiply', 'divide']:
            func = MATH_BUILTIN_FUNCS[op]
            res = func(self.num1, self.num2)
            symbols = {'add': '+', 'subtract': '-', 'multiply': '×', 'divide': '÷'}
            return f"[사칙연산 {op}] {self.num1} {symbols[op]} {self.num2} = {res}"

        else:
            return f"[오류] 지원하지 않는 연산 타입입니다: {op}"


class JejuQuery(BaseModel):
    """제주도 정보(날씨, 관광지, 특산물/맛집, 여행팁) 조회를 위한 입력 스키마"""
    category: Literal['weather', 'tourist_spot', 'food', 'tip'] = Field(
        ..., 
        description="조회할 제주 정보 카테고리 ('weather': 날씨, 'tourist_spot': 관광지, 'food': 음식/특산물, 'tip': 여행팁)"
    )
    location: str = Field(default="제주도 전체", description="조회할 제주 세부 지역 (예: 서귀포, 애월, 성산, 제주시)")
    date: Optional[str] = Field(default="today", description="조회할 날짜 (예: 오늘, 내일, YYYY-MM-DD)")

    def get_jeju_info(self) -> str:
        """제주 요청 카테고리에 맞는 요약 정보를 반환하는 메서드"""
        if self.category == "weather":
            return f"🌤️ [{self.location}] {self.date} 날씨: 맑음, 기온: 22°C (여행하기 좋은 날씨입니다)"
        elif self.category == "tourist_spot":
            return f"🌋 [{self.location}] 대표 추천 관광지: 성산일출봉, 섭지코지, 한라산 국립공원, 곽지해수욕장"
        elif self.category == "food":
            return f"🍊 [{self.location}] 추천 특산물 및 맛집: 흑돼지 구이, 제주 감귤/한라봉, 고기국수, 갈치조림"
        elif self.category == "tip":
            return f"💡 [{self.location}] 제주 여행 팁: 렌터카 사전 예약 필수, 해안도로 드라이브 추천, 일몰 시간 확인"
        else:
            return f"🏝️ [{self.location}] 제주도 가이드 정보 제공 완료"


# =========================================================
# 2. @tool 데코레이터 적용 (args_schema 인자 활용)
# =========================================================
@tool(args_schema=MathQuery)
def math_tool(operation: str, num1: float, num2: float = 0.0) -> str:
    """
    수학 연산 및 내장함수(abs, round, math.sqrt, math.pow, add, subtract, multiply, divide)를 수행하는 도구입니다.
    """
    query = MathQuery(operation=operation, num1=num1, num2=num2)
    return query.calculate()


@tool(args_schema=JejuQuery)
def jeju_tool(category: str, location: str = "제주도 전체", date: str = "today") -> str:
    """
    제주도의 날씨, 관광지, 특산물/맛집, 여행 팁 정보를 제공하는 전용 툴입니다.
    """
    query = JejuQuery(category=category, location=location, date=date)
    return query.get_jeju_info()


tools = [math_tool, jeju_tool]
tools_dict = {t.name: t for t in tools}


# =========================================================
# 3. 내장 CustomAgentExecutor (호환용 엔진)
# =========================================================
class CustomAgentExecutor:
    """
    AgentExecutor 아키텍처 구현체
    """
    def __init__(self, model: ChatOpenAI, tools: list, system_prompt: str):
        self.model = model
        self.tools = tools
        self.tool_map = {t.name: t for t in tools}
        self.model_with_tools = model.bind_tools(tools)
        self.system_prompt = system_prompt

    def invoke(self, inputs: dict) -> dict:
        user_input = inputs.get("input") or inputs.get("question", "")
        chat_history = inputs.get("chat_history", [])

        messages = [SystemMessage(content=self.system_prompt)]
        messages.extend(chat_history)
        messages.append(HumanMessage(content=user_input))

        ai_response = self.model_with_tools.invoke(messages)
        intermediate_steps = []

        if hasattr(ai_response, "tool_calls") and ai_response.tool_calls:
            tool_messages = []
            for tool_call in ai_response.tool_calls:
                t_name = tool_call["name"]
                t_args = tool_call["args"]
                t_id = tool_call["id"]

                target_tool = self.tool_map.get(t_name)
                t_output = target_tool.invoke(t_args) if target_tool else f"[오류] 없는 도구: {t_name}"

                intermediate_steps.append({
                    "tool": t_name,
                    "args": t_args,
                    "output": str(t_output)
                })
                tool_messages.append(ToolMessage(content=str(t_output), tool_call_id=t_id))

            final_context = messages + [ai_response] + tool_messages
            final_ai_msg = self.model.invoke(final_context)
            final_output = final_ai_msg.content
        else:
            final_output = ai_response.content

        return {
            "input": user_input,
            "output": final_output,
            "intermediate_steps": intermediate_steps
        }


# =========================================================
# 4. AgentExecutor 인스턴스 빌더 함수
# =========================================================
def build_agent_executor(temperature: float = 0.0):
    model = ChatOpenAI(
        model="openai/gpt-4o-mini",
        openai_api_key=OPENROUTER_API_KEY,
        base_url="https://openrouter.ai/api/v1",
        temperature=temperature
    )
    system_prompt = (
        "당신은 제주도 여행 정보(날씨, 관광지, 특산물, 팁) 및 수학 내장함수(abs, round, sqrt, pow 등) 도구를 활용하여 "
        "사용자의 질문에 친절하고 명확하게 한국어로 답변하는 전문 AI 어시스턴트입니다."
    )

    if CLASSIC_AGENT_AVAILABLE and create_tool_calling_agent is not None and AgentExecutor is not None:
        try:
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                MessagesPlaceholder(variable_name="chat_history"),
                ("user", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ])
            agent = create_tool_calling_agent(model, tools, prompt)
            return AgentExecutor(
                agent=agent,
                tools=tools,
                verbose=False,
                return_intermediate_steps=True,
                handle_parsing_errors=True
            )
        except Exception:
            pass

    return CustomAgentExecutor(model=model, tools=tools, system_prompt=system_prompt)


# =========================================================
# 5. 메인 콘솔 실행 루프 (CLI Mode)
# =========================================================
def run_query(agent_executor, user_query: str, chat_history: list) -> str:
    """질문을 실행하고 결과를 출력 및 JSON 저장합니다."""
    print(f"\n💬 [질문 입력]: \"{user_query}\"")
    print("⏳ AgentExecutor가 분석 및 내장함수/도구 호출을 수행 중입니다...")

    result = agent_executor.invoke({
        "input": user_query,
        "chat_history": chat_history
    })

    output_text = result["output"]
    raw_steps = result.get("intermediate_steps", [])

    # 도구 호출 단계 파싱
    tool_logs = []
    for step in raw_steps:
        if isinstance(step, tuple) and len(step) == 2:
            action, tool_output = step
            tool_logs.append({
                "tool": getattr(action, "tool", str(action)),
                "args": getattr(action, "tool_input", {}),
                "output": str(tool_output)
            })
        elif isinstance(step, dict):
            tool_logs.append(step)

    # 콘솔에 도구 실행 로그 출력
    if tool_logs:
        print("\n⚡ [도구 실행 로그 (Tool Calls)]")
        for idx, step in enumerate(tool_logs, 1):
            print(f"  {idx}. 도구: {step['tool']}")
            print(f"     인자: {step['args']}")
            print(f"     결과: {step['output']}")

    print("\n💡 [AI 최종 응답]:")
    print(output_text)

    # data2/jejumath.json 파일에 저장
    saved_path = save_to_jejumath_json(
        user_query=user_query,
        ai_response=output_text,
        tools_executed=tool_logs
    )
    print(f"💾 [저장 완료] 결과가 '{saved_path}' 파일에 저장되었습니다.\n" + "-" * 60)

    # 히스토리 업데이트
    chat_history.append(HumanMessage(content=user_query))
    chat_history.append(AIMessage(content=output_text))

    return output_text


def main():
    print("=" * 65)
    print(" 🍊 [콘솔 모드] 제주 여행 & 수학 내장함수 AgentExecutor AI")
    print("    ('abs': abs, 'round': round, 'sqrt': math.sqrt, 'pow': math.pow)")
    print("    (data2/jejumath.json 자동 누적 저장)")
    print("=" * 65)

    agent_executor = build_agent_executor()
    chat_history = []

    # 1. 수학 내장함수(abs, round, sqrt, pow) 및 제주 정보 자동 테스트
    sample_queries = [
        "abs(2 - 17) 계산해주고 144의 제곱근(sqrt)을 구해줘",
        "3.141592를 소수점 둘째자리까지 반올림(round)하고, 2의 10승(pow)을 계산해줘",
        "서귀포 특산물 맛집 추천과 함께 오늘 제주도 날씨 알려줘"
    ]

    print("\n🚀 [내장함수 샘플 쿼리 자동 실행 테스트]")
    for query in sample_queries:
        run_query(agent_executor, query, chat_history)

    print("\n" + "=" * 65)
    print("✨ 샘플 질의 완료! 이제 직접 질문을 입력해보세요. (종료: 'q' 또는 'exit')")
    print("=" * 65)

    # 2. 대화형 인터랙티브 콘솔 루프
    while True:
        try:
            user_input = input("\n👉 질문 입력: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ["q", "exit", "quit", "종료"]:
                print("👋 이용해주셔서 감사합니다. 프로그램을 종료합니다.")
                break

            run_query(agent_executor, user_input, chat_history)

        except KeyboardInterrupt:
            print("\n👋 프로그램을 종료합니다.")
            break
        except Exception as e:
            print(f"❌ 오류 발생: {e}")


if __name__ == "__main__":
    main()
