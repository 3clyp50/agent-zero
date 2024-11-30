from python.helpers.extension import Extension
from agent import Agent, LoopData
from python.helpers.print_style import PrintStyle
from typing import List
import asyncio
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage, HumanMessage
from python.helpers.dirty_json import DirtyJson
from python.helpers import settings
import json

class ThinkingPhaseExtension(Extension):

    async def show_progress(self, stage_message: str):
        """Display the current thinking stage in both progress bar and CLI."""
        # Show in CLI
        PrintStyle(
            italic=True,
            font_color="#b3b3ff",
            padding=True
        ).print(f"{stage_message}")
        
        # Show in progress bar
        log_item = self.agent.context.log.log(
            type="util",
            heading=stage_message
        )
        return log_item

    async def execute(self, loop_data: LoopData = LoopData(), **kwargs):
        # Reset execution phase at the start
        self.agent.data["execution_phase"] = False
        
        # Get the current message
        current_message = loop_data.user_message
        
        # Get settings
        current_settings = settings.get_settings()
        thinking_trigger_type = current_settings.get("thinking_trigger_type", "enabled")
        
        # Check if thinking is disabled
        if thinking_trigger_type == "disabled":
            return
            
        # Proceed with thinking phase if conditions are met
        if (current_message and 
            not self.agent.data.get("execution_phase", False) and
            not getattr(current_message, 'is_system_message', False) and
            not getattr(current_message, 'ai', False) and  # User message only
            not getattr(current_message, 'tool_result', False) and  # Not a tool result
            not hasattr(current_message, 'thinking_processed')):  # Haven't processed this message
            
            # Mark this message as processed to prevent redundant thinking
            setattr(current_message, 'thinking_processed', True)
            
            # Get thinking duration from settings
            thinking_duration = current_settings["thinking_duration"]
            
            # Format duration message consistently
            duration_text = f"{int(thinking_duration)} seconds" if thinking_duration < 60 else f"{thinking_duration/60:.1f} minutes"
            
            # Show initial reasoning message in progress bar only
            self.agent.context.log.log(
                type="util",
                heading=f"Reasoning for {duration_text}...",
                content=""
            )
            
            # Process thoughts with dynamic stages
            await self.think_through_message(loop_data)
            
            # After thinking phase completes, set execution phase
            self.agent.data["execution_phase"] = True
            
            # Get the accumulated thoughts and plan
            plan = self.agent.data.get("current_execution_plan", {})
            thought_process = self.agent.data.get("thought_process", "")
            accumulated_thoughts = self.agent.data.get("accumulated_thoughts", [])
            
            analysis_context = f"""
IMPORTANT - Your Previous Analysis:

THOUGHT PROCESS:
{thought_process}

ACCUMULATED THOUGHTS:
{json.dumps(accumulated_thoughts, indent=2)}

EXECUTION PLAN:
{json.dumps(plan, indent=2)}

CRITICAL INSTRUCTIONS:
1. You MUST use the insights from your prior analysis above
2. Your response MUST directly address the conclusions from your thought process
3. DO NOT create new analysis - use your existing insights
4. Ensure your response reflects the depth of your previous thinking
5. Follow the execution plan while incorporating your analytical insights

RESPONSE FORMAT:
1. Start with a summary of key insights from your analysis
2. Explain how these insights inform your approach
3. Present the solution with clear connection to your analysis
4. Address any important considerations or edge cases identified

Remember: Your previous thinking contains valuable insights that MUST be reflected in your response.
"""
            # Include the thought process template
            thought_process_template = self.agent.read_prompt(
                'fw.include_thought_process.md',
                thought_process=thought_process,
                key_insights=json.dumps(plan.get("key_insights", []), indent=2)
            )
            
            # Add the analysis context and thought process as SEPARATE system messages
            # This ensures they're both properly considered
            loop_data.system.append(analysis_context)
            loop_data.system.append(thought_process_template)
            
            # Add a final reminder to enforce thought process inclusion
            final_reminder = """
CRITICAL: Your response MUST explicitly incorporate:
1. The insights from your prior analysis
2. The key conclusions from your thought process
3. The specific considerations you identified

DO NOT generate a response without referencing your prior analysis.
"""
            loop_data.system.append(final_reminder)

    async def think_through_message(self, loop_data: LoopData):
        # Get thinking duration from settings
        thinking_duration = settings.get_settings()["thinking_duration"]
        message = loop_data.user_message.output_text() if loop_data.user_message else ""

        # Format duration message
        duration_text = f"{int(thinking_duration)} seconds" if thinking_duration < 60 else f"{thinking_duration/60:.1f} minutes"
        
        # Show initial thinking message
        await self.show_progress(f"Reasoning for {duration_text}...")

        # Initialize thoughts with the original problem
        thoughts: List[HumanMessage] = [
            HumanMessage(content=f"Original Problem:\n{message}\n\nInitial Analysis:")
        ]
        accumulated_thoughts = []  # Keep track of all thoughts

        # Get thinking prompts from prompt system
        thinking_prompt = self.agent.read_prompt(
            'thinking.phase.prompt.md',
            original_problem="{original_problem}",
            thoughts="{thoughts}",
            system_prompt="{system_prompt}",
            tools_prompt="{tools_prompt}"
        ).replace("AVAILABLE TOOLS:", "AVAILABLE TOOLS:\n{tools_prompt}")

        start_time = asyncio.get_event_loop().time()
        buffer = ""  # Initialize buffer for accumulating content
        current_stage = ""  # Track current thinking stage

        # Get system and tools prompts once before the loop
        system_prompt_str = self.agent.read_prompt("agent.system.main.md")
        tools_prompt_str = self.agent.read_prompt("agent.system.tools.md")

        while (asyncio.get_event_loop().time() - start_time) < thinking_duration:
            try:
                # Determine next stage based on accumulated thoughts
                if not current_stage:
                    stage_prompt = f"""Based on the current analysis state, determine the immediate next thinking stage.
Return only a single line ending with "..." that describes what the Agent is currently thinking about.

Current thoughts:
{json.dumps(accumulated_thoughts, indent=2)}

User's question: {message}

Example stages:
- "Understanding the core requirements..."
- "Analyzing potential approaches..."
- "Evaluating technical considerations..."
- "Identifying edge cases..."
- "Reviewing previous analysis..."
- "Revisiting key insights..."
- "Synthesizing solution approach..."

Return the next appropriate stage:"""
                    
                    current_stage = (await self.agent.call_utility_llm(system=stage_prompt, msg="")).strip()
                    await self.show_progress(current_stage)

                prompt = ChatPromptTemplate.from_messages([
                    SystemMessage(content=thinking_prompt),
                    MessagesPlaceholder(variable_name="thoughts")
                ])

                chain = prompt | self.agent.config.chat_model

                # Stream thoughts while maintaining problem context
                async for chunk in chain.astream({
                    "thoughts": thoughts,
                    "original_problem": message,
                    "system_prompt": system_prompt_str,
                    "tools_prompt": tools_prompt_str
                }):
                    await self.agent.handle_intervention()

                    if isinstance(chunk, str):
                        content = chunk
                    elif hasattr(chunk, "content"):
                        content = str(chunk.content)
                    else:
                        content = str(chunk)

                    if content:
                        buffer += content  # Append to buffer

                        # Check if the content ends with sentence-ending punctuation
                        if content.strip().endswith(('.', '!', '?')):
                            if buffer.strip():  # Ensure buffer is not empty
                                formatted_thought = buffer.strip()
                                
                                thoughts.append(HumanMessage(content=formatted_thought))
                                accumulated_thoughts.append(formatted_thought)

                                # Log thinking progress only to CLI
                                PrintStyle(
                                    italic=True,
                                    font_color="#b3b3ff",
                                    padding=False
                                ).print(formatted_thought)

                                # Clear stage and buffer after significant thought
                                current_stage = ""
                                buffer = ""

            except Exception as e:
                self.agent.context.log.log(
                    type="warning",
                    content=f"Thinking phase error: {str(e)}"
                )

        # Handle any remaining buffer content
        if buffer.strip():
            formatted_thought = buffer.strip()
            
            thoughts.append(HumanMessage(content=formatted_thought))
            accumulated_thoughts.append(formatted_thought)

            PrintStyle(
                italic=True,
                font_color="#b3b3ff",
                padding=False
            ).print(formatted_thought)

        # Show final stage
        await self.show_progress("Synthesizing final thoughts...")

        # Show accumulated thoughts
        if accumulated_thoughts:
            self.agent.context.log.log(
                type="agent",
                heading="Thought Process",
                content="",
                kvps={
                    "thoughts": accumulated_thoughts
                }
            )

        # Create a structured plan from the accumulated thoughts
        try:
            # Extract key insights and action plan from the last few thoughts
            final_thoughts = accumulated_thoughts[-3:] if accumulated_thoughts else []
            
            plan = {
                "key_insights": final_thoughts,
                "analysis": "\n".join(final_thoughts),
                "thoughts": accumulated_thoughts,
                "response_requirements": [
                    "Incorporate key insights from analysis",
                    "Reference specific thoughts from thinking phase",
                    "Connect solution to identified considerations"
                ],
                "tool_sequence": []
            }
        except:
            # Fallback plan if extraction fails
            plan = {
                "key_insights": accumulated_thoughts[-3:] if accumulated_thoughts else [],
                "analysis": "\n".join(accumulated_thoughts),
                "thoughts": accumulated_thoughts,
                "response_requirements": [
                    "Incorporate key insights from analysis",
                    "Reference specific thoughts from thinking phase",
                    "Connect solution to identified considerations"
                ],
                "tool_sequence": []
            }

        # Add the thought process to the agent's history
        await self.agent.hist_add_ai_response(json.dumps(plan, indent=2))

        # Get execution prompt from prompt system and structure it for strict adherence
        execution_prompt = self.agent.read_prompt(
            'thinking.phase.execution.md',
            plan=json.dumps(plan, indent=2)
        )
        
        # Store the plan and execution prompt in the agent's data for direct access
        self.agent.data["thought_process"] = "\n".join(accumulated_thoughts)
        self.agent.data["accumulated_thoughts"] = accumulated_thoughts
        self.agent.data["current_execution_plan"] = plan
        self.agent.data["execution_phase"] = True
        
        # Add execution context to system messages for next iteration
        execution_context = f"""
IMPORTANT: You are in the execution phase. You MUST follow this exact plan:
{json.dumps(plan, indent=2)}

DO NOT create a new plan or analysis. Execute the above plan precisely.
Follow the tool sequence and response structure defined in the plan.
"""
        loop_data.system.append(execution_context)
        loop_data.system.append(execution_prompt)
