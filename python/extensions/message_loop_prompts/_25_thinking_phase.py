from python.helpers.extension import Extension
from agent import Agent, LoopData
from python.helpers.print_style import PrintStyle
from typing import List
import asyncio
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage, HumanMessage
from python.helpers.dirty_json import DirtyJson

class ThinkingPhaseExtension(Extension):

    async def execute(self, loop_data: LoopData = LoopData(), **kwargs):
        await self.think_through_message(loop_data)

    async def think_through_message(self, loop_data: LoopData):
        thinking_duration = 10.0  # Duration in seconds (5 minutes)
        message = loop_data.message

        # Initialize thoughts with the original problem
        thoughts: List[HumanMessage] = [
            HumanMessage(content=f"Original Problem:\n{message}\n\nInitial Analysis:")
        ]

        thinking_prompt = """You are solving the following specific problem:

{original_problem}

Current chain of thoughts:
{thoughts}

Continue analyzing this exact problem. Build upon the previous thoughts to deepen the analysis.
Think deeply about various aspects of this task, considering:
- Different approaches and their trade-offs
- Potential challenges and solutions
- Related concepts and how they apply
- Step-by-step planning
- Edge cases and error handling

Stay focused on this specific problem. Do not deviate to other topics."""

        start_time = asyncio.get_event_loop().time()
        buffer = ""  # Initialize buffer for accumulating content

        while (asyncio.get_event_loop().time() - start_time) < thinking_duration:
            try:
                prompt = ChatPromptTemplate.from_messages([
                    SystemMessage(content=thinking_prompt),
                    MessagesPlaceholder(variable_name="thoughts")
                ])

                chain = prompt | self.agent.config.chat_model

                # Stream thoughts while maintaining problem context
                async for chunk in chain.astream({
                    "thoughts": thoughts,
                    "original_problem": message
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
                                # Add structured prefix to show thinking progress
                                timestamp = int(asyncio.get_event_loop().time() - start_time)
                                thought_entry = f"[{timestamp}s] {buffer.strip()}"

                                thoughts.append(HumanMessage(content=thought_entry))

                                # Log thinking progress with clear formatting
                                PrintStyle(
                                    italic=True,
                                    font_color="#b3b3ff",
                                    padding=False
                                ).print(f"Thinking ({timestamp}s): {buffer.strip()}")

                                # Add to agent's log for record keeping
                                self.agent.context.log.log(
                                    type="thinking",
                                    content=thought_entry
                                )

                                buffer = ""  # Reset buffer after logging
            except Exception as e:
                self.agent.context.log.log(
                    type="warning",
                    content=f"Thinking phase error: {str(e)}"
                )

        # Handle any remaining buffer content
        if buffer.strip():
            timestamp = int(asyncio.get_event_loop().time() - start_time)
            thought_entry = f"[{timestamp}s] {buffer.strip()}"

            thoughts.append(HumanMessage(content=thought_entry))

            PrintStyle(
                italic=True,
                font_color="#b3b3ff",
                padding=False
            ).print(f"Thinking ({timestamp}s): {buffer.strip()}")

            self.agent.context.log.log(
                type="thinking",
                content=thought_entry
            )

        # Synthesize thoughts with problem context
        synthesis_prompt = """You have spent time analyzing this problem:

{original_problem}

You have spent time thinking about the task through this chain of thoughts:

{thoughts}

Synthesize these thoughts into a clear, actionable conclusion that will guide your next steps.
Focus on:
1. Key insights gained
2. Chosen approach and rationale
3. Critical considerations
4. Next concrete steps"""

        original_problem_str = str(message)
        thoughts_str = "\n".join([str(t.content) for t in thoughts])

        final_thought = await self.agent.call_utility_llm(
            system="Synthesize the thinking process into a final conclusion for this specific problem.",
            msg=synthesis_prompt.format(
                original_problem=original_problem_str,
                thoughts=thoughts_str
            )
        )

        # Log the final synthesized thought
        self.agent.context.log.log(
            type="synthesis",
            content=final_thought
        )

        # Store the final thought in the agent's data for later use
        self.agent.data["thought_process"] = final_thought

        # Add the prior thought process as the last system prompt
        if final_thought:  # Use thought_result instead of thought_process
            thought_prompt = self.agent.read_prompt(
                'fw.include_thought_process.md', 
                thought_process=final_thought
            )
