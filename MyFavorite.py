import os
import sys
import json
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# LangChain 최신 패키지 임포트
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# ==============================================================================
# [1단계] 환경 설정 및 API 키 로드
# ==============================================================================

# Windows 콘솔 환경에서 한글 깨짐 방지를 위한 UTF-8 출력 재설정
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

# .env 파일에서 환경 변수(API 키 등) 로드
load_dotenv()

# LangSmith 추적 비활성화 (불필요한 HTTP 403 경고 로그 방지)
os.environ["LANGSMITH_TRACING"] = "false"

# API 키 가져오기 (OpenRouter 우선 탐지, 없으면 OpenAI 사용)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


# ==============================================================================
# [2단계] Pydantic 기반의 상세페이지 데이터 구조(스키마) 정의
# ==============================================================================

class FeatureItem(BaseModel):
    """
    [핵심 혜택 스키마]
    단순한 기술 스펙 나열이 아닌, 고객이 실제로 얻게 되는 가치와 혜택을 정의합니다.
    """
    feature_title: str = Field(
        description="특징 제목 (예: 대낮에도 선명한 3,800 안시루멘)"
    )
    benefit_description: str = Field(
        description="고객 관점의 실질적인 혜택 설명 (예: 암막 커튼 없이 형광등 아래에서도 선명하게 영화를 감상할 수 있습니다.)"
    )


class FAQItem(BaseModel):
    """
    [FAQ 스키마]
    고객이 구매 직전 망설이는 핵심 고민과 질문을 사전에 해결해 주는 Q&A 구조입니다.
    """
    question: str = Field(description="고객이 궁금해할 만한 핵심 질문")
    answer: str = Field(description="명쾌하고 신뢰를 주는 전문가의 답변")


class ProductDetailPage(BaseModel):
    """
    [고전환율(High-Conversion) 상세페이지 전체 모델]
    AIDA(주의->흥미->욕구->행동) 및 PAS(문제->자극->해결) 마케팅 공식을 적용한 완성형 데이터 모델입니다.
    """
    product_name: str = Field(description="상품의 공식 명칭")
    target_audience: str = Field(description="구체적인 타겟 고객 페르소나 정의")
    
    # 1. 시선을 끄는 카피라이팅 영역 (Hooking)
    hook_headline: str = Field(description="첫 3초 만에 시선을 사로잡는 강력한 메인 후킹 헤드라인")
    sub_headline: str = Field(description="제품의 매력과 가치를 극대화하는 매혹적인 서브 카피")
    pain_points: List[str] = Field(description="고객이 겪고 있는 불편함과 고민에 대한 공감 포인트 (3~4개)")
    
    # 2. 문제 해결 및 핵심 가치 제안 영역 (Solution & Features)
    solution_summary: str = Field(description="우리 제품이 고객의 문제를 어떻게 완벽히 해결하는지에 대한 요약 설명")
    features_and_benefits: List[FeatureItem] = Field(description="차별화된 핵심 강점 및 고객 혜택 리스트 (3~5개)")
    social_proof: str = Field(description="신뢰도를 극대화하는 증거 (누적 판매량, 만족도, 안전 인증, A/S 보증 등)")
    
    # 3. 구매 전환 유도 영역 (Conversion & CTA)
    faqs: List[FAQItem] = Field(description="구매 전 의구심을 완전히 해소하는 핵심 FAQ 리스트 (3개 내외)")
    cta_button_text: str = Field(description="즉시 구매 및 행동을 유도하는 강력한 CTA(Call To Action) 버튼 문구")
    
    # 4. 전체 마크다운 본문
    full_markdown_content: str = Field(description="아이콘과 섹션이 정돈된 완성형 마크다운 상세페이지 본문")


# ==============================================================================
# [3단계] 콘텐츠 & 프리미엄 상세페이지 자동 제작 클래스 (MyFavorite)
# ==============================================================================

