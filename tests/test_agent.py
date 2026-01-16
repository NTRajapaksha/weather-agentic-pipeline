# test_agent.py
import logging
from src.config import setup_logging
from src.agent.bot import WeatherAgent

# Setup logging so we can see tool execution
setup_logging()

def test_queries():
    agent = WeatherAgent()
    
    print("\n--- Test 1: Simple Weather Query ---")
    response = agent.chat("What is the current weather in Tokyo?")
    print(f"Agent: {response}")

    print("\n--- Test 2: Historical Query ---")
    response = agent.chat("What was the temperature trend in London over the last 3 days?")
    print(f"Agent: {response}")

    print("\n--- Test 3: Guardrail Check (Non-weather) ---")
    response = agent.chat("Who won the last cricket world cup?")
    print(f"Agent: {response}")

if __name__ == "__main__":
    test_queries()