from python.helpers.extension import Extension
from agent import Agent, LoopData
from python.helpers.print_style import PrintStyle
from typing import List, Dict, Any, Optional
import asyncio
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from python.helpers.dirty_json import DirtyJson
from python.helpers import settings
import json
import traceback

class ThinkingPhaseExtension(Extension):

    async def show_progress(self, stage_message: str):
        """Display the current thinking stage in CLI and progress bar."""
        # Show in CLI with proper formatting
        PrintStyle(
            italic=True,
            font_color="#b3b3ff",
            padding=True
        ).print(f"{stage_message}")
        
        # Log as utility message and update progress bar
        log_item = self.agent.context.log.log(
            type="util",
            heading=stage_message,
            content=""
        )
        if log_item:
            log_item.stream(progress=stage_message)

    async def show_thought(self, thought: str, stage: str):
        """Display a thought as an Agent message with kvps."""
        # Get current planning context
        planning_context = self.agent.data.get("planning_context", {})
        
        # Debug logging
        print(f"\nDEBUG: Showing thought")
        print(f"Stage: {stage}")
        print(f"Thought: {thought}")
        print(f"Planning Context: {json.dumps(planning_context, indent=2)}")
        
        # Show in agent log with kvps, keeping dynamic stage in heading
        log_item = self.agent.context.log.log(
            type="agent",
            heading=stage.strip() if stage else "Planning...",
            content=thought,
            kvps={
                "Key Considerations": "\n".join(planning_context.get("key_points", [])) or "None yet",
                "Plan Evolution": f"{len(planning_context.get('thought_evolution', []))} iterations",
                "Critical Decisions": "\n".join(planning_context.get("decision_points", [])) or "None yet",
                "Current Analysis": planning_context.get("current_focus", "Initial planning")
            }
        )
        
        # Debug logging for log item
        if log_item:
            print(f"Log item created successfully")
        else:
            print(f"WARNING: Failed to create log item")

    async def execute(self, loop_data: LoopData = LoopData(), **kwargs):
        # Reset execution phase at the start
        self.agent.data["execution_phase"] = False
        
        # Get the current message
        current_message = loop_data.user_message
        
        # Get settings
        current_settings = settings.get_settings()
        thinking_trigger_type = current_settings.get("thinking_trigger_type", "enabled")
        thinking_duration = current_settings["thinking_duration"]
        
        # Debug logging for settings
        print(f"\nDEBUG: Thinking Phase Settings")
        print(f"Trigger Type: {thinking_trigger_type}")
        print(f"Duration: {thinking_duration}")
        
        # Check if thinking is disabled
        if thinking_trigger_type == "disabled":
            print("DEBUG: Thinking phase is disabled")
            return
            
        # Debug logging for message
        print(f"\nDEBUG: Message Info")
        print(f"Has message: {bool(current_message)}")
        print(f"Is system message: {getattr(current_message, 'is_system_message', False)}")
        print(f"Is AI message: {getattr(current_message, 'ai', False)}")
        print(f"Is tool result: {getattr(current_message, 'tool_result', False)}")
        print(f"Already processed: {hasattr(current_message, 'thinking_processed')}")
        
        # Proceed with thinking phase if conditions are met
        if (current_message and 
            not self.agent.data.get("execution_phase", False) and
            not getattr(current_message, 'is_system_message', False) and
            not getattr(current_message, 'ai', False) and  # User message only
            not getattr(current_message, 'tool_result', False) and  # Not a tool result
            not hasattr(current_message, 'thinking_processed')):  # Haven't processed this message
            
            print("\nDEBUG: Starting thinking phase")
            
            # Mark this message as processed to prevent redundant thinking
            setattr(current_message, 'thinking_processed', True)
            
            # Process thoughts with dynamic stages
            plan = await self.think_through_message(loop_data, thinking_duration)
            validated_plan = await self.validate_plan(plan)
            await self.prepare_execution_phase(validated_plan, loop_data)
            
            print("\nDEBUG: Completed thinking phase")
            
            # After thinking phase completes, set execution phase
            self.agent.data["execution_phase"] = True
        else:
            print("\nDEBUG: Skipping thinking phase - conditions not met")

    async def think_through_message(self, loop_data: LoopData, thinking_duration: float) -> str:
        """Generate solution plan through iterative thinking and refinement."""
        message = loop_data.user_message.output_text() if loop_data.user_message else ""
        
        # Show initial planning message
        duration_text = f"{int(thinking_duration)} seconds" if thinking_duration < 60 else f"{thinking_duration/60:.1f} minutes"
        await self.show_progress(f"Planning solution approach for {duration_text}...")
        
        # Initialize planning context
        planning_context = {
            "key_points": [],
            "thought_evolution": [],
            "decision_points": [],
            "current_focus": "Initial planning"
        }
        self.agent.data["planning_context"] = planning_context
        
        # Get system and tools prompts
        system_prompt_str = await self._get_system_prompt()
        tools_prompt_str = await self._get_tools_prompt()
        
        # Load the thinking phase prompt
        thinking_prompt = self.agent.read_prompt('thinking.phase.prompt.md').format(
            original_problem=message,
            system_prompt=system_prompt_str,
            tools_prompt=tools_prompt_str
        )
        
        # Initialize for thought collection
        thoughts: List[str] = []
        start_time = asyncio.get_event_loop().time()
        
        # Create the planning prompt
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=thinking_prompt),
            HumanMessage(content=f"""Problem to Solve:\n{message}\n\nInitial Analysis:
            
You are Agent Zero, analyzing this problem step by step. Express your thoughts naturally:

IMPORTANT: Format your response as plain text, not JSON. Do not include any tool calls or JSON structure.

For each thought:
1. Start with "Let me think about..." or similar agent-like phrases
2. Use first person perspective ("I think...", "I see...", "I need to...")
3. Explain your reasoning naturally
4. If something is particularly important, start with "IMPORTANT:"
5. When making decisions, explain your choice clearly

Consider:
1. Problem understanding and requirements
2. Potential approaches and trade-offs
3. Implementation strategy and steps
4. Possible challenges and solutions
5. Success criteria""")
        ])
        
        while (asyncio.get_event_loop().time() - start_time) < thinking_duration:
            try:
                # Generate complete thought
                buffer = ""
                async for chunk in self.agent.config.chat_model.astream(prompt.format_messages()):
                    if isinstance(chunk, AIMessage):
                        content = chunk.content if isinstance(chunk.content, str) else str(chunk.content)
                    else:
                        content = str(chunk)
                    
                    if content:
                        buffer += content
                
                # Process complete thought
                if buffer.strip():
                    thought = buffer.strip()
                    
                    # Skip if thought looks like JSON
                    if thought.startswith("{") or thought.startswith("["):
                        continue
                        
                    thoughts.append(thought)
                    
                    # Update planning context based on thought content
                    if thought.startswith("IMPORTANT:"):
                        planning_context["key_points"].append(thought[10:].strip())
                    elif "crucial" in thought.lower() or "important" in thought.lower() or "key" in thought.lower():
                        planning_context["key_points"].append(thought)
                    elif "choose" in thought.lower() or "decision" in thought.lower() or "selected" in thought.lower():
                        planning_context["decision_points"].append(thought)
                    
                    planning_context["thought_evolution"].append({
                        "thought": thought,
                        "timestamp": asyncio.get_event_loop().time() - start_time
                    })
                    
                    # Determine current focus based on content
                    if "problem" in thought.lower() or "requirement" in thought.lower():
                        planning_context["current_focus"] = "Problem Analysis"
                    elif "approach" in thought.lower() or "strategy" in thought.lower():
                        planning_context["current_focus"] = "Solution Strategy"
                    elif "implement" in thought.lower() or "step" in thought.lower():
                        planning_context["current_focus"] = "Implementation Planning"
                    elif "challenge" in thought.lower() or "risk" in thought.lower():
                        planning_context["current_focus"] = "Risk Assessment"
                    
                    # Generate new stage marker
                    stage_prompt = f"""You are analyzing a problem. Create a brief marker (5-8 words) that captures:
1. What aspect you're currently thinking about
2. The depth of analysis being performed

Your stage should feel like a window into an elegant mind at work.
Keep it simple and natural, ending with "..."

Examples:
- "Analyzing core problem details..."
- "Evaluating solution approaches..."
- "Considering implementation steps..."
"""
                    
                    current_stage = await self.agent.call_utility_llm(system=stage_prompt, msg="")
                    if isinstance(current_stage, str):
                        await self.show_progress(current_stage.strip())
                    
                    # Show the complete thought with kvps
                    await self.show_thought(thought, current_stage)
                
                await asyncio.sleep(0.1)  # Small delay between thoughts

            except Exception as e:
                self.agent.context.log.log(
                    type="warning",
                    content=f"Thinking phase error: {str(e)}\n{traceback.format_exc()}"
                )
        
        # Create final plan structure
        plan = {
            "key_points": planning_context["key_points"],
            "analysis": "\n".join(thoughts),
            "thoughts": thoughts,
            "thought_evolution": planning_context["thought_evolution"],
            "decision_points": planning_context["decision_points"]
        }
        
        # Store in agent's data
        self.agent.data["thought_process"] = "\n".join(thoughts)
        self.agent.data["accumulated_thoughts"] = thoughts
        self.agent.data["planning_context"] = planning_context
        self.agent.data["current_plan"] = plan
        
        return json.dumps(plan, indent=2)

    async def validate_plan(self, initial_plan: str) -> str:
        """Validate and refine the solution plan."""
        await self.show_progress("Validating solution plan...")
        
        # Get validation prompt
        validation_prompt = self.agent.read_prompt('thinking.phase.design.md')
        
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=validation_prompt),
            HumanMessage(content=initial_plan)
        ])
        
        # Generate validated plan
        validation_response = await self.agent.config.chat_model.ainvoke(prompt.format_messages())
        
        try:
            if isinstance(validation_response, AIMessage):
                validated_plan = validation_response.content if isinstance(validation_response.content, str) else str(validation_response.content)
            else:
                validated_plan = str(validation_response)
            
            # Parse the initial plan
            try:
                initial_plan_dict = json.loads(initial_plan)
                key_points = initial_plan_dict.get("key_points", [])
                analysis = initial_plan_dict.get("analysis", "")
                thoughts = initial_plan_dict.get("thoughts", [])
                
                # Format the initial plan
                formatted_initial_plan = []
                if key_points:
                    formatted_initial_plan.extend(['- ' + point for point in key_points])
                if analysis:
                    formatted_initial_plan.append('\n' + analysis)
                initial_plan_text = "\n".join(formatted_initial_plan)
                
            except:
                initial_plan_text = initial_plan
            
            # Show planning progress
            self.agent.context.log.log(
                type="agent",
                heading="Solution Planning Progress",
                content="Finalizing solution plan",
                kvps={
                    "Initial Analysis": initial_plan_text,
                    "Refined Plan": validated_plan,
                    "Final Solution Plan": self.agent.data.get("thought_process", "")
                }
            )
            
        except Exception as e:
            self.agent.context.log.log(
                type="warning",
                content=f"Failed to parse validated plan: {str(e)}"
            )
            validated_plan = initial_plan
        
        return validated_plan

    async def prepare_execution_phase(self, validated_plan: str, loop_data: LoopData):
        """Prepare for execution based on fw.include_thought_process.md"""
        # Get execution framework prompt
        fw_prompt = self.agent.read_prompt('fw.include_thought_process.md')
        
        # Add analysis context as a system message
        analysis_context = f"""
IMPORTANT - Your Previous Analysis:

THOUGHT PROCESS:
{self.agent.data.get("thought_process", "")}

ACCUMULATED THOUGHTS:
{self.agent.data.get("accumulated_thoughts", [])}

EXECUTION PLAN:
{validated_plan}

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
"""
        loop_data.system.append(analysis_context)
        
        # Add execution framework as a separate system message
        if isinstance(fw_prompt, str):
            loop_data.system.append(fw_prompt.format(
                validated_plan=validated_plan,
                accumulated_thoughts=self.agent.data.get("accumulated_thoughts", [])
            ))
        
        # Add final reminder
        final_reminder = """
CRITICAL: Your response MUST explicitly incorporate:
1. The insights from your prior analysis
2. The key conclusions from your thought process
3. The specific considerations you identified

DO NOT generate a response without referencing your prior analysis.
"""
        loop_data.system.append(final_reminder)

    async def _get_system_prompt(self) -> str:
        """Load and combine system prompt components"""
        system_components = [
            "agent.system.main.role.md",
            "agent.system.main.environment.md",
            "agent.system.main.communication.md",
            "agent.system.main.solving.md",
            "agent.system.main.tips.md"
        ]
        
        system_prompt_str = "# Agent Zero System Manual\n\n"
        for component in system_components:
            try:
                component_content = self.agent.read_prompt(component)
                if component_content:
                    system_prompt_str += component_content + "\n\n"
            except Exception as e:
                self.agent.context.log.log(
                    type="warning",
                    content=f"Failed to load system component from {component}: {str(e)}"
                )
        return system_prompt_str

    async def _get_tools_prompt(self) -> str:
        """Load and combine tool descriptions"""
        tool_files = [
            "agent.system.tool.response.md",
            "agent.system.tool.call_sub.md",
            "agent.system.tool.behaviour.md",
            "agent.system.tool.knowledge.md",
            "agent.system.tool.memory.md",
            "agent.system.tool.code_exe.md",
            "agent.system.tool.web.md"
        ]
        
        tools_prompt_str = "## Available Tools:\n\n"
        for tool_file in tool_files:
            try:
                tool_content = self.agent.read_prompt(tool_file)
                if tool_content:
                    tools_prompt_str += tool_content + "\n\n"
            except Exception as e:
                self.agent.context.log.log(
                    type="warning",
                    content=f"Failed to load tool description from {tool_file}: {str(e)}"
                )
        return tools_prompt_str
