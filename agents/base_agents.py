import json
from typing import Callable, Dict, List, TypedDict
from langchain.agents import initialize_agent, AgentType
from langgraph.types import Command
from langgraph.graph import START, END, StateGraph
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

load_dotenv()

model = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
)
small_model = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash-8b",
)


class SwarmState(TypedDict):
    user_input: str
    agents_order: list
    agent_responses: dict
    error: bool

class BaseAgent:
    """Base Agent."""

    def __init__(self, agent_name: str, model, prompt_template: str):
        """Initialize Base Agent.

        agent_name: Unique name for the agent (e.g., 'writer_agent')
        model: The LLM model instance to invoke.
        prompt_template: A format string for the prompt. It can include placeholders like {user_input}
        """
        self.agent_name = agent_name
        self.model = model
        self.prompt_template = prompt_template

    def build_prompt(self, state: SwarmState) -> str:
        """Build the prompt using the state."""
        return self.prompt_template.format(**state)

    def invoke_llm(self, prompt: str) -> str:
        """Invoke the LLM with the prompt and handle exceptions."""
        try:
            response = self.model.invoke(prompt)
            output = response.content.strip()
            return output
        except Exception as e:
            print(f"Error in {self.agent_name}: {e}")
            return None

    def update_state(self, state: SwarmState, output: str) -> None:
        """Update the state with the agent's output."""
        state["agent_responses"][self.agent_name] = output

    def determine_next(self, state: SwarmState, output: str) -> str:
        """Determine the next agent (or fallback) based on the output and remaining agents_order."""
        if not output:
            print(f"{self.agent_name} produced no valid output, falling back to planner_agent.")
            return "planner_agent"
        if state["agents_order"]:
            return state["agents_order"].pop(0)
        return END

    def run(self, state: SwarmState) -> Command:
        """Run the agent: build prompt, invoke LLM, update state, and decide the next node."""
        prompt = self.build_prompt(state)
        print(f"Agent {self.agent_name} prompt:\n{prompt}\n")
        output = self.invoke_llm(prompt)
        self.update_state(state, output)
        goto = self.determine_next(state, output)
        return Command(update=state, goto=goto)


class ToolAgent(BaseAgent):
    """
    ToolAgent extends BaseAgent to use an agent executor that supports tool calls.
    
    This agent class accepts a list of tools during initialization. When run,
    it builds the prompt from the current swarm state (using the prompt template),
    then creates an agent executor using the provided LLM and tools with the
    STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION agent type.
    
    The run() method invokes the executor with the generated prompt, updates the 
    swarm state with the LLM’s output, and determines the next agent to run.
    
    Args:
        agent_name (str): Unique name for the agent (e.g., 'writer_agent').
        model: The LLM model instance to invoke.
        prompt_template (str): A format string for the prompt, with placeholders for state.
        tools (list): A list of tools (functions decorated with @tool) that the agent can invoke.
    
    Methods:
        build_prompt(state: SwarmState) -> str:
            Build the prompt from the state using the prompt_template.
        invoke_llm(prompt: str) -> str:
            (Inherited from BaseAgent) Invoke the LLM; in this case, via the agent executor.
        update_state(state: SwarmState, output: str) -> None:
            (Inherited) Update the state with the agent's output.
        determine_next(state: SwarmState, output: str) -> str:
            (Inherited) Decide which agent should run next.
        run(state: SwarmState) -> Command:
            Build the prompt, invoke the executor (with tools) using the prompt,
            update the state with the output, and return a Command with the updated state and next agent.
    """
    
    def __init__(self, agent_name: str, model, prompt_template: str, tools: list):
        super().__init__(agent_name, model, prompt_template)
        self.tools = tools
        # Pre-initialize the executor with the tools.
        self.executor = initialize_agent(
            tools,
            model,
            agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True,
        )

    def run(self, state: dict) -> 'Command':
        """
        Run the tool-enabled agent:
        
        1. Build the prompt using the current state.
        2. Use the agent executor (which has the provided tools) to generate a response.
        3. Update the swarm state with the agent's output.
        4. Determine the next agent based on the output.
        
        Args:
            state (dict): The current state of the swarm, including any placeholders needed by the prompt_template.
        
        Returns:
            Command: A command object containing the updated state and the identifier of the next agent (or END).
        """
        prompt = self.build_prompt(state)
        print(f"Agent {self.agent_name} prompt:\n{prompt}\n")
        # Use the executor to run the prompt (this internally handles tool invocation)
        output = self.executor.run(prompt)
        self.update_state(state, output)
        goto = self.determine_next(state, output)
        return Command(update=state, goto=goto)

class CustomSwarm:
    def __init__(self, base_agents: Dict[str, Callable[[SwarmState], Command]], available_agents: List[str]):
        """
        base_agents: a dictionary mapping agent names (str) to agent functions (taking SwarmState and returning Command).
        available_agents: list of agent names (str) that the planner will use.
        """
        self.base_agents = base_agents
        self.available_agents = available_agents
        self.graph = self.build_graph()

    def _planner_agent(self, state: SwarmState) -> Command:
        """Planner Agent method embedded in the swarm class."""
        print("Start Planner Agent")
        user_input = state['user_input']
        # Use the available_agents list passed during initialization.
        prompt = f"""
        You will plan out which agents should be invoked, and in which order.
        You have the following agents you can use:
        {self.available_agents}

        Instructions:
        Create an order that the agents should run in based on the user's input.
        This is the user input:
        {user_input}

        Output format:
        {{
            "agents_order": [agent_1_name, agent_2_name, ...]
        }}
        Return ONLY the JSON!
        """
        try:
            response = small_model.invoke(prompt)
            print(response)
            try:
                json_response = json.loads(response.content)
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON: {e}")
                # extract json surrounded by ```json {} ```
                json_start = response.content.find("```json")
                if json_start != -1:
                    json_end = response.content.find("```", json_start + 1)
                    if json_end != -1:
                        json_response = json.loads(response.content[json_start + 7:json_end])
                        
            agents_order = json_response.get('agents_order', [])
        except Exception as e:
            print(f"Error in planner_agent: {e}")
            state['error'] = True
            return Command(update=state, goto=END)

        if not agents_order:
            print("No agents planned, ending execution.")
            return Command(update=state, goto=END)
        
        goto = agents_order.pop(0)
        state['agents_order'] = agents_order
        return Command(update=state, goto=goto)

    def build_graph(self):
        """Construct the state graph using the embedded planner and the provided agents."""
        builder = StateGraph(SwarmState)
        # Add planner as the starting node.
        builder.add_edge(START, "planner_agent")
        builder.add_node("planner_agent", self._planner_agent)
        # Add all other agents.
        for agent_name, agent_func in self.base_agents.items():
            builder.add_node(agent_name, agent_func)
        graph = builder.compile()
        return graph

    def invoke(self, input_state: SwarmState) -> SwarmState:
        """Invoke the swarm with the given initial state."""
        return self.graph.invoke(input_state)