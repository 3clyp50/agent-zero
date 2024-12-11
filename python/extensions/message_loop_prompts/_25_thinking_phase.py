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
		return self.agent.read_prompt("thinking.iterate.md")  

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

	async def show_thought(self, thought_stream: str, stage: str):    
		"""Display a thought as an Agent message with real-time character streaming."""    
		# Get current planning context    
		planning_context = self.agent.data.get("planning_context", {})    

		# Show in CLI with proper formatting    
		PrintStyle(    
			italic=True,    
			font_color="#b3b3ff",    
			padding=True    
		).stream(thought_stream)    

		# Accumulate the thought stream    
		accumulated_content = self.agent.data.get("accumulated_content", "")    
		accumulated_content += thought_stream    
		self.agent.data["accumulated_content"] = accumulated_content    

		# Get or create the current batch log item    
		current_batch = self.agent.data.get("current_thought_batch", None)    
		if not current_batch or self._should_create_new_batch(planning_context):    
			# Create new batch log item    
			current_batch = self.agent.context.log.log(    
				type="agent",    
				heading="Thinking...",    
				content=accumulated_content,  # Use accumulated content    
				kvps={    
					"Thoughts": [accumulated_content],  # Initialize with accumulated content    
					"Phase": planning_context.get("iteration_phase", "Initial"),    
					"Strategy": planning_context.get("current_strategy", "None"),    
					"Pattern": planning_context.get("thought_pattern", "None")    
					# Removed 'Evolution' key from kvps as per requirements  
				}    
			)    
			self.agent.data["current_thought_batch"] = current_batch    
			self.agent.data["current_batch_thoughts"] = [accumulated_content]    
		else:    
			# Update the content with accumulated content    
			current_batch.update(content=accumulated_content)    
			# Update Thoughts key with current batch thoughts    
			current_batch_thoughts = self.agent.data.get("current_batch_thoughts", [])    
			# Update the last thought in current_batch_thoughts    
			if current_batch_thoughts:    
				current_batch_thoughts[-1] = accumulated_content    
			else:    
				current_batch_thoughts = [accumulated_content]    
			self.agent.data["current_batch_thoughts"] = current_batch_thoughts    

			# Update the thoughts array in kvps    
			if current_batch.kvps:    
				current_batch.kvps["Thoughts"] = current_batch_thoughts    
				current_batch.update(kvps=current_batch.kvps)    

		# Check if this is a complete thought (ends with period or newline)    
		if thought_stream.strip().endswith('.') or '\n' in thought_stream:    
			# Clear the accumulated content    
			self.agent.data["accumulated_content"] = ""    
			current_thoughts = self.agent.data.get("current_batch_thoughts", [])    
			# Start a new thought in current_batch_thoughts    
			current_thoughts.append("")    
			self.agent.data["current_batch_thoughts"] = current_thoughts    

		# Update progress bar using show_progress    
		if stage:    
			await self.show_progress(stage.strip())    

	def _should_create_new_batch(self, context: Dict[str, Any]) -> bool:    
		"""Determine if a new thought batch should be created."""    
		current_thoughts = self.agent.data.get("current_batch_thoughts", [])    

		# Check number of thoughts in current batch    
		if len(current_thoughts) >= 25:  # Create new batch after 25 thoughts    
			return True    

		# Check if phase has changed    
		current_batch = self.agent.data.get("current_thought_batch")    
		if current_batch and current_batch.kvps:    
			if current_batch.kvps.get("Phase") != context.get("iteration_phase"):    
				return True    

		return False        

	async def _generate_thought(self, message: str, context: Dict[str, Any]) -> str:    
		"""Generate a single thought with real-time streaming."""    
		# Get the thinking prompt, system prompt, and tools prompt    
		thinking_prompt = self.get_thinking_prompt()    
		system_prompt = context["system_prompt"]    
		tools_prompt = context["tools_prompt"]    

		# Create thought generation context    
		thought_context = {    
			"phase": context["iteration_phase"],    
			"strategy": context["current_strategy"],    
			"pattern": context["thought_pattern"],    
			"recent_thoughts": [t["thought"] for t in context["thought_evolution"][-3:]] if context["thought_evolution"] else [],    
			"recent_insights": []    
		}    

		# Build the prompt    
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
		"""    

		prompt = ChatPromptTemplate.from_messages([    
			SystemMessage(content=system_content),    
			HumanMessage(content=f"""Problem to Solve: {message}    

		Generate the next thought, following the current phase, strategy, and pattern.    
		Show clear progression and demonstrate evolving understanding.   

		**Remember:**    
		- Do not execute or use any tools during this thinking phase.    
		- Focus on planning and analysis.    
		- Avoid starting multiple thoughts with the same phrase.  
		- Demonstrate learning and growth through diverse expression.
		- Format your response as natural text, not JSON.""")    
		])    

		# Get streaming response    
		response = ""    
		stage = await self._generate_stage("", context)    

		async for chunk in self.agent.config.chat_model.astream(prompt.format_messages()):    
			chunk_content = chunk.content if hasattr(chunk, 'content') else str(chunk)    
			if chunk_content:    
				response += chunk_content    
				# Stream each chunk in real-time    
				await self.show_thought(chunk_content, stage)    

		return response    

	async def think_through_message(self, loop_data: LoopData, thinking_duration: float) -> str:    
		"""Generate solution plan through iterative thinking and refinement."""    
		message = loop_data.user_message.output_text() if loop_data.user_message else ""    

		# Show initial planning message    
		duration_text = f"{int(thinking_duration)} seconds" if thinking_duration < 60 else f"{thinking_duration/60:.1f} minutes"    
		await self.show_progress(f"Planning solution approach for {duration_text}...")    

		# Initialize components and context    
		system_prompt = self.get_system_prompt()    
		tools_prompt = self.get_tools_prompt()    
		thinking_components = await self._generate_thinking_components(message, tools_prompt)    

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

		thoughts: List[str] = []    
		start_time = asyncio.get_event_loop().time()    

		try:    
			while (asyncio.get_event_loop().time() - start_time) < thinking_duration:    
				thought = await self._generate_thought(message, planning_context)    

				if thought and not thought.startswith("{") and not thought.startswith("["):    
					thoughts.append(thought)    
					self._update_planning_context(planning_context, thought)    
					await self._advance_iteration_phase(planning_context)    

				await asyncio.sleep(0.1)    

		except Exception as e:    
			self.agent.context.log.log(    
				type="warning",    
				content=f"Thinking phase error: {str(e)}\n{traceback.format_exc()}"    
			)    

		# Create final plan    
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

	async def _generate_stage(self, thought: str, context: Dict[str, Any]) -> str:  
		"""Generate a stage marker for the current thought."""  
		# Get evolution context  
		recent_evolution = context["thought_evolution"][-3:] if context["thought_evolution"] else []  
		evolution_summary = ""  
		if recent_evolution:  
			evolution_summary = f"\nBuilding on: {recent_evolution[-1]['thought'][:50]}..."  

		stage_prompt = f"""You are an AI agent in the {context['iteration_phase']} phase, using the {context['current_strategy']} strategy   
and following a {context['thought_pattern']} pattern.{evolution_summary}  

Create a natural stage marker of 6/10 words that reflects this context and shows progression.  

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