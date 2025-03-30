# Fantasy Swarm Planning

1. Tasks to be done:
- Fetch league data: Standings, current week, playoff teams, etc.
- Retrieve rosters: For each team or owner.
- Get player statistics: Weekly points, matchups, injury status.
- Fetch player news: Latest articles, expert analysis, injury updates.
- Evaluate trades and waiver wire picks: Determine best available players.

2. Extend Your Agent Classes for Specific Tasks
Using your BaseAgent and ToolAgent:
- BaseAgent: Use this for simpler tasks where you only need to generate a response from your language model.
- ToolAgent: Use this when you need the agent to invoke one or more tools (API calls) as part of its reasoning process.

For example, you might create:
- RosterAgent: Uses a tool that retrieves a team’s roster.
- NewsAgent: Uses a tool function (like get_player_news) to fetch the latest news.
- StatsAgent: Uses a tool to get historical and current player statistics.
- TradeAnalyzerAgent: Combines data from multiple sources (rosters, stats, news) to recommend trades.

Each agent’s run() method will:
- Build a prompt using your custom prompt template (which might include placeholders like {user_input}).
- Invoke the LLM (or agent executor in the case of ToolAgent) to process that prompt.
- Update the shared SwarmState with its output.
- Decide which agent should run next (using your determine_next logic).

3. Orchestrate the Workflow with Your Custom Swarm
Planning Agent (_planner_agent):
Your custom swarm class already includes a planner agent that, given the user’s initial input, returns a JSON object listing the order in which your agents should execute.

Use this planner to decide the sequence of specialized agents based on what the user wants (for instance, if the query is “Who should I trade for Saquon Barkley?” the planner might return ["NewsAgent", "StatsAgent", "TradeAnalyzerAgent"]).
Graph Construction:

In your CustomSwarm.build_graph() method, add nodes for each of your specialized agents.
The graph will start at the planner, then follow the order provided in state["agents_order"]. As each agent runs, it updates the state with its results.
Swarm Invocation:

You’ll call CustomSwarm.invoke(initial_state) with an initial state that includes the user’s query.
As the graph executes, each agent’s output is accumulated in state["agent_responses"]. When no further agents are scheduled (i.e. goto equals END), you have the full set of responses.

4. Integrate Additional Enhancements
Caching API Responses:

To reduce latency and API load (as described in the Medium article), integrate caching into your tool functions. For example, you might use a caching library (like requests-cache) to store and reuse recent API responses.
User Interface (Optional):

Although your custom classes manage the backend orchestration, you can build a simple UI (using Streamlit, for example) to allow users to input their fantasy football queries and view both the final summary and detailed agent responses.
A “research pane” can display raw tool outputs for transparency and debugging.