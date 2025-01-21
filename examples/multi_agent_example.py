
# 필요한 라이브러리들을 임포트합니다
from smolagents import CodeAgent, ToolCallingAgent, DuckDuckGoSearchTool, LiteLLMModel, PythonInterpreterTool, tool, TOOL_CALLING_SYSTEM_PROMPT
from typing import Optional
import os

# .env 파일에서 환경 변수를 로드합니다
from dotenv import load_dotenv
load_dotenv()

# Gemini AI 모델을 초기화합니다
# LiteLLMModel을 사용하여 여러 LLM을 통합적으로 사용할 수 있습니다
model = LiteLLMModel(model_id="gemini/gemini-2.0-flash-exp",
                     api_key=os.getenv("GOOGLE_API_KEY"))


# @tool 데코레이터를 사용하여 agent가 사용할 수 있는 도구를 정의합니다
@tool
def get_weather(location: str, celsius: Optional[bool] = False) -> str:
    """
    주어진 위치의 날씨 정보를 가져오는 도구입니다.
    Args:
        location: 날씨를 확인할 위치
        celsius: 섭씨 온도 사용 여부 (기본값: False)
    """
    return f"The weather in {location} is sunny with temperatures around 7°C."

# ToolCallingAgent를 생성합니다
# 이 agent는 정의된 도구들(여기서는 get_weather)을 사용할 수 있습니다
agent = ToolCallingAgent(tools=[get_weather], model=model, system_prompt=TOOL_CALLING_SYSTEM_PROMPT)


# CodeAgent를 생성합니다
# 이 agent는 DuckDuckGo 검색 도구를 사용할 수 있으며, requests와 bs4 라이브러리 사용이 허용됩니다
agent = CodeAgent(tools=[DuckDuckGoSearchTool()], model=model, additional_authorized_imports=["requests", "bs4"])

user_input = input("무엇이 궁금하신가요? (자유롭게 질문해주세요): ")
answer = agent.run(user_input)
print(answer)