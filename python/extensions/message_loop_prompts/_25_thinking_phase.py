from datetime import datetime
from python.helpers.extension import Extension
from agent import Agent, LoopData
from python.helpers.print_style import PrintStyle
from typing import List, Dict, Any, Optional, TypedDict, Union
import asyncio
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from python.helpers.dirty_json import DirtyJson
from python.helpers import settings
import json
import traceback

def get_prompt(file: str, agent: Agent) -> str:
    """Helper function to get prompts with variables."""
    vars = {
        "date_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "agent_name": agent.agent_name,
    }
    return agent.read_prompt(file, **vars)

class ThinkingComponent(TypedDict):
    name: str
    description: str

class ThinkingComponents(TypedDict):
    phases: List[ThinkingComponent]
    strategies: List[ThinkingComponent]
    patterns: List[ThinkingComponent]

class ThinkingPhaseExtension(Extension):

    def get_thinking_prompt(self) -> str:
        """Get the main thinking phase prompt."""
        return get_prompt("thinking.phase.prompt.md", self.agent)

    def get_thought_iteration_prompt(self) -> str:
        """Get the thought iteration framework prompt."""
        return get_prompt("thought_iteration.md", self.agent)

    def get_system_prompt(self) -> str:
        """Get the system prompt."""
        return get_prompt("agent.system.main.md", self.agent)

    def get_tools_prompt(self) -> str:
        """Get the tools prompt."""
        return get_prompt("agent.system.tools.md", self.agent)

    async def execute(self, loop_data: LoopData = LoopData(), **kwargs):
        """Execute the thinking phase extension."""
        # Reset execution phase at the start
        self.agent.data["execution_phase"] = False
        
        # Get the current message
        current_message = loop_data.user_message
        
        # Get settings
        current_settings = settings.get_settings()
        thinking_trigger_type = current_settings.get("thinking_trigger_type", "enabled")
        thinking_duration = current_settings["thinking_duration"]
        
        # Check if thinking is disabled
        if thinking_trigger_type == "disabled":
            print("DEBUG: Thinking phase is disabled")
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
            
            # Process thoughts with dynamic stages
            plan = await self.think_through_message(loop_data, thinking_duration)
            validated_plan = await self.validate_plan(plan)
            await self.prepare_execution_phase(validated_plan, loop_data)
            
            # After thinking phase completes, set execution phase
            self.agent.data["execution_phase"] = True

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
        """Display a thought as an Agent message with enhanced context."""
        # Get current planning context
        planning_context = self.agent.data.get("planning_context", {})
        
        # Show in CLI with proper formatting
        PrintStyle(
            italic=True,
            font_color="#b3b3ff",
            padding=True
        ).print(thought)
        
        # Show in agent log with thoughts and context
        log_item = self.agent.context.log.log(
            type="agent",
            heading="Thinking...",
            content=thought,
            kvps={
                "Thoughts": [thought],
                "Phase": planning_context.get("iteration_phase", "Initial"),
                "Strategy": planning_context.get("current_strategy", "None"),
                "Pattern": planning_context.get("thought_pattern", "None")
            }
        )
        
        # Update progress bar using show_progress
        if stage:
            await self.show_progress(stage.strip())

    async def think_through_message(self, loop_data: LoopData, thinking_duration: float) -> str:
        """Generate solution plan through iterative thinking and refinement."""
        message = loop_data.user_message.output_text() if loop_data.user_message else ""
        
        # Show initial planning message
        duration_text = f"{int(thinking_duration)} seconds" if thinking_duration < 60 else f"{thinking_duration/60:.1f} minutes"
        await self.show_progress(f"Planning solution approach for {duration_text}...")
        
        # Generate dynamic thinking components
        thinking_components = await self._generate_thinking_components(message)
        
        # Initialize planning context with dynamic components
        planning_context = {
            "thoughts": [],
            "thought_evolution": [],
            "current_focus": "Initial planning",
            "iteration_phase": thinking_components["phases"][0]["name"],
            "current_strategy": thinking_components["strategies"][0]["name"],
            "thought_pattern": thinking_components["patterns"][0]["name"],
            "thinking_components": thinking_components  # Store full components for reference
        }
        self.agent.data["planning_context"] = planning_context
        
        # Initialize for thought collection
        thoughts: List[str] = []
        start_time = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start_time) < thinking_duration:
            try:
                # Generate complete thought
                thought = await self._generate_thought(message, planning_context)
                if thought and not thought.startswith("{") and not thought.startswith("["):
                    thoughts.append(thought)
                    
                    # Update planning context and phase
                    self._update_planning_context(planning_context, thought)
                    await self._advance_iteration_phase(planning_context, len(thoughts))
                    
                    # Generate and show stage
                    stage = await self._generate_stage(thought, planning_context)
                    await self.show_progress(stage)
                    await self.show_thought(thought, stage)
                
                await asyncio.sleep(0.1)

            except Exception as e:
                self.agent.context.log.log(
                    type="warning",
                    content=f"Thinking phase error: {str(e)}\n{traceback.format_exc()}"
                )
        
        # Create final plan structure
        plan = {
            "thoughts": thoughts,
            "thought_evolution": planning_context["thought_evolution"],
            "iteration_phases": self._summarize_iteration_phases(planning_context)
        }
        
        # Store in agent's data
        self.agent.data["thought_process"] = "\n".join(thoughts)
        self.agent.data["accumulated_thoughts"] = thoughts
        self.agent.data["planning_context"] = planning_context
        self.agent.data["current_plan"] = plan
        
        return json.dumps(plan, indent=2)

    def _update_planning_context(self, context: Dict[str, Any], thought: str):
        """Update planning context based on thought content and current phase."""
        # Add phase-specific insights
        context["thought_evolution"].append({
            "thought": thought,
            "timestamp": asyncio.get_event_loop().time(),
            "phase": context["iteration_phase"],
            "strategy": context["current_strategy"],
            "pattern": context["thought_pattern"]
        })
        context["thoughts"].append(thought)

    async def _advance_iteration_phase(self, context: Dict[str, Any], thought_count: int):
        """Advance through iteration phases based on progress and context."""
        components = context["thinking_components"]
        phases = [p["name"] for p in components["phases"]]
        strategies = [s["name"] for s in components["strategies"]]
        patterns = [p["name"] for p in components["patterns"]]
        
        # Dynamic phase advancement based on thought evolution
        current_evolution = context.get("thought_evolution", [])
        if current_evolution:
            last_thoughts = current_evolution[-3:] if len(current_evolution) >= 3 else current_evolution
            repeated_patterns = len(set(t.get("pattern") for t in last_thoughts)) == 1
            
            # If pattern has repeated too much, force a change
            if repeated_patterns:
                current_pattern_index = patterns.index(context["thought_pattern"])
                context["thought_pattern"] = patterns[(current_pattern_index + 1) % len(patterns)]
        
        # Advance phase based on both count and context
        phase_index = min((thought_count // 4) % len(phases), len(phases) - 1)
        context["iteration_phase"] = phases[phase_index]
        
        # Rotate through strategies with some randomization for exploration
        strategy_index = ((thought_count // 2) + hash(str(current_evolution[-1:])) if current_evolution else 0) % len(strategies)
        context["current_strategy"] = strategies[strategy_index]
        
        # Update thought pattern if not recently changed
        if not context.get("last_pattern_change", 0) or thought_count - context.get("last_pattern_change", 0) >= 3:
            pattern_index = (thought_count // 3) % len(patterns)
            context["thought_pattern"] = patterns[pattern_index]
            context["last_pattern_change"] = thought_count

    def _summarize_iteration_phases(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Summarize insights gained through different iteration phases with enhanced analytics."""
        phase_summary = {}
        
        for entry in context["thought_evolution"]:
            phase = entry["phase"]
            if phase not in phase_summary:
                phase_summary[phase] = {
                    "thoughts": [],
                    "strategies_used": [],
                    "patterns_used": [],
                    "key_insights": [],
                    "duration": 0,
                    "thought_count": 0,
                    "pattern_distribution": {},
                    "strategy_effectiveness": {}
                }
            
            # Add thought with timestamp
            thought_entry = {
                "content": entry["thought"],
                "timestamp": entry.get("timestamp", 0),
                "pattern": entry["pattern"],
                "strategy": entry["strategy"]
            }
            phase_summary[phase]["thoughts"].append(thought_entry)
            
            # Track unique strategies and patterns
            if entry["strategy"] not in phase_summary[phase]["strategies_used"]:
                phase_summary[phase]["strategies_used"].append(entry["strategy"])
            if entry["pattern"] not in phase_summary[phase]["patterns_used"]:
                phase_summary[phase]["patterns_used"].append(entry["pattern"])
            
            # Update pattern distribution
            pattern = entry["pattern"]
            phase_summary[phase]["pattern_distribution"][pattern] = \
                phase_summary[phase]["pattern_distribution"].get(pattern, 0) + 1
            
            # Track strategy effectiveness (based on key insights generated)
            strategy = entry["strategy"]
            if any(keyword in entry["thought"].lower() for keyword in ["important", "key", "crucial", "significant"]):
                phase_summary[phase]["strategy_effectiveness"][strategy] = \
                    phase_summary[phase]["strategy_effectiveness"].get(strategy, 0) + 1
                phase_summary[phase]["key_insights"].append(entry["thought"])
            
            # Update metrics
            phase_summary[phase]["thought_count"] += 1
        
        # Calculate phase durations and additional metrics
        for phase, data in phase_summary.items():
            if data["thoughts"]:
                start_time = min(t["timestamp"] for t in data["thoughts"])
                end_time = max(t["timestamp"] for t in data["thoughts"])
                data["duration"] = end_time - start_time
                
                # Calculate thought density (thoughts per minute)
                if data["duration"] > 0:
                    data["thought_density"] = data["thought_count"] / (data["duration"] / 60)
                
                # Identify most effective patterns and strategies
                data["most_effective_pattern"] = max(data["pattern_distribution"].items(), 
                                                   key=lambda x: x[1])[0] if data["pattern_distribution"] else None
                data["most_effective_strategy"] = max(data["strategy_effectiveness"].items(), 
                                                    key=lambda x: x[1])[0] if data["strategy_effectiveness"] else None
        
        return phase_summary

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
                thoughts = initial_plan_dict.get("thoughts", [])
                
                # Format the initial plan
                initial_plan_text = "\n".join(['- ' + thought for thought in thoughts]) if thoughts else initial_plan
                
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
        """Prepare final plan validation based on fw.include_thought_process.md"""
        # Get validation framework prompt
        fw_prompt = self.agent.read_prompt('fw.include_thought_process.md')
        
        # Add analysis context and instructions as a single system message
        analysis_context = f"""
IMPORTANT - Final Solution Plan Validation:

REFINED PLAN:
{validated_plan}

KEY INSIGHTS:
{self._extract_key_insights(self.agent.data.get("accumulated_thoughts", []))}

VALIDATION REQUIREMENTS:
1. Validate the refined plan structure
2. Verify approach and strategy alignment
3. Confirm key insights integration
4. Ensure solution completeness and quality

Remember: This is the final validation phase to ensure the plan is complete and ready to guide implementation.
"""
        loop_data.system.append(analysis_context)
        
        # Add validation framework as a separate system message
        if isinstance(fw_prompt, str):
            loop_data.system.append(fw_prompt.format(
                validated_plan=validated_plan,
                accumulated_thoughts=self._extract_key_insights(self.agent.data.get("accumulated_thoughts", []))
            ))

    def _extract_key_insights(self, thoughts: List[str]) -> str:
        """Extract key insights from accumulated thoughts."""
        if not thoughts:
            return "No prior insights available."
            
        # Get the most significant thoughts (last 3-5 thoughts that represent conclusions)
        significant_thoughts = thoughts[-5:] if len(thoughts) > 5 else thoughts
        
        # Format insights
        insights = []
        for thought in significant_thoughts:
            # Clean up the thought and make it concise
            cleaned = thought.strip().split('\n')[0]  # Take first line if multiple
            if len(cleaned) > 100:  # If still too long, truncate
                cleaned = cleaned[:97] + "..."
            insights.append(f"- {cleaned}")
            
        return "\n".join(insights)

    async def _generate_thought(self, message: str, context: Dict[str, Any]) -> str:
        """Generate a single thought based on current context."""
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=self.get_thinking_prompt()),
            HumanMessage(content=f"""Problem to Solve: {message}

Current Phase: {context['iteration_phase']}
Strategy: {context['current_strategy']}
Pattern: {context['thought_pattern']}

Express your thoughts following the current phase, strategy, and pattern.""")
        ])
        
        response = await self.agent.config.chat_model.ainvoke(prompt.format_messages())
        if isinstance(response, AIMessage):
            return response.content if isinstance(response.content, str) else str(response.content)
        return str(response)

    async def _generate_stage(self, thought: str, context: Dict[str, Any]) -> str:
        """Generate a stage marker for the current thought."""
        stage_prompt = f"""You are an AI agent in the {context['iteration_phase']} phase, using the {context['current_strategy']} strategy 
and following a {context['thought_pattern']} pattern. Create a brief, natural stage marker (max 10 words) that reflects this context.

Guidelines:
1. Be concise and natural
2. End with "..."
3. Focus on current phase and strategy
4. Your stage should feel like a window into an elegant mind at work

Current thought context:
{thought}

Create a stage:"""
        
        stage = await self.agent.call_utility_llm(system=stage_prompt, msg="")
        if isinstance(stage, str):
            await self.show_progress(stage.strip())
            return stage.strip()
        return "Thinking..."

    async def _generate_thinking_components(self, message: str) -> ThinkingComponents:
        """Generate dynamic thinking components based on the current problem context."""
        # Get the dynamic components prompt
        components_prompt = self.agent.read_prompt('dynamic_components.md')
        
        base_prompt = f"""Generate thinking components for solving this problem: {message}

IMPORTANT: You must respond with ONLY valid JSON matching this structure. Do not include any other text or markdown:
{{
    "phases": [
        {{"name": string, "description": string}},
        // 2-4 phases total
    ],
    "strategies": [
        {{"name": string, "description": string}},
        // 2-3 strategies total
    ],
    "patterns": [
        {{"name": string, "description": string}},
        // 2-3 patterns total
    ]
}}"""

        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=components_prompt),
            HumanMessage(content=base_prompt)
        ])
        
        # Keep trying until we get valid components
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Generate components using LLM
                response = await self.agent.config.chat_model.ainvoke(prompt.format_messages())
                components_str = str(response.content) if isinstance(response, AIMessage) else str(response)
                
                # Parse components using DirtyJson
                components = DirtyJson.parse_string(components_str)
                
                if not isinstance(components, dict):
                    raise ValueError("Components must be a dictionary")

                # Validate structure
                required_keys = ["phases", "strategies", "patterns"]
                missing_keys = [k for k in required_keys if k not in components]
                if missing_keys:
                    raise ValueError(f"Missing required keys: {missing_keys}")
                
                # Validate arrays and convert to TypedDict
                result: ThinkingComponents = {
                    "phases": [],
                    "strategies": [],
                    "patterns": []
                }
                
                for key in required_keys:
                    if not isinstance(components[key], list) or not components[key]:
                        raise ValueError(f"{key} must be a non-empty array")
                    
                    for item in components[key]:
                        if not isinstance(item, dict) or "name" not in item or "description" not in item:
                            raise ValueError(f"Invalid item in {key}: {item}")
                        result[key].append({
                            "name": str(item["name"]),
                            "description": str(item["description"])
                        })
                
                return result
                
            except Exception as e:
                if attempt == max_retries - 1:
                    raise ValueError(f"Failed to generate valid thinking components after {max_retries} attempts: {str(e)}")
                
                # Add more explicit instruction for retry
                prompt = ChatPromptTemplate.from_messages([
                    SystemMessage(content=components_prompt),
                    HumanMessage(content=f"{base_prompt}\n\nPrevious attempt failed with: {str(e)}\nPlease ensure your response is properly formatted JSON."),
                ])
        
        raise ValueError("Failed to generate valid thinking components")