import os
import sys

# Windows 콘솔 UTF-8 인코딩 설정
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass


SYSTEM_FLOWCHART_MERMAID = """```mermaid
flowchart TD
    subgraph CLI ["💻 사용자 인터페이스 (Console CLI)"]
        A["👤 사용자 (User)<br/>자연어 질의 입력"] --> B["⚙️ run_query()<br/>(질의 전달 및 대화 히스토리 관리)"]
    end

    subgraph AGENT ["🤖 AgentExecutor 엔진 (AI Reasoning)"]
        B --> C["📝 System Prompt + History + User Input"]
        C --> D["🧠 ChatOpenAI (OpenRouter / gpt-4o-mini)<br/>bind_tools([math_tool, jeju_tool])"]
        D --> E{"🔍 LLM 판단<br/>도구(Tool) 호출 필요?"}
    end

    subgraph TOOLS ["🛠️ Pydantic 기반 전용 도구 (Tools)"]
        E -- "수학/내장함수 질문" --> F1["🧮 math_tool<br/>args_schema: MathQuery"]
        E -- "제주도 여행/날씨 질문" --> F2["🌴 jeju_tool<br/>args_schema: JejuQuery"]
        
        F1 --> G1["MathQuery.calculate()<br/>(abs, round, sqrt, pow, 사칙연산)"]
        F2 --> G2["JejuQuery.get_jeju_info()<br/>(날씨, 관광지, 맛집, 여행팁)"]
    end

    subgraph OUTPUT ["💾 응답 반환 및 JSON 영구 저장"]
        E -- "일반 대화" --> H["AI 텍스트 답변 생성"]
        G1 --> I["⚡ ToolMessage 결과 피드백"]
        G2 --> I
        I --> D
        H --> J["💡 콘솔 최종 응답 출력"]
        J --> K["📂 save_to_jejumath_json()<br/>data2/jejumath.json 누적 저장"]
    end

    style CLI fill:#e3f2fd,stroke:#1565c0,stroke-width:2px
    style AGENT fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    style TOOLS fill:#fff3e0,stroke:#e65100,stroke-width:2px
    style OUTPUT fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px
```"""

SEQUENCE_DIAGRAM_MERMAID = """```mermaid
sequenceDiagram
    autonumber
    actor User as 👤 사용자
    participant App as 💻 mymathjeju.py (CLI)
    participant Agent as 🤖 AgentExecutor
    participant LLM as 🧠 OpenRouter (gpt-4o-mini)
    participant Tool as 🛠️ Math / Jeju Tool
    participant Storage as 💾 JSON 저장소 (data2/)

    User->>App: 질의 입력 (예: "abs(2 - 17) 계산하고 서귀포 맛집 알려줘")
    App->>Agent: run_query(user_query, chat_history)
    Agent->>LLM: 프롬프트 + 히스토리 + 도구 바인딩 정보 전달
    
    rect rgb(255, 248, 225)
        note over LLM,Tool: 1차 Tool Call (수학 연산)
        LLM-->>Agent: Tool Call 요청 (math_tool, operation="abs", num1=2, num2=17)
        Agent->>Tool: math_tool.invoke(...)
        Tool-->>Agent: "[내장함수 abs 연산] abs(2.0 - 17.0) = 15.0"
        Agent->>LLM: ToolMessage 결과 전달
    end

    rect rgb(232, 245, 233)
        note over LLM,Tool: 2차 Tool Call (제주 맛집 조회)
        LLM-->>Agent: Tool Call 요청 (jeju_tool, category="food", location="서귀포")
        Agent->>Tool: jeju_tool.invoke(...)
        Tool-->>Agent: "🍊 [서귀포] 추천 특산물 및 맛집: 흑돼지 구이, 감귤, 갈치조림"
        Agent->>LLM: ToolMessage 결과 전달
    end

    LLM-->>Agent: 최종 종합 답변 텍스트 생성
    Agent->>Storage: save_to_jejumath_json() 호출 -> jejumath.json 누적 저장
    Agent-->>App: 최종 결과 문자열 및 실행 로그 반환
    App-->>User: 콘솔 화면에 답변 출력
```"""


def display_structure():
    """mymathjeju.py의 파이프라인 구조와 Mermaid 다이어그램을 출력합니다."""
    print("=" * 65)
    print(" 🍊 mymathjeju.py 시스템 아키텍처 및 Mermaid 다이어그램")
    print("=" * 65)
    print("\n[1] 시스템 구조 Flowchart Mermaid:\n")
    print(SYSTEM_FLOWCHART_MERMAID)
    print("\n" + "-" * 65)
    print("\n[2] AgentExecutor 실행 시퀀스 다이어그램 Mermaid:\n")
    print(SEQUENCE_DIAGRAM_MERMAID)
    print("\n" + "=" * 65)
    print("💡 상세 설명 문서는 'mymathjeju_structure.md' 파일을 참조하세요.")


if __name__ == "__main__":
    display_structure()
