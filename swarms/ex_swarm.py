from ai_playground.agents.base_agents import ToolAgent, BaseAgent, CustomSwarm, SwarmState
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from langgraph.types import Command
import time

load_dotenv()

# Now use gemini_api_key and gemini_api_secret wherever needed
model = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
)

def writer_agent(state: SwarmState) -> Command:
    """Writer agent using BaseAgent to simplify prompt invocation."""
    print("Start Writer Agent")
    prompt_template = (
        "You are an email writing assistant. You will write a professional email based on the following requirements:\n"
        "{user_input}\n\n"
        "Please provide:\n"
        "1. A clear subject line\n"
        "2. Professional email body\n"
        "3. Appropriate greeting and closing\n"
        "4. Any necessary formatting for clarity\n\n"
        "Return the email in proper format, maintaining a professional tone and business etiquette.\n"
        "Do not add any additional text before or after the email response."
    )
    agent = BaseAgent("writer_agent", model, prompt_template)
    return agent.run(state)

def revisor_agent(state: SwarmState) -> Command:
    """Revisor agent which refines the writer's response."""
    print("Start Revisor Agent")
    writer_response = state['agent_responses'].get('writer_agent')
    if not writer_response:
        print("No writer response available, falling back to planner_agent.")
        return Command(update=state, goto="planner_agent")
    
    prompt_template = (
        "You are an email revision assistant. Review and improve the following email while considering the original requirements:\n\n"
        "Original Requirements:\n{user_input}\n\n"
        "Email to Review:\n{agent_responses[writer_agent]}\n\n"
        "Please:\n"
        "1. Check for grammatical and spelling errors\n"
        "2. Improve clarity and conciseness\n"
        "3. Ensure professional tone and business etiquette\n"
        "4. Enhance formatting if needed\n"
        "5. Verify all required information is included\n"
        "6. Maintain or improve the overall message effectiveness\n\n"
        "Return the revised email in the same format as the original, with all improvements applied.\n"
        "Do not add any additional text before or after the email response."
    )
    agent = BaseAgent("revisor_agent", model, prompt_template)
    return agent.run(state)


def main():
    # Create a dictionary of agents (excluding the planner; planner is embedded in CustomSwarm)
    base_agents = {
        "writer_agent": writer_agent,
        "revisor_agent": revisor_agent
    }
    
    # Define available agent names that the planner should use.
    available_agents = list(base_agents.keys())
    
    # Instantiate the CustomSwarm with available_agents and base_agents.
    swarm = CustomSwarm(base_agents=base_agents, available_agents=available_agents)
    
    user_input = "Create an email to schedule a meeting with a potential investor from Investors Global, Jesus Santana"
    input_state = {
        "user_input": user_input,
        "agents_order": [],
        "agent_responses": {},
        "error": False
    }
    
    start_time = time.time()
    result_state = swarm.invoke(input_state)
    print(f"Time taken: {time.time() - start_time:.2f} seconds")
    print("Responses from agents:", list(result_state.get("agent_responses", {}).keys()))
    print("Final email (revised):", result_state.get("agent_responses", {}).get('revisor_agent', "No final email produced."))

if __name__ == "__main__":
    main()