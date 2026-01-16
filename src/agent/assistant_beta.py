# src/agent/assistant_beta.py
import time
import json
import logging
from openai import OpenAI

# Absolute imports
from config import Config
from agent.tools import WEATHER_TOOLS, execute_tool_call

logger = logging.getLogger(__name__)

class BetaWeatherAgent:
    """
    Alternative implementation using the OpenAI Assistants API (Beta).
    This manages state via Threads rather than managing history manually.
    """
    def __init__(self):
        self.client = OpenAI(api_key=Config.OPENAI_API_KEY)
        self.model = Config.OPENAI_MODEL
        
        # In a real app, you might load this ID from env to avoid recreating it
        self.assistant = self._get_or_create_assistant()

    def _get_or_create_assistant(self):
        """Create a new assistant with our tools"""
        logger.info("Initializing OpenAI Assistant (Beta)...")
        return self.client.beta.assistants.create(
            name="Weather Bot Beta",
            instructions="""
            You are a helpful Weather Assistant. 
            1. You ONLY answer questions about weather. 
            2. If a user asks about non-weather topics, politely refuse.
            3. Use the provided tools to fetch real data.
            """,
            tools=WEATHER_TOOLS,
            model=self.model
        )

    def chat(self, user_message: str) -> str:
        """
        Full cycle: Create Thread -> Add Message -> Run -> Poll -> Tool Output -> Response
        """
        # 1. Create a Thread (Stateful conversation container)
        thread = self.client.beta.threads.create()
        
        # 2. Add the user's message
        self.client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=user_message
        )

        # 3. Run the Assistant on the Thread
        run = self.client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=self.assistant.id
        )

        # 4. Polling Loop
        # The Assistants API is asynchronous, so we must poll for completion
        while True:
            # Refresh run status
            run_status = self.client.beta.threads.runs.retrieve(
                thread_id=thread.id,
                run_id=run.id
            )
            
            logger.info(f"Run status: {run_status.status}")

            if run_status.status == 'completed':
                # Fetch the latest message from the assistant
                messages = self.client.beta.threads.messages.list(
                    thread_id=thread.id
                )
                # Return the most recent text response
                return messages.data[0].content[0].text.value
            
            elif run_status.status == 'requires_action':
                logger.info("Assistant requires tool execution...")
                tool_outputs = []
                
                # Iterate through all requested tool calls
                for tool_call in run_status.required_action.submit_tool_outputs.tool_calls:
                    function_name = tool_call.function.name
                    arguments = tool_call.function.arguments
                    
                    # Execute our existing Python code
                    result = execute_tool_call(function_name, arguments)
                    
                    tool_outputs.append({
                        "tool_call_id": tool_call.id,
                        "output": result
                    })
                
                # Submit outputs back to OpenAI to continue execution
                self.client.beta.threads.runs.submit_tool_outputs(
                    thread_id=thread.id,
                    run_id=run.id,
                    tool_outputs=tool_outputs
                )
            
            elif run_status.status in ['failed', 'cancelled', 'expired']:
                logger.error(f"Run failed: {run_status.last_error}")
                return "I encountered an error processing your request."
            
            # Wait a bit before polling again
            time.sleep(1)