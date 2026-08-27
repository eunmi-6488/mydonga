import sys
import os

# ── Windows 콘솔 UTF-8 인코딩 설정 (한글 깨짐 방지) ────────────
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# pydantic
import yfinance as yf
import pytz

from datetime import datetime
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from dotenv import load_dotenv
load_dotenv()
model = ChatOpenAI(model="gpt-4o", temperature=0)


from pydantic import BaseModel, Field

class StockHistoryInput(BaseModel):   
    ticker: str = Field(..., title='주식코드', description='주식 티커 코드 (예: AAPL, TSLA, 한국 주식은 083450.KQ(GST), 005930.KS(삼성전자) 형식)')
    period: str = Field(..., title='기간', description='주식 데이터 조회 기간 (예: 1d, 5d, 1mo, 1y)')


@tool
def get_yf_stock_history(stock_history_input: StockHistoryInput) -> str:
    """ 주식 종목의 가격 데이터를 조회하는 함수 """
    stock = yf.Ticker(ticker=stock_history_input.ticker)
    history = stock.history(period=stock_history_input.period)
    print('history 타입:', type(history))
    print()
    if history.empty:
        return f"{stock_history_input.ticker} 종목에 대한 주가 데이터를 찾을 수 없습니다."
    history_md = history.to_markdown()
    return history_md


@tool
def get_current_time(timezone: str, location: str) -> str:
    """
    현재 시간을 YYYY-MM-DD HH:MM:SS 형식으로 반환하는 함수
    Args:
        timezone (str): 타임존(예: "Asia/Seoul"). 실제 존재해야 함.
        location (str): 지역명.
    """
    tz = pytz.timezone(timezone)
    now = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
    return f"{timezone} ({location}) 현재시간 {now}"


# 랭체인 @tool 포함된 함수 기능처럼 이름으로 접근 가능
tools = [get_yf_stock_history, get_current_time]
tool_dict = {
    "get_current_time": get_current_time,
    "get_yf_stock_history": get_yf_stock_history
}

# 도구를 모델에 바인딩
llm_with_tools = model.bind_tools(tools)

# 도구를 사용해 언어 모델 답변 생성
messages = [
    SystemMessage("당신은 사용자의 질문에 답변을 하기 위해 tools를 사용할 수 있는 AI 어시스턴트입니다. 한국 종목(예: GST)의 경우 코스닥(.KQ) 또는 코스피(.KS) 티커(예: GST -> 083450.KQ)를 활용하세요."),
    HumanMessage("GST의 최근 3일간 주가 정보는 어떻게 되지?")
]

response = llm_with_tools.invoke(messages)
messages.append(response)


for tool_call in response.tool_calls:
   selected_tool = tool_dict.get(tool_call['name'])
   tool_msg = selected_tool.invoke(tool_call)
   messages.append(tool_msg)


response = llm_with_tools.invoke(messages)
print(response)
print('- ' * 50)
print()
print(response.content)


# ModuleNotFoundError: No module named 'yfinance' 
# pip install yfinance

# ModuleNotFoundError: No module named 'pytz'
# pip install pytz

# ImportError: `Import tabulate` failed.  Use pip or conda to install the tabulate package.
# pip install tabulate

