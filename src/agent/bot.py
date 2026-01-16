# src/agent/bot.py
from openai import OpenAI
import logging
from config import Config
from agent.tools import WEATHER_TOOLS, execute_tool_call

logger = logging.getLogger(__name__)

class WeatherAgent:
    def __init__(self):
        self.client = OpenAI(api_key=Config.OPENAI_API_KEY)
        self.model = Config.OPENAI_MODEL
        self.system_prompt = """
        You are a helpful Weather Assistant. 
        1. You ONLY answer questions about weather. 
        2. If a user asks about non-weather topics (politics, sports, etc.), politely refuse.
        3. Use the provided tools to fetch real data. Do not guess.
        4. When answering, be concise and professional.
        """

    def chat(self, user_message: str) -> str:
        """
        Process a user message and return the agent's response.
        Handles the tool-calling loop automatically.
        """
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_message}
        ]

        # 1. First call to LLM
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=WEATHER_TOOLS,
            tool_choice="auto" 
        )

        response_message = response.choices[0].message

        # 2. Check if the LLM wants to run a tool
        if response_message.tool_calls:
            logger.info("Agent requested tool execution")
            
            # Append the assistant's request to conversation history
            messages.append(response_message)

            # Execute each requested tool
            for tool_call in response_message.tool_calls:
                function_name = tool_call.function.name
                arguments = tool_call.function.arguments
                
                # Run our Python code
                function_response = execute_tool_call(function_name, arguments)
                
                # Append result to conversation
                messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": function_response,
                })

            # 3. Second call to LLM (Get final answer based on tool outputs)
            final_response = self.client.chat.completions.create(
                model=self.model,
                messages=messages
            )
            return final_response.choices[0].message.content

        # If no tool was called, just return the text (e.g., for refusals)
        return response_message.content