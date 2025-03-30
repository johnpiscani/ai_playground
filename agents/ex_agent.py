from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv


load_dotenv()


# Now use gemini_api_key and gemini_api_secret wherever needed
example_agent = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
)

def run_example_agent(prompt: str):
    # Your logic here
    print("Running example agent...")
    # Example agent logic
    response = example_agent.invoke(prompt)
    return response.content

if __name__ == "__main__":
    # Example usage
    prompt = "What is the meaning of life?"
    result = run_example_agent(prompt)
    print(result)