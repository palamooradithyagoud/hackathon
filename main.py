"""
Faculty Research RAG & Collaboration Intelligence Platform CLI.
Direct chat interface featuring conversational RAG, collaboration matchmaking,
trend/gap analysis, confirmation logging, and interactive feedback.
"""

import sys
from db.init_db import init_database
from agents.chat_agent import ChatAgent
from memory.memory_store import MemoryStore
from core.logger import logger

def main():
    print("=" * 65)
    print("  Faculty Research Assistant RAG + Collaboration Platform")
    print("=" * 65)
    
    # 1. Initialize DB tables
    try:
        init_database()
    except Exception as e:
        print(f"Database initialization failed: {e}")
        sys.exit(1)
        
    # 2. Instantiate main orchestrator and memory store
    chat_agent = ChatAgent()
    memory = MemoryStore()
    
    print("Choose your default user role:")
    print("  1. Student (simple, educational tone)")
    print("  2. Faculty (academic depth, peer-to-peer synergy tone)")
    role_choice = input("Select option (1 or 2, default: 1): ").strip()
    user_role = "faculty" if role_choice == "2" else "student"
    print(f"-> Active Mode: {user_role.upper()}")
    
    print("\nAsk questions like: 'Who works on Federated Learning?' or 'Professor mode: IoT'")
    print("You can switch roles using: '/role student' or '/role faculty'")
    print("Type 'exit' or 'quit' to terminate the session.\n")
    
    while True:
        try:
            query = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break
            
        if not query:
            continue
        if query.lower() in ("exit", "quit", "q"):
            print("Goodbye!")
            break
            
        if query.lower().startswith("professor mode:") or query.lower().startswith("professor:"):
            # Extract topic
            prefix = "professor mode:" if query.lower().startswith("professor mode:") else "professor:"
            topic = query[len(prefix):].strip()
            if not topic:
                print("Please specify a topic, e.g., 'Professor mode: Cloud Computing'")
                continue
                
            print(f"\nRunning Professor Mode analysis & workload optimization for: '{topic}'...")
            
            try:
                from professor_mode.professor_agent import ProfessorAgent
                prof_agent = ProfessorAgent()
                report = prof_agent.run_analysis_report(topic)
                
                # Print Trend Analysis
                print("\n" + "=" * 65)
                print("  GLOBAL RESEARCH TRENDS")
                print("=" * 65)
                for i, trend in enumerate(report["trend_analysis"]["trends"], 1):
                    print(f"{i}. {trend['title']} ({trend['source'].upper()}, Confidence: {trend['confidence']:.2f})")
                    print(f"   Summary: {trend['summary']}\n")
                print("Emerging Areas: " + ", ".join(report["trend_analysis"]["emerging_areas"]))
                
                # Print Gap Analysis
                print("\n" + "=" * 65)
                print("  INSTITUTIONAL GAP ANALYSIS")
                print("=" * 65)
                print("Covered Areas: " + ", ".join(report["gap_analysis"]["covered_areas"]))
                print("Missing Areas: " + ", ".join(report["gap_analysis"]["missing_areas"]))
                print("\nOpportunity Gaps:")
                for i, gap in enumerate(report["gap_analysis"]["opportunity_gaps"], 1):
                    print(f" {i}. Gap: {gap['gap']}")
                    print(f"    Why it matters: {gap['why_it_matters']}")
                
                # Print Project Suggestions
                print("\n" + "=" * 65)
                print("  SUGGESTED COLLABORATIVE RESEARCH PROJECTS")
                print("=" * 65)
                for i, proj in enumerate(report["project_suggestions"], 1):
                    print(f"Project {i}: {proj['title']}")
                    print(f"Description: {proj['description']}")
                    print(f"Assigned Faculty: {', '.join(proj['faculty'])}")
                    print(f"Trend Alignment: {proj['trend_alignment']}")
                    print(f"Gap Alignment: {proj['gap_alignment']}")
                    print(f"Impact: {proj['impact']}")
                    
                    if proj["workload_warnings"]:
                        for warn in proj["workload_warnings"]:
                            print(f"   ⚠️ WARNING: {warn['warning']}")
                            if warn["suggested_alternatives"]:
                                print(f"   Suggested Alternatives: {', '.join(warn['suggested_alternatives'])}")
                    print("-" * 65)
                
                # CRITICAL confirmation step before action layer
                proceed = input("\nDo you want to proceed with recommendation or email generation? (yes/no): ").strip().lower()
                if proceed in ("yes", "y"):
                    try:
                        proj_choice = input(f"Enter project number to select (1-{len(report['project_suggestions'])}): ").strip()
                        choice_idx = int(proj_choice) - 1
                        if 0 <= choice_idx < len(report["project_suggestions"]):
                            selected_proj = report["project_suggestions"][choice_idx]
                            
                            # 1. Log recommendation
                            q_log_id = prof_agent.log_recommendation_to_db(topic, report, choice_idx)
                            if q_log_id != -1:
                                print("\nRecommendation successfully logged.")
                            
                            # 2. Generate email
                            print("\nGenerating email pitch draft...")
                            email_draft = prof_agent.generate_collaboration_email(selected_proj)
                            print("\n" + "=" * 65)
                            print("  COLLABORATION EMAIL DRAFT")
                            print("=" * 65)
                            print(f"Subject: {email_draft['subject']}")
                            print(f"Body:\n{email_draft['body']}")
                            print("=" * 65)

                            # 2b. Send email
                            from services.email_service import EmailService
                            recipients = [f"{fac.replace(' ', '.').lower()}@university.edu" for fac in selected_proj.get("faculty", [])]
                            if not recipients:
                                recipients = ["coordinator@university.edu"]
                            print(f"\nSending collaboration email to {', '.join(recipients)}...")
                            EmailService.send_pitch(
                                subject=email_draft["subject"],
                                body=email_draft["body"],
                                recipients=recipients
                            )
                            
                            # 3. Interactive feedback loop
                            rating_in = input("\nWould you like to rate this response? (1-5, or press Enter to skip): ").strip()
                            if rating_in:
                                try:
                                    rating = int(rating_in)
                                    comments = input("Any comments? (Optional): ").strip()
                                    prof_agent.log_feedback(q_log_id, rating, comments or None)
                                    print("Thank you for your feedback!")
                                except ValueError:
                                    print("Invalid rating skipped.")
                        else:
                            print("Invalid selection. Action cancelled.")
                    except ValueError:
                        print("Invalid input. Action cancelled.")
                else:
                    print("\nAnalysis complete. Action layer skipped.")
            except Exception as e:
                print(f"\nAn error occurred running Professor Mode: {e}")
                
            continue

        # Run query through intent router
        try:
            # Check for role switches on the fly
            if query.lower().startswith("/role "):
                new_role = query[6:].strip().lower()
                if new_role in ("student", "faculty"):
                    user_role = new_role
                    print(f"-> Active Mode changed to: {user_role.upper()}\n")
                else:
                    print("Invalid role. Select 'student' or 'faculty'.\n")
                continue

            result = chat_agent.run_query(query, role=user_role)
            intent = result["intent"]
            response_text = result["response_text"]
            data = result["data"]
            
            print(f"\nAssistant:\n{response_text}\n")
            
            # Print ChromaDB matches with distance scores if available
            if intent == "rag" and data.get("internal_matches"):
                print("ChromaDB Retrieval Match Scores (Distance):")
                for i, match in enumerate(data["internal_matches"], 1):
                    src = match["metadata"].get("source", "Unknown")
                    dist = match.get("distance", 0.0)
                    print(f"  [{i}] Source: {src} | Distance: {dist:.4f}")
                print()
            
            # CRITICAL Confirmation prompt
            confirm = input("Shall I proceed and log this recommendation? (yes/no): ").strip().lower()
            if confirm in ("yes", "y"):
                # Save to database
                query_log_id = memory.log_query(
                    query_text=query,
                    response_text=response_text,
                    mode=intent
                )
                
                if query_log_id != -1:
                    # Save context-specific data
                    if intent == "rag":
                        recs = []
                        for m in data.get("internal_matches", []):
                            recs.append({
                                "faculty_name": m["metadata"].get("source", "Unknown"),
                                "reasoning": m["document"][:200] + "...",
                                "is_fallback": data.get("is_fallback_active", False)
                            })
                        memory.log_recommendations(query_log_id, recs)
                        
                    elif intent == "collaborate":
                        memory.log_collaborations(query_log_id, [{
                            "faculty_a": data.get("faculty_a", "Unknown"),
                            "faculty_b": data.get("faculty_b", "Unknown"),
                            "synergy_reason": data.get("synergy_reason", ""),
                            "project_idea": data.get("project_idea", "")
                        }])
                        
                    elif intent == "project":
                        memory.log_projects(query_log_id, [{
                            "title": "Topic-based Project Proposal",
                            "description": data.get("project_suggestion", ""),
                            "target_faculty": data.get("topic", "")
                        }])
                        
                    print("Recommendation successfully logged.")
                    
                    # FeedBack system
                    feedback_input = input("Would you like to rate this response? (1-5, or press Enter to skip): ").strip()
                    if feedback_input.isdigit():
                        rating = int(feedback_input)
                        comments = input("Any comments? (Optional): ").strip()
                        memory.log_user_feedback(
                            query_log_id=query_log_id,
                            rating=rating,
                            comments=comments if comments else None
                        )
                        print("Thank you for your feedback!")
                    else:
                        print("Feedback skipped.")
                else:
                    print("Error: Could not record log entry.")
            else:
                print("Logging cancelled.")
                
            print("-" * 65 + "\n")
            
        except Exception as e:
            print(f"\nAn error occurred processing your query: {e}\n")

if __name__ == "__main__":
    main()
