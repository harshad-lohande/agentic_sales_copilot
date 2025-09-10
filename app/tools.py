# app/tools.py

from tavily import TavilyClient
from agents import function_tool

from .config import settings
from .logging_config import logger


@function_tool
def web_search(first_name: str, last_name: str, company: str):
    """
    Performs a comprehensive web search using a set of targeted queries to find recent,
    relevant information about a prospect and their company.

    Args:
        first_name: The first name of the prospect.
        last_name: The last name of the prospect.
        company: The company of the prospect.
    """
    logger.info(
        {
            "message": "Performing comprehensive web search",
            "prospect": f"{first_name} {last_name}",
            "company": company,
        }
    )

    # Generate a list of targeted search queries for freshness and relevance

    queries = [
        f'"{first_name} {last_name}" {company} recent news',
        f"{company} achievements or milestones",
        f'"{first_name} {last_name}" recent interviews or blog posts',
        f'"{first_name} {last_name}" {company} linkedin profile',
        f"{company} linkedin page",
    ]

    all_results = []
    try:
        tavily = TavilyClient(api_key=settings.TAVILY_API_KEY)
        for query in queries:
            response = tavily.search(
                query=query, search_depth="basic", max_results=2, time_range="week"
            )
            if response.get("results"):
                all_results.extend(response["results"])

        if not all_results:
            logger.warning({"message": "Comprehensive web search returned no results"})
            return "No relevant information found."

        # Consolidate results into a single summary string
        consolidated_summary = "\n\n---\n\n".join(
            [f"URL: {res['url']}\nContent: {res['content']}" for res in all_results]
        )
        logger.info({"message": "Comprehensive web search successful"})
        return consolidated_summary

    except Exception as e:
        logger.error(
            {"message": "Error during comprehensive web search", "error": str(e)}
        )
        return f"An error occurred during the web search: {e}"
