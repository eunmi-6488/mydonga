# 🌟 MyFavorite 시스템 구조도 및 가이드 문서

본 문서는 [MyFavorite.py](file:///c:/workAI/work8langchain/MyFavorite.py)의 **Pydantic 스키마 기반 콘텐츠 기획 및 상세페이지 자동 생성 엔진**의 전체 아키텍처와 데이터 흐름을 초보자도 한눈에 이해할 수 있도록 Mermaid 다이어그램과 함께 정리한 가이드입니다.

---

## 1. 전체 아키텍처 및 데이터 흐름도

```mermaid
flowchart TD
    subgraph INPUT ["1. 상품 정보 입력 (User Input)"]
        A1["📦 상품명 (Product Name)"]
        A2["🏷️ 카테고리 (Category)"]
        A3["🎯 타겟 고객 (Target Audience)"]
        A4["✨ 핵심 특장점 (Key Features)"]
        A5["🎨 톤앤매너 & 프로모션 (Tone & Promo)"]
    end

    subgraph ENGINE ["2. MyFavorite 생성 엔진 (LCEL Pipeline)"]
        B1["ChatPromptTemplate (AIDA & PAS 마케팅 공식)"]
        B2["ChatOpenAI (OpenRouter / gpt-4o-mini)"]
        B3["with_structured_output (ProductDetailPage)"]
        B1 --> B2 --> B3
    end

    subgraph PYDANTIC ["3. Pydantic 구조화 데이터 (ProductDetailPage)"]
        C1["🔥 후킹 헤드라인 & 서브카피"]
        C2["😫 문제점 공감 (Pain Points)"]
        C3["💡 해결책 요약 (Solution)"]
        C4["✨ 핵심 혜택 리스트 (FeatureItem)"]
        C5["🏆 신뢰 보증 (Social Proof)"]
        C6["❓ 자주 묻는 질문 (FAQItem)"]
        C7["🛒 행동 촉구 CTA 버튼 문구"]
    end

    subgraph OUTPUT ["4. 다중 포맷 파일 저장 (Output Exporters)"]
        D1["📄 마크다운 문서 (*.md)"]
        D2["💾 구조화 JSON 데이터 (*.json)"]
        D3["🌐 반응형 웹 상세페이지 (*.html)"]
    end

    INPUT --> ENGINE
    ENGINE --> PYDANTIC
    PYDANTIC --> OUTPUT
```

---

## 2. Pydantic 모델 및 클래스 다이어그램

```mermaid
classDiagram
    class FeatureItem {
        +str feature_title
        +str benefit_description
    }

    class FAQItem {
        +str question
        +str answer
    }

    class ProductDetailPage {
        +str product_name
        +str target_audience
        +str hook_headline
        +str sub_headline
        +List~str~ pain_points
        +str solution_summary
        +List~FeatureItem~ features_and_benefits
        +str social_proof
        +List~FAQItem~ faqs
        +str cta_button_text
        +str full_markdown_content
    }

    class MyFavorite {
        +str model_name
        +float temperature
        +str output_dir
        +ChatOpenAI llm
        +Runnable chain
        +create_detail_page() ProductDetailPage
        +save_markdown() str
        +save_json() str
        +save_html() str
    }

    ProductDetailPage *-- FeatureItem : contains
    ProductDetailPage *-- FAQItem : contains
    MyFavorite ..> ProductDetailPage : creates
```

---

## 3. 상세페이지 생성 시퀀스 다이어그램

```mermaid
sequenceDiagram
    autonumber
    actor User as 사용자 (User)
    participant MF as MyFavorite 엔진
    participant Prompt as 프롬프트 (AIDA & PAS)
    participant LLM as OpenRouter LLM
    participant Schema as Pydantic 검증기
    participant File as 파일 시스템 (data2/)

    User->>MF: create_detail_page(상품정보 전달)
    MF->>Prompt: 상품 정보 주입 및 프롬프트 생성
    Prompt->>LLM: 마케팅 프롬프트 전송
    LLM->>Schema: 구조화된 JSON 데이터 생성
    Schema-->>MF: ProductDetailPage 객체 반환
    
    par 3가지 포맷 동시 저장
        MF->>File: save_markdown() -> *.md 생성
        MF->>File: save_json() -> *.json 생성
        MF->>File: save_html() -> *.html 웹페이지 생성
    end

    MF-->>User: 제작 완료 및 저장 파일 경로 반환
```

---

## 4. 핵심 구성 요소 요약

| 구성 요소 | 설명 | 핵심 역할 |
| :--- | :--- | :--- |
| **`FeatureItem`** | 특징 및 고객 혜택 스키마 | 단순 스펙 나열이 아닌 고객 관점의 실질적 이점(Benefit) 구조화 |
| **`FAQItem`** | 자주 묻는 질문/답변 스키마 | 구매 전 고객의 의문점 및 망설임을 해소 |
| **`ProductDetailPage`** | 전체 상세페이지 데이터 모델 | 헤드라인, 공감 포인트, 솔루션, 혜택, 신뢰 증명, CTA 버튼을 하나의 완성형 모델로 관리 |
| **`MyFavorite`** | 상세페이지 제작 및 저장 엔진 | LangChain LCEL 파이프라인을 실행하고 `.md`, `.json`, `.html` 3종 파일로 즉시 변환/저장 |

---

## 5. 실행 및 활용 방법

```bash
# 콘솔에서 즉시 실행하여 상세페이지 3종 파일 생성
python MyFavorite.py
```

### 📁 생성되는 파일 위치 (`data2/`)
1. **마크다운 상세페이지**: `data2/jeju_hallabong_detail.md`
2. **JSON 데이터**: `data2/jeju_hallabong_detail.json`
3. **웹 브라우저용 반응형 HTML**: `data2/jeju_hallabong_detail.html`
