# Modified branding version of your agents.py
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from tools import web_search, scrape_url
from dotenv import load_dotenv

load_dotenv()

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

def build_discovery_agent():
    return create_agent(model=llm, tools=[web_search])

def build_intelligence_agent():
    return create_agent(model=llm, tools=[scrape_url])

writer_prompt = ChatPromptTemplate.from_messages([
    ("system","You are a senior research analyst and technical communicator."),
    ("human","Topic: {topic}\n\nResearch:\n{research}")
])

synthesis_chain = writer_prompt | llm | StrOutputParser()