class MyFavorite:
    """
    🎯 [MyFavorite] 콘텐츠 & 프리미엄 상세페이지 자동 제작 시스템
    
    [주요 기능]
    1. 상품 정보 딕셔너리 입력 -> LCEL 체인을 통한 전문 카피라이팅 자동 생성
    2. Pydantic 구조화된 데이터 파싱을 통한 완벽한 데이터 검증
    3. 마크다운(.md), 웹 반응형 페이지(.html), 데이터(.json) 파일 3종 동시 자동 저장
    """

    def __init__(
        self,
        model_name: str = "openai/gpt-4o-mini",
        temperature: float = 0.7,
        output_dir: str = "data2"
    ):
        """
        MyFavorite 생성 엔진 초기화
        - model_name: 사용할 LLM 모델 (기본값: openai/gpt-4o-mini)
        - temperature: 창의성 조절 파라미터 (0.7: 매력적이고 자연스러운 마케팅 문구 생성에 최적화)
        - output_dir: 결과물이 저장될 폴더 경로
        """
        self.model_name = model_name
        self.temperature = temperature
        self.output_dir = output_dir

        # 결과 저장용 폴더가 없으면 자동 생성
        os.makedirs(self.output_dir, exist_ok=True)

        # 1. LLM 클라이언트 초기화 (OpenRouter 또는 OpenAI API 연결)
        if OPENROUTER_API_KEY:
            self.llm = ChatOpenAI(
                model=self.model_name,
                api_key=OPENROUTER_API_KEY,
                base_url="https://openrouter.ai/api/v1",
                temperature=self.temperature
            )
        elif OPENAI_API_KEY:
            self.llm = ChatOpenAI(
                model="gpt-4o-mini",
                api_key=OPENAI_API_KEY,
                temperature=self.temperature
            )
        else:
            raise ValueError("❌ .env 파일에 OPENROUTER_API_KEY 또는 OPENAI_API_KEY가 설정되어 있어야 합니다.")

        # 2. Pydantic 모델과 연결된 구조화된 출력(Structured Output) 전용 모델 생성
        self.structured_llm = self.llm.with_structured_output(ProductDetailPage)

        # 3. 10년 차 마케팅 디렉터의 관점을 담은 시스템 프롬프트 템플릿 구성
        self.prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "당신은 10년 차 이상의 최고급 이커머스 수석 마케팅 디렉터이자 커머스 상세페이지 전문 카피라이터입니다.\n"
                "고객의 심리를 자극하는 AIDA(Attention, Interest, Desire, Action) 모델과 PAS(Problem, Agitation, Solution) 공식을 철저히 적용하여,\n"
                "고객이 읽자마자 '이건 나를 위한 상품이다!'라고 느끼고 즉시 결제 버튼을 누르고 싶어지는 고전환율 상세페이지를 작성해 주세요.\n"
                "모든 항목은 Pydantic 스키마 형식에 맞추어 전문적이고 매력적인 한국어로 작성해 주세요."
            ),
            (
                "user",
                "다음 입력된 상품 정보를 바탕으로 최고급 상세페이지 콘텐츠를 완성해 주세요:\n\n"
                "📦 상품명: {product_name}\n"
                "🏷️ 카테고리: {category}\n"
                "🎯 타겟 고객: {target_audience}\n"
                "✨ 핵심 특징 및 기술: {key_features}\n"
                "🎨 브랜드 분위기/톤앤매너: {tone_and_manner}\n"
                "🎁 프로모션 및 사은품 혜택: {promotions}"
            )
        ])

        # 4. LangChain LCEL(LangChain Expression Language) 파이프라인 결합
        # Prompt | Structured_LLM 구조로 한 번에 Pydantic 객체로 변환
        self.chain = self.prompt | self.structured_llm

    def create_detail_page(
        self,
        product_name: str,
        category: str,
        target_audience: str,
        key_features: str,
        tone_and_manner: str = "신뢰감을 주는 전문적인 고급 톤앤매너",
        promotions: str = "런칭 기념 특별 프로모션 진행 중"
    ) -> ProductDetailPage:
        """
        [상세페이지 생성 메서드]
        딕셔너리 형태의 입력 정보를 받아 LCEL 체인을 실행하고 완성형 ProductDetailPage 객체를 반환합니다.
        """
        print(f"\n🚀 [MyFavorite] '{product_name}' 상세페이지 기획 및 카피라이팅 생성 시작...")
        
        # LCEL 체인 실행 (AI가 구조화된 상세페이지 데이터를 생성)
        detail_page: ProductDetailPage = self.chain.invoke({
            "product_name": product_name,
            "category": category,
            "target_audience": target_audience,
            "key_features": key_features,
            "tone_and_manner": tone_and_manner,
            "promotions": promotions
        })
        
        print("✅ [MyFavorite] AI 상세페이지 콘텐츠 생성 완료!\n")
        return detail_page

    def save_markdown(self, detail_page: ProductDetailPage, filename: str = "detail_page.md") -> str:
        """
        [1. 마크다운(.md) 파일 저장 메서드]
        깃허브, 노션, 블로그 등에 즉시 붙여넣을 수 있는 정돈된 마크다운 문서로 저장합니다.
        """
        file_path = os.path.join(self.output_dir, filename)
        
        md_text = f"""# 🛍️ {detail_page.product_name}

> **{detail_page.hook_headline}**  
> *{detail_page.sub_headline}*

---

## 🎯 타겟 고객 페르소나
- **대상:** {detail_page.target_audience}

---

## 😫 혹시 이런 불편함, 느껴보신 적 있으신가요?
"""
        for p in detail_page.pain_points:
            md_text += f"- ❌ {p}\n"

        md_text += f"\n---\n\n## 💡 [완벽한 해결책] {detail_page.solution_summary}\n\n---\n\n## ✨ 차별화된 핵심 혜택 (Key Benefits)\n\n"
        for idx, f in enumerate(detail_page.features_and_benefits, 1):
            md_text += f"### {idx}. {f.feature_title}\n{f.benefit_description}\n\n"

        md_text += f"---\n\n## 🏆 신뢰의 증명 (Social Proof)\n{detail_page.social_proof}\n\n---\n\n## ❓ 자주 묻는 질문 (FAQ)\n\n"
        for idx, faq in enumerate(detail_page.faqs, 1):
            md_text += f"**Q{idx}. {faq.question}**\n\n> 💡 **A:** {faq.answer}\n\n"

        md_text += f"""---

## 🛒 지금 바로 특별한 혜택으로 만나보세요!

<div align="center">
  <a href="#">
    <button style="background-color:#E65100; color:white; padding:16px 36px; font-size:1.3rem; border:none; border-radius:12px; cursor:pointer; font-weight:bold;">
      👉 {detail_page.cta_button_text}
    </button>
  </a>
</div>
"""
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(md_text)

        print(f"📄 [1. 마크다운 저장 완료] -> '{file_path}'")
        return file_path

    def save_json(self, detail_page: ProductDetailPage, filename: str = "detail_page.json") -> str:
        """
        [2. 구조화된 JSON(.json) 파일 저장 메서드]
        백엔드 API 전송, 데이터베이스 적재, 쇼핑몰 솔루션 연동에 사용되는 JSON 데이터로 저장합니다.
        """
        file_path = os.path.join(self.output_dir, filename)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(detail_page.model_dump(), f, ensure_ascii=False, indent=2)
            
        print(f"💾 [2. JSON 데이터 저장 완료] -> '{file_path}'")
        return file_path

    def save_html(self, detail_page: ProductDetailPage, filename: str = "detail_page.html") -> str:
        """
        [3. 반응형 웹페이지(.html) 파일 저장 메서드]
        모던 프리미엄 디자인(글래스모피즘, 카드 UI, 그라디언트 CTA 버튼)이 적용된 단일 완성형 웹페이지로 저장합니다.
        """
        file_path = os.path.join(self.output_dir, filename)
        
        # 특징 및 혜택 카드 HTML 조립
        features_html = "".join([
            f"""
            <div class="feature-card">
                <div class="feature-badge">PREMIUM BENEFIT</div>
                <h3>⭐ {f.feature_title}</h3>
                <p>{f.benefit_description}</p>
            </div>
            """ for f in detail_page.features_and_benefits
        ])

        # FAQ 아코디언 카드 HTML 조립
        faqs_html = "".join([
            f"""
            <div class="faq-card">
                <h4><span class="q-mark">Q.</span> {faq.question}</h4>
                <p><span class="a-mark">A.</span> {faq.answer}</p>
            </div>
            """ for faq in detail_page.faqs
        ])

        # 문제 공감 포인트 HTML 조립
        pain_points_html = "".join([
            f"<li><span class='cross-icon'>❌</span> {p}</li>" for p in detail_page.pain_points
        ])

        # 완성된 HTML 템플릿
        html_content = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{detail_page.product_name} | 프리미엄 공식 상세페이지</title>
    <!-- 고급 웹폰트 Pretendard 로드 -->
    <link href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css" rel="stylesheet">
    <style>
        :root {{
            --primary: #E65100;
            --primary-light: #FFF3E0;
            --dark: #1A1A1A;
            --gray: #666666;
            --light-bg: #F8F9FA;
            --card-border: #EAEAEA;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif; }}
        body {{ background-color: #F0F2F5; color: var(--dark); line-height: 1.75; padding: 40px 16px; }}
        .container {{ max-width: 820px; margin: 0 auto; background: #FFFFFF; border-radius: 28px; box-shadow: 0 25px 60px rgba(0,0,0,0.08); overflow: hidden; padding: 60px 40px; }}
        
        /* 헤더 영역 */
        .header {{ text-align: center; padding-bottom: 40px; border-bottom: 2px solid #F1F3F5; }}
        .brand-tag {{ display: inline-block; background: var(--primary-light); color: var(--primary); font-weight: 800; padding: 8px 20px; border-radius: 30px; font-size: 0.95rem; margin-bottom: 20px; letter-spacing: 0.5px; }}
        h1 {{ font-size: 2.3rem; font-weight: 900; color: #111111; margin-bottom: 16px; word-break: keep-all; line-height: 1.35; }}
        .sub-headline {{ font-size: 1.25rem; color: var(--gray); word-break: keep-all; font-weight: 500; }}
        
        /* 섹션 공통 */
        .section {{ margin-top: 55px; }}
        .section-title {{ font-size: 1.6rem; font-weight: 800; margin-bottom: 24px; color: #111827; display: flex; align-items: center; gap: 10px; }}
        
        /* 문제점 공감 박스 (Pain Points) */
        .pain-box {{ background: #FFF5F5; border-left: 6px solid #FF5252; padding: 28px; border-radius: 16px; }}
        .pain-box ul {{ list-style: none; }}
        .pain-box li {{ font-size: 1.1rem; margin-bottom: 14px; color: #D32F2F; font-weight: 600; display: flex; align-items: flex-start; gap: 8px; }}
        .cross-icon {{ flex-shrink: 0; }}
        
        /* 해결책 박스 (Solution) */
        .solution-box {{ background: #F1F8E9; border-left: 6px solid #4CAF50; padding: 28px; border-radius: 16px; font-size: 1.15rem; color: #2E7D32; font-weight: 600; line-height: 1.8; }}
        
        /* 핵심 혜택 카드 (Features) */
        .feature-grid {{ display: grid; gap: 20px; }}
        .feature-card {{ background: #FAFAFA; border: 1px solid var(--card-border); border-radius: 20px; padding: 28px; transition: all 0.3s ease; }}
        .feature-card:hover {{ transform: translateY(-4px); box-shadow: 0 12px 28px rgba(0,0,0,0.06); border-color: #FFB74D; }}
        .feature-badge {{ display: inline-block; font-size: 0.75rem; font-weight: 800; background: #FFE0B2; color: #E65100; padding: 4px 10px; border-radius: 6px; margin-bottom: 10px; }}
        .feature-card h3 {{ font-size: 1.35rem; color: #111; margin-bottom: 10px; font-weight: 800; }}
        .feature-card p {{ font-size: 1.05rem; color: #4B5563; }}
        
        /* 신뢰의 증명 (Social Proof) */
        .proof-box {{ background: linear-gradient(135deg, #E3F2FD 0%, #BBDEFB 100%); padding: 28px; border-radius: 20px; color: #0D47A1; font-size: 1.1rem; font-weight: 600; line-height: 1.8; }}
        
        /* 자주 묻는 질문 (FAQ) */
        .faq-card {{ background: #F8F9FA; border-radius: 16px; padding: 24px; margin-bottom: 16px; border: 1px solid #ECEFF1; }}
        .faq-card h4 {{ color: #1976D2; font-size: 1.15rem; margin-bottom: 10px; font-weight: 700; }}
        .q-mark {{ color: #FF9800; font-weight: 900; }}
        .a-mark {{ color: #4CAF50; font-weight: 900; }}
        .faq-card p {{ font-size: 1.05rem; color: #374151; }}
        
        /* 구매 유도 CTA 박스 */
        .cta-section {{ text-align: center; margin-top: 60px; padding: 45px 30px; background: linear-gradient(135deg, #FF6F00 0%, #FF8F00 100%); border-radius: 24px; color: white; box-shadow: 0 15px 35px rgba(230,81,0,0.3); }}
        .cta-section h2 {{ font-size: 2rem; font-weight: 900; margin-bottom: 12px; }}
        .cta-section p {{ font-size: 1.15rem; opacity: 0.95; margin-bottom: 28px; }}
        .cta-btn {{ display: inline-block; background: #FFFFFF; color: #E65100; font-weight: 900; font-size: 1.35rem; padding: 20px 50px; border-radius: 50px; text-decoration: none; box-shadow: 0 10px 25px rgba(0,0,0,0.2); transition: all 0.3s ease; }}
        .cta-btn:hover {{ transform: scale(1.06); background: #FFF8E1; }}
        
        /* 모바일 반응형 대응 */
        @media (max-width: 640px) {{
            .container {{ padding: 36px 20px; }}
            h1 {{ font-size: 1.8rem; }}
            .sub-headline {{ font-size: 1.1rem; }}
            .cta-btn {{ font-size: 1.15rem; padding: 16px 36px; width: 100%; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- 1. 헤더 영역 -->
        <div class="header">
            <span class="brand-tag">✨ 프리미엄 공식 추천 상품</span>
            <h1>{detail_page.hook_headline}</h1>
            <p class="sub-headline">{detail_page.sub_headline}</p>
        </div>

        <!-- 2. 고객 문제점 공감 (Pain Points) -->
        <div class="section">
            <h2 class="section-title">😫 혹시 이런 고민, 해보신 적 있으신가요?</h2>
            <div class="pain-box">
                <ul>{pain_points_html}</ul>
            </div>
        </div>

        <!-- 3. 완벽한 솔루션 제안 (Solution) -->
        <div class="section">
            <h2 class="section-title">💡 MyFavorite이 제안하는 명쾌한 해결책</h2>
            <div class="solution-box">
                {detail_page.solution_summary}
            </div>
        </div>

        <!-- 4. 핵심 특장점 및 고객 혜택 (Features & Benefits) -->
        <div class="section">
            <h2 class="section-title">✨ 차별화된 핵심 프리미엄 혜택</h2>
            <div class="feature-grid">
                {features_html}
            </div>
        </div>

        <!-- 5. 신뢰의 증명 (Social Proof) -->
        <div class="section">
            <h2 class="section-title">🏆 신뢰의 약속 & 안심 보증</h2>
            <div class="proof-box">
                {detail_page.social_proof}
            </div>
        </div>

        <!-- 6. 자주 묻는 질문 (FAQ) -->
        <div class="section">
            <h2 class="section-title">❓ 구매 전 자주 묻는 질문 (FAQ)</h2>
            {faqs_html}
        </div>

        <!-- 7. 구매 전환 유도 (CTA) -->
        <div class="cta-section">
            <h2>지금 특별한 런칭 혜택으로 만나보세요!</h2>
            <p>한정 수량 특별 사은품 증정 이벤트가 마감 임박 상태입니다.</p>
            <a href="#" class="cta-btn">👉 {detail_page.cta_button_text}</a>
        </div>
    </div>
</body>
</html>
"""
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        print(f"🌐 [3. 웹 반응형 HTML 저장 완료] -> '{file_path}'")
        return file_path


# ==============================================================================
# [4단계] 비즈니스 실전 실행 데모 (Main Execution)
# ==============================================================================

def main():
    print("=" * 70)
    print(" 🌟 [MyFavorite] 콘텐츠 & 프리미엄 상세페이지 자동 제작 시스템")
    print("    (LangChain LCEL + Pydantic 스키마 + Markdown/HTML/JSON 동시 생성)")
    print("=" * 70)

    # 1. MyFavorite 생성기 인스턴스 생성
    creator = MyFavorite(model_name="openai/gpt-4o-mini", temperature=0.7)

    # 2. [실전 상품 입력] '하나투 빔프로젝터' 프리미엄 홈시네마 & 오피스 에디션 정보
    sample_product = {
        # 1. 정식 상품명 (전문성과 브랜드 파워를 극대화한 네이밍)
        "product_name": "하나투 시네마 프라임 4K 레이저 빔프로젝터 (HANATWO Cinema Prime 4K Laser)",

        # 2. 카테고리
        "category": "하이엔드 영상 가전 / 4K UHD 레이저 홈시네마 & 프리미엄 비즈니스 프로젝터",

        # 3. 구체적인 타겟 고객 페르소나
        "target_audience": (
            "1) 저가형 미니빔의 흐린 화질과 모터 소음에 실망하고, 거실 TV를 대체할 300인치 극장급 홈시네마를 찾는 3050 프리미엄 고객\n"
            "2) 암막 커튼 없이 대낮이나 조명이 켜진 대회의실에서도 또렷한 텍스트 가독성과 끊김 없는 무선 프레젠테이션이 필요한 기업/스타트업 임원 및 총무팀\n"
            "3) OTT(넷플릭스·디즈니+) 영화, PS5/Xbox 120Hz 고주사율 게이밍, 스포츠 생중계를 압도적인 몰입감으로 즐기고 싶은 얼리어답터"
        ),

        # 4. 차별화된 핵심 기능 4가지
        "key_features": (
            "1. [대낮에도 선명한 3,800 안시루멘 & 리얼 4K UHD] 암막 커튼 없이 형광등 아래에서도 생생하고 선명한 4K(3840x2160) 해상도 및 3,000,000:1 고명암비 지원\n"
            "2. [반영구 ALPD 4.0 트리플 레이저 광원] 30,000시간 수명(하루 4시간 기준 20년 사용)으로 램프 교체 비용 0원 & 자연색 그대로를 재현하는 NTSC 115% 광색역\n"
            "3. [전원 켜면 0.2초 자동 세팅] ToF 센서 기반 초고속 AI 오토포커스 + 상하좌우 6D 무왜곡 자동 키스톤 + 벽면 장애물 및 스크린 테두리 자동 인식 맞춤 기술\n"
            "4. [하만카돈 20W 돌비 애트모스 사운드 & 22dB 초저소음] 별도 스피커 없이도 가슴을 울리는 극장급 입체 음향 및 도서관보다 조용한 항공기 듀얼 쿨링 시스템"
        ),

        # 5. 브랜드 분위기 톤앤매너
        "tone_and_manner": "전문가의 광학 기술력과 하이엔드 라이프스타일의 품격을 전달하는 신뢰감 넘치고 세련된 프리미엄 톤",

        # 6. 고객을 사로잡을 특별 프로모션 혜택
        "promotions": (
            "🎁 [하나투 공식 런칭 기념 5대 특별 혜택]\n"
            "① 120인치 고화질 무선 전동 텐션 스크린 100% 무료 증정 (38만원 상당)\n"
            "② 전문 엔지니어 전국 무료 방문 설치 및 화질 최적화 캘리브레이션 지원\n"
            "③ 안심 보증 3년 무상 A/S (1년 이내 문제 발생 시 1:1 새제품 맞교환)\n"
            "④ 넷플릭스·유튜브 정식 인증 전용 블루투스 음성 리모컨 + 4K HDMI 2.1 케이블 기본 동봉\n"
            "⑤ 포토리뷰 작성 시 네이버페이 30,000원 100% 즉시 지급"
        )
    }

    # 3. 상세페이지 콘텐츠 자동 생성 (LCEL 체인 실행)
    page_data: ProductDetailPage = creator.create_detail_page(**sample_product)

    # 4. 콘솔 주요 결과 출력
    print("=" * 70)
    print(" 📋 [제작된 상세페이지 핵심 카피라이팅 요약]")
    print("=" * 70)
    print(f"📦 [상품명] {page_data.product_name}")
    print(f"🎯 [타겟 고객] {page_data.target_audience}")
    print(f"🔥 [후크 헤드라인] \"{page_data.hook_headline}\"")
    print(f"📌 [서브 카피] \"{page_data.sub_headline}\"")
    print(f"\n💡 [솔루션 요약]\n   {page_data.solution_summary}\n")
    print(f"🛒 [CTA 버튼] \"{page_data.cta_button_text}\"")
    print("=" * 70)

    # 5. 결과 파일 3종 (Markdown, JSON, HTML) 저장
    md_file = creator.save_markdown(page_data, "hanatwo_projector_detail.md")
    json_file = creator.save_json(page_data, "hanatwo_projector_detail.json")
    html_file = creator.save_html(page_data, "hanatwo_projector_detail.html")

    print("\n" + "=" * 70)
    print("🎉 축하합니다! '하나투 빔프로젝터' 상세페이지 3종 세트가 완성되었습니다!")
    print(f"  1. 📄 마크다운 문서   : {md_file}")
    print(f"  2. 💾 구조화 JSON 데이터 : {json_file}")
    print(f"  3. 🌐 웹 반응형 HTML    : {html_file}")
    print("=" * 70)


if __name__ == "__main__":
    main()
