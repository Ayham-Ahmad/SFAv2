from sqlalchemy.orm import Session

from . import tents_agent, tables_agent, guard_agent, intent_agent, verifier_agent, planner_agent
from ..tools.tools_manager import ToolsManager
from ..services.prompts import CreatePrompt, UpdatePrompt, StopPrompt
from ..services.fallback import FallBackService
from ..core.llm_client import call_agent
from ..utils.clean import extract_react_components, clean_tables_schema, get_chosen_tables_schema
from ..utils.responses import get_fallback_response
from api.database.events import TentCRUD
from api.constants import AIModel
from api.database.schemas import get_usage_metrics_dict
from api.config import settings

ACTIVE_AGENTS = {}

class SFA:

    def __init__(self, user_query: str, db: Session, company_id: int, user_id: int = None):
        self.user_query = user_query
        self.db = db
        self.company_id = company_id
        self.user_id = user_id
        self.max_iterations = settings.MAX_ITERATIONS
        self.usage_metrics = get_usage_metrics_dict()
        self.last_retrieval_results = None
        self.all_generated_graphs = []
        
        if self.user_id is not None: # just a safy reset
            ACTIVE_AGENTS[self.user_id] = False

    async def main(self, request=None):
        
        
        
        
        # 1. GUARD AGENT
        print("\n1. Guard agent...")
        is_safe, self.usage_metrics = await guard_agent.is_query_safe(self.user_query, self.usage_metrics)
        if not is_safe:
            return "Sorry, I can't proceed with this request", self.usage_metrics, self.all_generated_graphs
        print(f"Guard agent result: {is_safe}\n")
        
        
        
        
        
        
        
        # 2. INTENT AGENT
        print("\n2. Intent agent...")
        intent_response, self.usage_metrics = await intent_agent.classify_intent(self.user_query, self.usage_metrics)
        if intent_response:
            intent = intent_response.get('intent')
            complexity = intent_response.get('complexity', 'ANALYSIS')
            if intent in ['GREETING', 'IRRELEVANT']:
                print(intent_response.get('response'))
                return intent_response.get('response'), self.usage_metrics, self.all_generated_graphs
            print(f"Intent agent result: {intent} (Complexity: {complexity})\n")
        
        # COST-AWARE QUERY OPTIMIZATION (Gap 4)
        # Adapt execution budget dynamically based on complexity
        if complexity == "LOOKUP":
            self.max_iterations = min(self.max_iterations, 3)
        elif complexity == "COMPUTATION":
            self.max_iterations = min(self.max_iterations, 4)
        else:
            self.max_iterations = min(self.max_iterations, 7)
        print(f"Adaptive Execution Budget set to: {self.max_iterations} iterations\n")
        
        
        
        
        
        
        # 3. TENT AGENT
        print("\n3. Choosing the Tents...")
        tents_ids, self.usage_metrics = await tents_agent.get_relevant_tents(self.user_query, self.db, self.company_id, self.usage_metrics)
        print(f"Choosing the Tents result: {tents_ids}\n")
        if not tents_ids:
            return "Sorry, can you clarify your request, like add the kind of data that you need?", self.usage_metrics, self.all_generated_graphs
        
        
        
        
        
         
        # 4. TABLES AGENT
        print("\n4. Choosing the tables...")
        tents_schema = TentCRUD.get_tables_schema(self.db, self.company_id, tents_ids)
        tablesAgent_tables_schema = clean_tables_schema(tents_schema)
        tables, self.usage_metrics = await tables_agent.get_relevant_tables(self.db, self.user_query, tents_ids, tablesAgent_tables_schema, self.usage_metrics)
        tables_schema = get_chosen_tables_schema(tables, tents_schema)
        print(f"Choosing the tables result: {tables_schema}")
                
        
        
        
        
        # 4.5 PLANNER AGENT (Phase 5)
        execution_plan = ""
        if complexity == "ANALYSIS":
            print("\n4.5 Generating execution plan...")
            execution_plan, self.usage_metrics = await planner_agent.generate_plan(self.user_query, tables_schema, self.usage_metrics)
            print(f"Plan generated:\n{execution_plan}\n")
        
        # 5. PREPARE PROMPT
        print("\n5. Prepare the prompt...")
        base_prompt = CreatePrompt.init_prompt(
            user_query=self.user_query, 
            tents_schema=tables_schema, 
            complexity=complexity, 
            execution_plan=execution_plan,
            iteration=self.max_iterations
        )
        current_prompt = base_prompt
        scratchpad = ""
        iterations = 0
        print(f"Prepare the prompt result: Prompt initialized successfully\n")
        # print(current_prompt)
        

        
        
        
        # 6. AGENT LOOP
        print("\n6. Entering reasoning loop...")
        while iterations < self.max_iterations:            
            print(f"\na. Agent iteration {iterations}...")
            
            # Check for early stop request from frontend
            if self.user_id is not None and ACTIVE_AGENTS.get(self.user_id, False):
                print(f"--- STOP SIGNAL RECEIVED FOR USER {self.user_id} ---")
                current_prompt += StopPrompt.prompt()
                ACTIVE_AGENTS[self.user_id] = False # Reset so it doesn't duplicate
            
            llm_raw_output, self.usage_metrics = await call_agent(
                prompt=current_prompt, 
                model=AIModel.LLAMA_33_70B, 
                usage_metrics=self.usage_metrics,
                user_query=self.user_query,
                scratchpad=scratchpad
            )
            print(f"\nAgent output result: {llm_raw_output}\n")
            
            components = extract_react_components(llm_raw_output)
            
            print("\nb. Checking for Final Answer...")
            if components["action"] == "Final Answer" or "Final Answer:" in llm_raw_output:
                print("\nChecking for Final Answer result: Found! Running verification...")
                final_answer_text = components.get("action_input", "Analysis complete, but no output provided.")
                
                # VERIFIER STAGE (Phase 3)
                verified_answer, self.usage_metrics = await verifier_agent.verify_answer(
                    final_answer=final_answer_text,
                    scratchpad=scratchpad,
                    usage_metrics=self.usage_metrics
                )
                components["action_input"] = verified_answer
                
                return components, self.usage_metrics, self.all_generated_graphs
            
            print("\nChecking for Final Answer result: Not found, continuing...\n")
            
            print("\nc. Execute Tools via ToolsManager...")
            action_input = components.get("action_input")
            
            if isinstance(action_input, dict) and "error" in action_input:
                observation = f"Observation: ERROR - {action_input['error']}. Please output valid JSON."
            else:
                observation, self.usage_metrics, self.last_retrieval_results, step_graphs = await ToolsManager.main_agent_output_manager(
                    self.db, self.company_id, action_input, request, self.usage_metrics, complexity, self.last_retrieval_results, self.user_id
                )
                if step_graphs:
                    self.all_generated_graphs.extend(step_graphs) # fix later, because maybe the agent wil return a list of graphs, is it will be a list in a list
                
            print(f"\nExecute Tools result: {observation}\n")
            
            print("d. updating prompt...")
            current_prompt, scratchpad = UpdatePrompt.update_prompt(base_prompt, scratchpad, llm_raw_output, observation)
            
            iterations += 1
            
            if iterations == self.max_iterations - 1:
                current_prompt += "\n\nSYSTEM WARNING: You have reached the maximum number of reasoning steps. You MUST immediately output a 'Final Answer' based on the information you have gathered so far. Do NOT call any more tools."
            
        print("\n10. Exiting loop (max iterations reached)...\n")
        
        # Fallback response if max iterations reached or timeout
        fallback_answer, self.usage_metrics = await FallBackService.generate_fallback_summary(
            user_query=self.user_query,
            scratchpad=scratchpad,
            usage_metrics=self.usage_metrics
        )
        
        return get_fallback_response(fallback_answer), self.usage_metrics, self.all_generated_graphs