# 🍊 mymathjeju.py 파이프라인 구조도 및 가이드 문서 (AgentExecutor & Tools)

본 문서는 [mymathjeju.py](file:///c:/workAI/work9langchain/mymathjeju.py)의 **수학 내장함수 연산 및 제주 여행 정보 제공 AgentExecutor AI 시스템**의 전체 아키텍처와 데이터 흐름을 초보자도 한눈에 이해할 수 있도록 Mermaid 다이어그램과 함께 정리한 가이드입니다.

---

## 💡 1. 한눈에 보는 전체 시스템 구조도 (System Architecture)

`mymathjeju.py`는 **콘솔 대화형 인터페이스(CLI)**, **AgentExecutor 실행 엔진**, **Pydantic 스키마 기반 Tool**, **OpenRouter API(gpt-4o-mini)**, 그리고 **JSON 데이터 저장소**가 유기적으로 연동되어 작동합니다.

```mermaid
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
```

---

## 🧩 2. 핵심 구성 요소별 역할 (Core Components)

### 1️⃣ Pydantic 입력 스키마 (`MathQuery`, `JejuQuery`)
* **`MathQuery`**:
  * `operation`: 수행할 연산 종류 (`abs`, `round`, `sqrt`, `pow`, `add`, `subtract`, `multiply`, `divide`)
  * `num1`, `num2`: 연산 대상 숫자값 검증 및 파이썬 내장함수(`math` 모듈) 기반 연산 실행
* **`JejuQuery`**:
  * `category`: 정보 분류 (`weather`: 날씨, `tourist_spot`: 관광지, `food`: 특산물/맛집, `tip`: 여행팁)
  * `location`: 세부 지역(서귀포, 애월, 제주시 등), `date`: 날짜

### 2️⃣ LangChain Tool (`@tool(args_schema=...)`)
* **`math_tool`**: `MathQuery` 스키마를 바탕으로 AI가 정확한 파라미터로 수학 함수를 호출하도록 가이드
* **`jeju_tool`**: `JejuQuery` 스키마를 기반으로 카테고리별 맞춤 제주 여행 정보 추출

### 3️⃣ CustomAgentExecutor (호환용 에이전트 엔진)
* LangChain 최신 버전 및 구버전 환경 모두에서 안정적으로 작동하도록 구현된 독립 실행 엔진
* LLM의 `tool_calls` 요청을 감지하여 알맞은 도구를 실행하고, 그 결과를 다시 모델에 전달하여 최종 답변 도출

### 4️⃣ 데이터 영구 저장소 (`save_to_jejumath_json`)
* 질의 내용, AI 응답, 실행된 도구 로그(Tool Calls), 타임스탬프를 [data2/jejumath.json](file:///c:/workAI/work9langchain/data2/jejumath.json) 파일에 JSON 형태로 누적 기록

---

## 🔄 3. 데이터 흐름 순서도 (Sequence Diagram)

```mermaid
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
```

---

## 📊 4. Pydantic 모델 및 클래스 관계도 (Class Diagram)

```mermaid
classDiagram
    class MathQuery {
        +Literal operation
        +float num1
        +Optional~float~ num2
        +calculate() str
    }

    class JejuQuery {
        +Literal category
        +str location
        +Optional~str~ date
        +get_jeju_info() str
    }

    class CustomAgentExecutor {
        +ChatOpenAI model
        +list tools
        +dict tool_map
        +str system_prompt
        +invoke(dict inputs) dict
    }

    CustomAgentExecutor ..> MathQuery : uses via math_tool
    CustomAgentExecutor ..> JejuQuery : uses via jeju_tool
```

---

## 🚀 5. 실행 방법

가상환경(`.venv`)이 활성화된 터미널에서 다음 명령어를 실행합니다:

```powershell
# mymathjeju.py 콘솔 실행
python mymathjeju.py
```

### 📁 실행 결과 저장 위치
- **JSON 로그 파일**: [data2/jejumath.json](file:///c:/workAI/work9langchain/data2/jejumath.json)
