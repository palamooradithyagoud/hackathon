"""
Main Conversational Orchestrator Agent.
Classifies user intent and routes queries to correct sub-agents (RAG, Collaboration, Professor Mode).
"""

import json
from services.groq_service import GroqService
from rag.pipeline import RagPipeline
from agents.collaboration_agent import CollaborationAgent
from agents.professor_agent import ProfessorAgent
from prompts.system_prompts import PROJECT_SYSTEM, PROJECT_USER_TEMPLATE
from core.logger import logger

class ChatAgent:
    def __init__(self):
        self.llm = GroqService()
        self.rag = RagPipeline()
        self.collaboration = CollaborationAgent()
        self.professor = ProfessorAgent()

    def classify_intent(self, query: str) -> dict:
        """Uses Groq to classify query intent and extract parameters."""
        classification_system = (
            "You are a routing agent for a University Faculty Research Platform.\n"
            "Classify the user query into one of these intents:\n"
            "- 'lookup': asking about a specific faculty member (e.g., 'Tell me about Dr. X')\n"
            "- 'collaborate': asking about matching professors or collaborations (e.g., 'Suggest collaboration between X and Y')\n"
            "- 'project': asking for new research project suggestions on a topic\n"
            "- 'professor': asking for gap analysis or global trend comparison (e.g., 'Professor mode: IoT')\n"
            "- 'chat': greetings, off-topic questions, queries about your capabilities, or generic conversation (e.g., 'what are the capabilities of you', 'hello', 'who are you', 'help')\n"
            "- 'rag': general research or expert search questions (e.g., 'Who works on Federated Learning?')\n\n"
            "Respond ONLY with a JSON object containing keys:\n"
            "- 'intent': one of ['lookup', 'collaborate', 'project', 'professor', 'chat', 'rag']\n"
            "- 'names': list of professor names extracted (if any)\n"
            "- 'topic': extracted search topic/keywords (if any)"
        )
        
        try:
            response = self.llm.generate(
                user_prompt=query,
                system_prompt=classification_system,
                temperature=0.1,
                max_tokens=200
            )
            # Find JSON boundaries in case of wrapping text
            start = response.find("{")
            end = response.rfind("}") + 1
            if start != -1 and end != -1:
                return json.loads(response[start:end])
        except Exception as e:
            logger.error(f"Intent classification failed: {e}")
            
        return {"intent": "rag", "names": [], "topic": query}

    def run_query(self, query: str, role: str = "student") -> dict:
        """Classifies, routes, and processes the query, returning structured response data."""
        from utils.helpers import sanitize_user_query
        query = sanitize_user_query(query)
        
        clf = self.classify_intent(query)
        intent = clf.get("intent", "rag")
        names = clf.get("names", [])
        topic = clf.get("topic", query) or query
        
        # Ensure names is list of strings
        if not isinstance(names, list):
            names = [str(names)] if names else []
        names = [str(n) for n in names]
            
        # Ensure topic is a string
        if isinstance(topic, list):
            topic = " ".join(topic)
        topic = str(topic)
        
        logger.info(f"Routed intent: {intent} (extracted names: {names}, topic: '{topic}')")
        
        if intent == "lookup" and names:
            # Scoped Faculty Lookup
            prof_name = names[0]
            profile_text = self.collaboration.get_faculty_profile(prof_name)
            if profile_text.strip():
                response_text = f"Dr. {prof_name.capitalize()} Research Profile:\n\n{profile_text}"
            else:
                response_text = f"No detailed faculty profile could be found for Dr. {prof_name.capitalize()}."
                
            return {
                "intent": "lookup",
                "response_text": response_text,
                "data": {"name": prof_name, "profile": profile_text}
            }
            
        elif intent == "collaborate":
            # Collaboration Engine
            if len(names) >= 2:
                col_res = self.collaboration.suggest_collaboration(names[0], names[1])
            else:
                col_res = self.collaboration.recommend_collaboration_by_topic(topic)
                
            if col_res.get("success"):
                return {
                    "intent": "collaborate",
                    "response_text": col_res["full_response"],
                    "data": col_res
                }
            else:
                return {
                    "intent": "collaborate",
                    "response_text": f"Could not generate collaboration recommendations: {col_res.get('error')}",
                    "data": col_res
                }
                
        elif intent == "project":
            # Project Suggestion Engine
            results = self.rag.retriever.retrieve(topic, n_results=6)
            formatted_profiles = "\n\n".join([f"Page: {r['metadata'].get('page')}\n{r['document']}" for r in results])
            
            # Fetch external trends to inform the project engine
            external_papers = self.rag.arxiv.search_papers(topic, max_results=2)
            external_web = self.rag.tavily.search(topic, max_results=2)
            
            from prompts.templates import format_external_trends
            trends_summary = format_external_trends(external_web, external_papers)
            
            user_prompt = PROJECT_USER_TEMPLATE.format(
                profiles=formatted_profiles,
                trends=trends_summary
            )
            
            project_response = self.llm.generate(
                user_prompt=user_prompt,
                system_prompt=PROJECT_SYSTEM,
                temperature=0.4
            )
            
            return {
                "intent": "project",
                "response_text": project_response,
                "data": {
                    "topic": topic,
                    "profiles_used": formatted_profiles,
                    "project_suggestion": project_response
                }
            }
            
        elif intent == "professor":
            # Professor Mode - Gap Analysis
            prof_res = self.professor.analyze_gaps(topic)
            return {
                "intent": "professor",
                "response_text": prof_res["analysis"],
                "data": prof_res
            }
            
        elif intent == "chat":
            # General conversation, capabilities, or greetings
            system_prompt = (
                "You are the Faculty Research Assistant RAG + Collaboration Platform AI.\n"
                "Explain your capabilities clearly, politely, and professionally.\n"
                "You can help users with the following tasks:\n"
                "1. Answer research expert search queries using RAG over faculty profiles (e.g. 'Who works on Federated Learning?').\n"
                "2. Provide detailed scoped lookups for specific faculty members.\n"
                "3. Recommend and evaluate synergies for potential faculty collaborations.\n"
                "4. Suggest research projects based on global trends and faculty profile fits.\n"
                "5. Run 'Professor Mode' gap analysis comparing local faculty expertise against global research trends (from arXiv and Tavily).\n\n"
                "Provide a structured, helpful explanation of these capabilities. Keep the tone academic and supportive."
            )
            chat_response = self.llm.generate(
                user_prompt=query,
                system_prompt=system_prompt,
                temperature=0.3
            )
            return {
                "intent": "chat",
                "response_text": chat_response,
                "data": {"query": query}
            }
            
        else:
            # Fallback to standard RAG Faculty Search
            rag_res = self.rag.run(query, role=role)
            return {
                "intent": "rag",
                "response_text": rag_res["response_text"],
                "data": rag_res
            }
