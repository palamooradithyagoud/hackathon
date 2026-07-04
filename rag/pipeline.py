"""
RAG Ingestion and Ingress Pipeline.
Coordinates retrieval, filtering, fallback searches (Tavily/arXiv), and Groq LLM synthesis.
"""

from services.groq_service import GroqService
from services.tavily_service import TavilyService
from services.arxiv_service import ArxivService
from rag.retriever import ChromaRetriever
from rag.reranker import Reranker
from core.logger import logger

class RagPipeline:
    def __init__(self):
        self.retriever = ChromaRetriever()
        self.reranker = Reranker()
        self.llm = GroqService()
        self.tavily = TavilyService()
        self.arxiv = ArxivService()

    def run(self, query: str, role: str = "student") -> dict:
        """
        Executes the full RAG pipeline:
        ChromaDB Search -> Reranker check -> (Optional Tavily + arXiv fallback) -> LLM Synthesis
        """
        logger.info(f"Starting RAG pipeline for query: '{query}' in {role.upper()} mode")
        
        # 1. Retrieve from ChromaDB
        db_results = self.retriever.retrieve(query)
        
        # 2. Check if results are weak
        scored_results, is_weak = self.reranker.analyze_results(db_results)
        
        external_summary = ""
        external_papers = []
        external_web = []
        is_fallback_active = False
        
        # 3. Fallback logic if ChromaDB results are weak/empty
        if is_weak or not scored_results:
            logger.info("Weak similarity score or no database matches. Triggering fallback intelligence...")
            is_fallback_active = True
            
            # Fetch latest academic papers from arXiv
            try:
                arxiv_results = self.arxiv.search_papers(query, max_results=3)
            except Exception as e:
                logger.error(f"arXiv fallback query failed: {e}")
                arxiv_results = []
            external_papers = arxiv_results
            
            # Fetch current trends from web search (Tavily)
            try:
                web_results = self.tavily.search(query, max_results=3)
            except Exception as e:
                logger.error(f"Tavily fallback query failed: {e}")
                web_results = []
            external_web = web_results
            
            # Synthesize external knowledge description
            trend_lines = []
            if arxiv_results:
                trend_lines.append("Latest papers from arXiv:")
                for p in arxiv_results:
                    trend_lines.append(f"- {p['title']} by {', '.join(p['authors'])} (URL: {p['url']})")
            if web_results:
                trend_lines.append("Current web research trends:")
                for w in web_results:
                    trend_lines.append(f"- {w['title']}: {w['content']} (Source: {w['url']})")
                    
            external_summary = "\n".join(trend_lines) if trend_lines else "No external information retrieved."
            
        # 4. Generate response using Groq
        # Prepare context
        context_parts = []
        for res in scored_results:
            meta = res["metadata"]
            source = meta.get("source", "Unknown Document")
            page = meta.get("page", "?")
            context_parts.append(f"[Source: {source}, Page {page}]\n{res['document']}")
            
        internal_context = "\n\n".join(context_parts)
        
        # Construct LLM prompt
        tone_instruction = ""
        if role == "student":
            tone_instruction = (
                "- Adapt tone for a STUDENT: Use clear, encouraging, accessible language. "
                "Briefly explain any advanced concepts or acronyms. Frame the matching faculty "
                "members as potential advisors or mentors, and mention how students could get involved."
            )
        else:
            tone_instruction = (
                "- Adapt tone for a FACULTY member: Use advanced academic terminology, citation-level depth, "
                "and reference specific research methodologies and venue information. Focus on potential "
                "collaboration, grant alignments, and peer-to-peer synergy."
            )

        system_prompt = (
            "You are a helpful Research Assistant RAG agent at our University. Your goal is to help "
            "users find faculty members and understand their expertise.\n"
            "RULES:\n"
            "- Answer using only the provided context.\n"
            "- Extract and mention ALL ACTUAL AUTHORS of the matched papers (usually listed on Page 1 "
            "under the title). Do not omit co-authors (e.g. if the paper is authored by Shirina Samreen and "
            "Akhil Jabbar Meerja, you must list and discuss both of them).\n"
            "- Distinguish between the ACTUAL AUTHORS of the paper and authors mentioned in the REFERENCES/CITATIONS section. "
            "Do not list reference authors as local faculty.\n"
            "- Hide similarity/distance scores from the user. Instead, explain matches qualitatively.\n"
            "- If fallback intelligence is active, compare the external global research trends with the local faculty "
            "profiles, explain that local matches are limited but recommend the closest candidates anyway based on overlap.\n"
            f"{tone_instruction}\n"
            "- Be concise, direct, and professional."
        )
        
        if is_fallback_active:
            user_prompt = f"""We could not find highly confident matches in our internal database.
We ran a global search for current trends and papers.

Global Research Trends & Papers for '{query}':
---
{external_summary}
---

Closest Internal Faculty Profiles available:
---
{internal_context}
---

Compare these global trends against our closest local faculty profiles. Present your output structured as follows:

Internal Knowledge:
[Qualitative summary of the closest local faculty members we have, and who they are]

External Research Trends:
[Summarize latest Tavily + arXiv trends/papers found]

Final Recommendation:
[Explain who is recommended among our faculty anyway, reasoning why their background has the closest overlap with these external trends]
"""
        else:
            user_prompt = f"""We found internal database matches for '{query}'.

Local Faculty Profiles:
---
{internal_context}
---

Question: {query}

Provide a summary of the matched faculty members. Explain why they are relevant using qualitative reasoning (refer to their projects/expertise, not scores). Mention page citations if helpful.
"""
            
        logger.info("Sending context to Groq for synthesis...")
        response_text = self.llm.generate(
            user_prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.3
        )
        
        return {
            "query": query,
            "internal_matches": scored_results,
            "external_summary": external_summary,
            "external_papers": external_papers,
            "external_web": external_web,
            "is_fallback_active": is_fallback_active,
            "response_text": response_text
        }
