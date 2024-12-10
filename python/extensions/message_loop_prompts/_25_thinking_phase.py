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
        return get_prompt("thinking.iterate.md", self.agent)

    def get_system_prompt(self) -> str:
        """Get the system prompt."""
        return self.agent.read_prompt("agent.system.main.md")

    def get_tools_prompt(self) -> str:
        """Get the tools prompt."""
        return self.agent.read_prompt("agent.system.tools.md")

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
                "Pattern": planning_context.get("thought_pattern", "None"),
                "Evolution": self._get_thought_evolution_summary(planning_context)
            }
        )
        
        # Update progress bar using show_progress
        if stage:
            await self.show_progress(stage.strip())

    def _get_thought_evolution_summary(self, context: Dict[str, Any]) -> str:
        """Generate a concise summary of thought evolution."""
        evolution = context.get("thought_evolution", [])
        if len(evolution) < 2:
            return "Initial thoughts..."
            
        # Get the key insight from the last thought
        last_thought = evolution[-1]
        if last_thought.get("insights"):
            return f"Building on: {last_thought['insights'][0][:50]}..."
        return f"Developing {last_thought['phase'].lower()}..."

    async def think_through_message(self, loop_data: LoopData, thinking_duration: float) -> str:  
        """Generate solution plan through iterative thinking and refinement."""  
        message = loop_data.user_message.output_text() if loop_data.user_message else ""  

        # Show initial planning message  
        duration_text = f"{int(thinking_duration)} seconds" if thinking_duration < 60 else f"{thinking_duration/60:.1f} minutes"  
        await self.show_progress(f"Planning solution approach for {duration_text}...")  

        # Get system and tools prompts  
        system_prompt = self.get_system_prompt()  
        tools_prompt = self.get_tools_prompt()  

        # Generate dynamic thinking components with tools context  
        thinking_components = await self._generate_thinking_components(message, tools_prompt)  

        # Initialize planning context with dynamic components  
        planning_context = {  
            "thoughts": [],  
            "thought_evolution": [],  
            "current_focus": "Initial planning",  
            "iteration_phase": thinking_components["phases"][0]["name"],  
            "current_strategy": thinking_components["strategies"][0]["name"],  
            "thought_pattern": thinking_components["patterns"][0]["name"],  
            "thinking_components": thinking_components,  
            "system_prompt": system_prompt,  
            "tools_prompt": tools_prompt,  
            "phase_progress": {},  
            "strategy_insights": {}  
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
                    await self._advance_iteration_phase(planning_context)  

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
            "iteration_phases": self._summarize_iteration_phases(planning_context),  
            "key_insights": self._extract_key_insights(thoughts)  
        }  

        # Store in agent's data  
        self.agent.data["thought_process"] = "\n".join(thoughts)  
        self.agent.data["accumulated_thoughts"] = thoughts  
        self.agent.data["planning_context"] = planning_context  
        self.agent.data["current_plan"] = plan  

        return json.dumps(plan, indent=2)  

    def _update_planning_context(self, context: Dict[str, Any], thought: str):
        """Update planning context based on thought content and current phase."""
        current_time = asyncio.get_event_loop().time()
        
        # Create thought entry with key information
        thought_entry = {
            "thought": thought,
            "timestamp": current_time,
            "phase": context["iteration_phase"],
            "strategy": context["current_strategy"],
            "pattern": context["thought_pattern"],
            "insights": []  # Will store any new insights
        }
        
        # Extract insights from key terms
        key_terms = ["because", "therefore", "this means", "this suggests", "this indicates"]
        for term in key_terms:
            if term in thought.lower():
                insight = thought.lower().split(term)[1].strip()
                thought_entry["insights"].append(insight)
        
        # Update phase progress
        phase = context["iteration_phase"]
        if phase not in context["phase_progress"]:
            context["phase_progress"][phase] = {
                "thought_count": 0,
                "insights": [],
                "start_time": current_time
            }
        context["phase_progress"][phase]["thought_count"] += 1
        context["phase_progress"][phase]["insights"].extend(thought_entry["insights"])
        
        # Update strategy insights
        strategy = context["current_strategy"]
        if strategy not in context["strategy_insights"]:
            context["strategy_insights"][strategy] = {
                "applications": [],
                "effectiveness": 0
            }
        if thought_entry["insights"]:
            context["strategy_insights"][strategy]["effectiveness"] += 1
            context["strategy_insights"][strategy]["applications"].append(thought)
        
        # Add to evolution history
        context["thought_evolution"].append(thought_entry)
        context["thoughts"].append(thought)

    async def _advance_iteration_phase(self, context: Dict[str, Any]):
        """Advance through iteration phases based on progress and insights."""
        components = context["thinking_components"]
        phases = [p["name"] for p in components["phases"]]
        strategies = [s["name"] for s in components["strategies"]]
        
        current_phase = context["iteration_phase"]
        current_phase_progress = context["phase_progress"].get(current_phase, {})
        
        # Check phase advancement criteria
        should_advance = False
        
        # 1. Check thought count in current phase
        if current_phase_progress.get("thought_count", 0) >= 4:
            should_advance = True
            
        # 2. Check insight generation
        if len(current_phase_progress.get("insights", [])) >= 3:
            should_advance = True
            
        # 3. Check time spent in phase
        current_time = asyncio.get_event_loop().time()
        phase_duration = current_time - current_phase_progress.get("start_time", current_time)
        if phase_duration > 60:  # 60 seconds in phase
            should_advance = True
        
        # Advance phase if criteria met
        if should_advance:
            current_index = phases.index(current_phase)
            next_index = (current_index + 1) % len(phases)
            context["iteration_phase"] = phases[next_index]
            
            # Reset phase progress for new phase
            if context["iteration_phase"] not in context["phase_progress"]:
                context["phase_progress"][context["iteration_phase"]] = {
                    "thought_count": 0,
                    "insights": [],
                    "start_time": current_time
                }
        
        # Update strategy based on effectiveness
        strategy_effectiveness = {
            s: context["strategy_insights"].get(s, {}).get("effectiveness", 0)
            for s in strategies
        }
        if strategy_effectiveness:
            # Choose most effective strategy that hasn't been used recently
            recent_strategies = [t["strategy"] for t in context["thought_evolution"][-3:]]
            available_strategies = [s for s in strategies if s not in recent_strategies]
            if available_strategies:
                context["current_strategy"] = max(
                    available_strategies,
                    key=lambda s: strategy_effectiveness.get(s, 0)
                )
            else:
                # If all strategies recently used, choose most effective overall
                context["current_strategy"] = max(
                    strategies,
                    key=lambda s: strategy_effectiveness.get(s, 0)
                )

    def _summarize_iteration_phases(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Summarize insights gained through different iteration phases."""
        phase_summary = {}
        
        for phase, progress in context["phase_progress"].items():
            phase_summary[phase] = {
                "thought_count": progress["thought_count"],
                "insight_count": len(progress["insights"]),
                "key_insights": progress["insights"][:3]  # Top 3 insights
            }
            
            # Add strategy effectiveness for this phase
            phase_summary[phase]["strategies"] = {}
            for strategy, data in context["strategy_insights"].items():
                strategy_thoughts = [t for t in data.get("applications", []) 
                                  if any(e["phase"] == phase and e["strategy"] == strategy 
                                       for e in context["thought_evolution"])]
                if strategy_thoughts:
                    phase_summary[phase]["strategies"][strategy] = len(strategy_thoughts)
        
        return phase_summary

    async def _generate_thought(self, message: str, context: Dict[str, Any]) -> str:  
        """Generate a single thought based on current context and previous thoughts."""  
        # Get the thinking prompt, system prompt, and tools prompt  
        thinking_prompt = self.get_thinking_prompt()  
        system_prompt = context["system_prompt"]  
        tools_prompt = context["tools_prompt"]  

        # Get recent thoughts and insights  
        recent_thoughts = context["thought_evolution"][-3:] if context["thought_evolution"] else []  
        recent_insights = []  
        for t in recent_thoughts:  
            recent_insights.extend(t.get("insights", []))  

        # Create thought generation context  
        thought_context = {  
            "phase": context["iteration_phase"],  
            "strategy": context["current_strategy"],  
            "pattern": context["thought_pattern"],  
            "recent_thoughts": [t["thought"] for t in recent_thoughts],  
            "recent_insights": recent_insights  
        }  

        # Combine prompts with enhanced context  
        system_content = f"""  
    {system_prompt}  

    {thinking_prompt}  

    AVAILABLE TOOLS AND CAPABILITIES:  
    {tools_prompt}  

    CURRENT THINKING CONTEXT:  
    Phase: {thought_context['phase']}  
    Strategy: {thought_context['strategy']}  
    Pattern: {thought_context['pattern']}  

    Recent Thoughts:  
    {chr(10).join(['- ' + t for t in thought_context['recent_thoughts']])}  

    Recent Insights:  
    {chr(10).join(['- ' + i for i in thought_context['recent_insights']])}  

    IMPORTANT:  
    - During this thinking phase, consider the tools and plan how you might use them, but **do not execute or use any tools at this stage**.  
    - Focus on planning and analysis.  
    - Your thoughts must be expressed in JSON format with a "thoughts" array containing your thought process.  
    For example:  
    {{  
        "thoughts": [  
            "Building on the previous insight about X...",  
            "This connects to our understanding of Y...",  
            "This suggests a new approach using Z..."  
        ]  
    }}  
    """  

        prompt = ChatPromptTemplate.from_messages([  
            SystemMessage(content=system_content),  
            HumanMessage(content=f"""Problem to Solve: {message}  

    Generate the next thought in our analysis, building on previous insights and following the current phase, strategy, and pattern.  
    Show clear progression from previous thoughts and demonstrate evolving understanding.  

    **Remember:**  
    - Do not execute or use any tools during this thinking phase.  
    - Focus on planning and analysis.  
    - Format your response as JSON with a "thoughts" array.""")  
        ])  

        response = await self.agent.config.chat_model.ainvoke(prompt.format_messages())  
        response_text = response.content if isinstance(response, AIMessage) else str(response)  

        try:  
            # Try to parse the response as JSON  
            thought_data = DirtyJson.parse_string(response_text)  
            if isinstance(thought_data, dict) and "thoughts" in thought_data:  
                # If it's a JSON object with thoughts array, join them into a single string  
                thoughts = thought_data["thoughts"]  
                if isinstance(thoughts, list):  
                    return "\n".join(str(t) for t in thoughts)  
                else:  
                    return str(thoughts)  

            # If it's JSON but doesn't match our expected format, return the whole response  
            return response_text  
        except:  
            # If it's not valid JSON, return the raw response  
            return response_text  

    async def _generate_stage(self, thought: str, context: Dict[str, Any]) -> str:
        """Generate a stage marker for the current thought."""
        # Get evolution context
        recent_evolution = context["thought_evolution"][-3:] if context["thought_evolution"] else []
        evolution_summary = ""
        if recent_evolution:
            evolution_summary = f"\nBuilding on: {recent_evolution[-1]['thought'][:50]}..."
        
        stage_prompt = f"""You are an AI agent in the {context['iteration_phase']} phase, using the {context['current_strategy']} strategy 
and following a {context['thought_pattern']} pattern.{evolution_summary}

Create a brief, natural stage marker (max 10 words) that reflects this context and shows progression.

Guidelines:
1. Be concise and natural
2. End with "..."
3. Focus on current phase and strategy
4. Show how thinking is evolving
5. Your stage should feel like a window into an elegant mind at work

Current thought context:
{thought}

Create a stage:"""
        
        stage = await self.agent.call_utility_llm(system=stage_prompt, msg="")
        if isinstance(stage, str):
            await self.show_progress(stage.strip())
            return stage.strip()
        return "Thinking..."

    async def _generate_thinking_components(self, message: str, tools_prompt: str) -> ThinkingComponents:  
        """Generate dynamic thinking components based on the current problem context."""  
        # Get the dynamic components prompt  
        components_prompt = self.agent.read_prompt('dynamic_components.md')  

        base_prompt = f"""Generate thinking components for solving this problem: {message}  

    Available tools and capabilities:  
    {tools_prompt}  

    **IMPORTANT:**  
    - Consider how the tools can be leveraged in different phases, strategies, and patterns.  
    - Do not execute or use any tools at this stage.  
    - Your response must be ONLY valid JSON matching this structure without any other text or markdown:  
    {{  
        "phases": [  
            {{"name": string, "description": string, "tool_considerations": [string]}},  
            // 2-4 phases total  
        ],  
        "strategies": [  
            {{"name": string, "description": string, "tool_applications": [string]}},  
            // 2-3 strategies total  
        ],  
        "patterns": [  
            {{"name": string, "description": string, "tool_integration": [string]}},  
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

    async def validate_plan(self, initial_plan: str) -> str:  
        """Validate and refine the solution plan."""  
        await self.show_progress("Validating solution plan...")  

        # Get validation prompt  
        validation_prompt = self.agent.read_prompt('thinking.validate.md')  

        # Ensure the validation prompt includes instructions about not using tools directly  
        # If the 'thinking.validate.md' does not include this, we can add it here  

        prompt = ChatPromptTemplate.from_messages([  
            SystemMessage(content=validation_prompt),  
            HumanMessage(content=f"""{initial_plan}  

    **IMPORTANT:**  
    - While refining the plan, consider how to use the available tools, but **do not execute or use any tools at this stage**.  
    - Focus on improving the plan and ensuring its practicality.  

    Your goal is to produce a refined, validated, and implementation-ready solution plan.""")  
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
                    "Refined Plan": validated_plan  
                }  
            )  

        except Exception as e:  
            self.agent.context.log.log(  
                type="warning",  
                heading="Plan validation warning:",  
                content=f"Error during plan validation: {str(e)}\n{traceback.format_exc()}"  
            )  
            validated_plan = initial_plan  

        return validated_plan  

    async def prepare_execution_phase(self, validated_plan: str, loop_data: LoopData):
        """Prepare execution phase based on validated plan and key insights."""
        # Get planning context for richer insights
        planning_context = self.agent.data.get("planning_context", {})
        
        # Extract key insights and strategy effectiveness
        key_insights = self._extract_key_insights(planning_context.get("thoughts", []))
        strategy_insights = planning_context.get("strategy_insights", {})
        
        # Format strategy effectiveness
        strategy_summary = []
        for strategy, data in strategy_insights.items():
            effectiveness = data.get("effectiveness", 0)
            applications = len(data.get("applications", []))
            if applications > 0:
                strategy_summary.append(f"- {strategy}: {effectiveness} insights from {applications} applications")
        
        # Add analysis context and instructions as a single system message
        analysis_context = f"""
IMPORTANT - Solution Plan Execution:

REFINED PLAN:
{validated_plan}

KEY INSIGHTS:
{key_insights}

STRATEGY EFFECTIVENESS:
{chr(10).join(strategy_summary)}

EXECUTION REQUIREMENTS:
1. Follow the refined plan structure
2. Verify approach and strategy alignment
3. Integrate key insights
4. Ensure solution completeness and quality
5. Build on successful strategies
6. Apply validated patterns

Remember: The refined plan will guide the implementation phase.
"""
        loop_data.system.append(analysis_context)

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
