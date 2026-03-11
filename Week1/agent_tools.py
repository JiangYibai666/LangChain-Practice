from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain.tools import tool
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from typing import List, Dict, Any
import csv
import os

load_dotenv()

# --- 1. Define Tools ---
@tool
def add(a: float, b: float) -> float:
    """Add two numbers together."""
    return a + b

@tool
def multiply(a: float, b: float) -> float:
    """Multiply two numbers together."""
    return a * b

@tool
def get_weather(city: str) -> str:
    """Get the current weather for a given city."""
    # Placeholder — replace with a real API call
    # Can use a weather API like OpenWeatherMap or WeatherAPI to get real data
    return f"The weather in {city} is sunny and 22°C."

@tool
def save_to_csv_with_path(data: List[Dict[str, Any]], file_name: str, file_path: str = ".") -> str:
    """
    Save data to a CSV file at the specified path.
    Args:
        data: A list of dictionaries representing the rows to save.
        file_name: The name of the CSV file (without extension).
        file_path: The directory path where the CSV file will be saved. Defaults to the current directory.
    """
    try:
        if not data:
            return "No data provided to save."
        full_path = os.path.join(file_path, file_name)

        directory = os.path.dirname(full_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
        
        if not full_path.endswith(".csv"):
            full_path += ".csv"
        
        fieldnames = set()
        for row in data:
            fieldnames.update(row.keys())
        fieldnames = list(fieldnames)

        with open(full_path, mode='w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for row in data:
                writer.writerow(row)
        return f"Data saved to {full_path}"
    
    except Exception as e:
        return f"An error occurred while saving to CSV: {str(e)}" 

# --- 2. Initialize the Model ---
llm = ChatAnthropic(model="claude-opus-4-5", temperature=0)

# --- 3. Create the Agent ---
tools = [add, multiply, get_weather, save_to_csv_with_path]
agent = create_agent(llm, tools)

# --- 4. Run the Agent ---
def run_agent(user_input: str):
    print(f"\nUser: {user_input}")
    result = agent.invoke({"messages": [HumanMessage(content=user_input)]})
    response = result["messages"][-1].content
    print(f"Agent: {response}")
    return response

if __name__ == "__main__":
    run_agent("What is 25 multiplied by 4?")
    run_agent("What's the weather like in Tokyo?")
    run_agent("Add 123 and 456, then tell me the result.")
    run_agent("Please save the following data to a CSV file named 'data.csv' in the 'output' directory: [{'name': 'Alice', 'age': 30}, {'name': 'Bob', 'age': 25}]")