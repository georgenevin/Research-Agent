from typing import TypedDict, Annotated , Optional, List
from langchain_core.messages import (

    HumanMessage,
    AIMessage,
    SystemMessage,
)
from langchain_openai import ChatOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from langgraph.graph import StateGraph, START, END
from langchain_mcp_adapters.client import MultiServerMCPClient
import os
from dotenv import load_dotenv
from langgraph.prebuilt import ToolNode
import requests
from bs4 import BeautifulSoup
from langchain_core.tools import tool
import asyncio
from langchain.agents import create_agent


load_dotenv()

class ResearchAgentState(TypedDict):
    query: str
    research_results: Annotated[Optional[List[str]], {"description": "List of research results"}] = None
    research_feedback: Annotated[Optional[str], {"description": "Supervisor's feedback on the research result"}] = None
    summary_approved: Annotated[Optional[bool], {"description": "Indicates if the summary is approved"}] = None
    summary: Annotated[Optional[str], {"description": "Summary of the research results"}] = None
    revision_notes: Annotated[Optional[str], {"description": "Notes for revision based on supervisor's feedback"}] = None
    revision_counter: Annotated[Optional[int], {"description": "Counter for the number of revisions"}] = 0


token_provider = get_bearer_token_provider(
    DefaultAzureCredential(),
    "https://cognitiveservices.azure.com/.default"
)

def route_supervisor(state):
    if state["research_feedback"] is not None:
        return "research_agent"
    elif state.get("summary_approved"):
        return "END"
    else:
        return "summarizer_agent"

@tool
async def web_scraper(url: str) -> str:
    """
    Scrape webpage content from a URL.
    """
    try:
        headers = {
            "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
             "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/138.0.0.0 Safari/537.36"
        ),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
    }
       
        response = await asyncio.to_thread(
            requests.get,
            url,
            timeout=15,
            headers=headers
        )

        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        text = soup.get_text(" ", strip=True)

        return text[:5000]

    except Exception as e:
        return f"Failed to scrape {url}: {str(e)}"


async def research_agent(state: ResearchAgentState):

    user_query = state["query"]
    tavily_url = os.getenv("TAVILY_URL")

    mcp_client = MultiServerMCPClient(
        {
            "tavily": {
                "url": tavily_url,
                "transport": "streamable_http",
            }
        }
    )

    mcp_tools = await mcp_client.get_tools()
    tools = mcp_tools + [web_scraper]

    system_prompt = """
You are a research assistant.

Rules:
1. Call tavily_research EXACTLY ONCE.
2. Select at most 3 URLs from the search results.
3. Call web_scraper only on those URLs.
4. Never call tavily_research a second time.
5. Never search for additional URLs.
6. After scraping the URLs, provide the final answer immediately.
7. Do not continue tool calling after scraping.
8. Maximum tool calls allowed:
   - tavily_research: 1
   - web_scraper: 3
"""

    agent = create_agent(
        model=llm,
        tools=tools,
    )

    response = await agent.ainvoke(
        {
            "messages": [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_query),
            ]
        },
        {
            "recursion_limit": 10
        }
    )

    final_content = response["messages"][-1].content

    return {
        "research_results": final_content,
        "research_feedback": None,
        "summary_approved": None,
        "summary": None,
        "revision_notes": None,
        "revision_counter": state.get("revision_counter", 0),
    }


MAX_REVISIONS = 3

def supervisor_agent(state: ResearchAgentState):
    SUPERVISOR_PROMPT = """You manage a research team with two workers:
- researcher: searches the web for facts/current info
- summarizer: writes a final answer based on gathered research

Review the query, research results, and current summary below.

Reply with EXACTLY these two lines:
DECISION: NEED_RESEARCH | NEED_SUMMARY | APPROVED
NOTES: <feedback explaining your decision and what to fix, or 'none' if approved>
"""

    context = f"""Query: {state['query']}

Research results:
{state.get('research_results', 'None yet')}

Current summary:
{state.get('summary', 'None yet')}
"""

    revision_counter = state.get("revision_counter", 0)

    # Hard stop regardless of what the LLM says
    if revision_counter >= MAX_REVISIONS:
        return {
            "research_feedback": None,
            "summary_approved": True,
            "revision_notes": None,
            "revision_counter": revision_counter,
        }

    response = llm.invoke([
        SystemMessage(content=SUPERVISOR_PROMPT),
        HumanMessage(content=context),
    ])

    lines = response.content.strip().split("\n")
    decision = lines[0].replace("DECISION:", "").strip()
    notes = lines[1].replace("NOTES:", "").strip() if len(lines) > 1 else ""

    if decision == "NEED_RESEARCH":
        return {
            "research_feedback": notes,
            "summary_approved": None,
            "revision_notes": None,
            "revision_counter": revision_counter + 1,
        }
    elif decision == "APPROVED":
        return {
            "research_feedback": None,
            "summary_approved": True,
            "revision_notes": None,
            "revision_counter": revision_counter,
        }
    else:  # NEED_SUMMARY
        return {
            "research_feedback": None,
            "summary_approved": None,
            "revision_notes": notes,
            "revision_counter": revision_counter + 1,
        }

def summarizer_agent(state: ResearchAgentState):
    SUMMARIZER_PROMPT = """You are a summarizer tasked with creating a concise and accurate summary based on the research results provided.
                           Review the research results and any feedback from the supervisor.
                           Create a summary that directly answers the user's query, ensuring clarity and completeness.
                           If the research results are insufficient or unclear, indicate what additional information is needed.
"""

    user_query = state["query"]
    research_results = state.get("research_results", "")
    revision_notes = state.get("revision_notes")

    human_content = f"User query: {user_query}\n\nResearch results:\n{research_results}"
    if revision_notes:
        human_content += f"\n\nFeedback from supervisor to address:\n{revision_notes}"

    response = llm.invoke([
        SystemMessage(content=SUMMARIZER_PROMPT),
        HumanMessage(content=human_content),
    ])

    return {
        "summary": response.content,
        "summary_approved": None,
        "revision_notes": None,  
    }                 
    





async def main():
   
    user_input = input("What is your research topic")
    graph = StateGraph(ResearchAgentState)
    graph.add_node("research_agent", research_agent)
    graph.add_node("supervisor_agent", supervisor_agent)
    graph.add_node("summarizer_agent", summarizer_agent)

    graph.add_edge(START, "supervisor_agent")
    graph.add_conditional_edges(
    "supervisor_agent",
             route_supervisor,
            {
                    "research_agent": "research_agent",
                    "summarizer_agent": "summarizer_agent",
                    "END": END,
            }
        )
    graph.add_edge("research_agent", "supervisor_agent")
    graph.add_edge("summarizer_agent", "supervisor_agent")
  
    global llm
    llm = ChatOpenAI(
        base_url=os.getenv("OPENAI_ENDPOINT"),
        api_key=token_provider(),   # note: this is a snapshot token, see caveat below
        model="gpt-5.4-mini-2",
    )
    research_graph = graph.compile()
    result = await research_graph.ainvoke(
        {
            "query": user_input
        }
    )
    
    print("Research Agent Result")
    final_response = result["research_results"]
    print(final_response)

  


if __name__ == "__main__":
    asyncio.run(main())
