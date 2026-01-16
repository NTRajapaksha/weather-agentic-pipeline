# test_beta.py
import logging
from src.config import Config
from src.config import setup_logging
from src.agent.assistant_beta import BetaWeatherAgent

# Setup logging to see the "polling" logs
setup_logging()

def test_beta_agent():
    print("\n--- Initializing Beta Agent (Assistants API) ---")
    try:
        agent = BetaWeatherAgent()
        
        print("\n--- Sending Query: Weather in London ---")
        # This will create a thread, run it, and poll for the answer
        response = agent.chat("What is the current weather in London?")
        
        print(f"\n[FINAL RESPONSE]: {response}")
        
    except Exception as e:
        print(f"\n[ERROR]: {e}")

if __name__ == "__main__":
    test_beta_agent()