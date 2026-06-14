# Branding-only tools example
from langchain.tools import tool

@tool
def web_search(query:str)->str:
    return 'SOURCE\n------\nHeadline: Example'
