

import os
import sys

# Windows 터미널 출력 인코딩 설정 (Emoji 및 UTF-8 지원)
sys.stdout.reconfigure(encoding='utf-8')

from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

#1 모델기술
model = ChatOllama(model='gemma3:latest')


#2 프롬프트 템플릿
prompt = ChatPromptTemplate([
   ("system", "길동님은 친절하고 전문적인 인공지능 AI선생님이야. 사용자의 질문에 한국어로 친절히 답해주세요."),
   ("user", "{question}에 대해서 설명해줘")
  ])

#3 LCEL언어지원  | 연결
chain = prompt | model | StrOutputParser()
result = chain.invoke({'question':'미녀와야수'})
print(result)

# 2026-08-27 목요일 12시 37분
