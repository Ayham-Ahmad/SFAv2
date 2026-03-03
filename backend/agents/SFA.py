from sqlalchemy.orm import Session

from . import tents_agent, tables_agent, guard_agent, intent_agent
from ..tools.tools_manager import ToolsManager
from ..services.prompts import CreatePrompt, UpdatePrompt
from ..core.llm_client import call_agent
from ..utils.clean import extract_react_components, clean_tables_schema, get_chosen_tables_schema
from ..utils.responses import get_fallback_response
from api.database.events import TentCRUD
from api.constants import AIModel
from api.database.schemas import get_usage_metrics_dict

class SFA:

    def __init__(self, user_query: str, db: Session, company_id: int):
        self.user_query = user_query
        self.db = db
        self.company_id = company_id
        self.max_iterations = 5
        self.usage_metrics = get_usage_metrics_dict()

    async def main(self, request=None):
        
        
        
        
        # 1. GUARD AGENT
        print("\n1. Guard agent...")
        is_safe, self.usage_metrics = await guard_agent.is_query_safe(self.user_query, self.usage_metrics)
        if not is_safe:
            return "Sorry, I can't proceed with this request", self.usage_metrics
        print(f"Guard agent result: {is_safe}\n")
        
        
        
        
        
        
        
        # 2. INTENT AGENT
        print("\n2. Intent agent...")
        intent_response, self.usage_metrics = await intent_agent.classify_intent(self.user_query, self.usage_metrics)
        if intent_response:
            intent = intent_response.get('intent')
            if intent in ['GREETING', 'IRRELEVANT']:
                print(intent_response.get('response'))
                return intent_response.get('response'), self.usage_metrics
            print(f"Intent agent result: {intent}\n")
        
        
        
        
        
        
        # 3. TENT AGENT
        print("\n3. Choosing the Tents...")
        tents_ids, self.usage_metrics = await tents_agent.get_relevant_tents(self.user_query, self.db, self.company_id, self.usage_metrics)
        print(f"Choosing the Tents result: {tents_ids}\n")
        if not tents_ids:
            return "Sorry, can you clarify your request, like add the kind of data that you need?", self.usage_metrics
        
        
        
        
        
         
        # 4. TABLES AGENT
        print("\n4. Choosing the tables...")
        tents_schema = TentCRUD.get_tables_schema(self.db, self.company_id, tents_ids)
        tablesAgent_tables_schema = clean_tables_schema(tents_schema)
        tables, self.usage_metrics = await tables_agent.get_relevant_tables(self.db, self.user_query, tents_ids, tablesAgent_tables_schema, self.usage_metrics)
        tables_schema = get_chosen_tables_schema(tables, tents_schema)
        print(f"Choosing the tables result: {tables_schema}")
                
        
        
        
        
        # 5. PREPARE PROMPT
        print("\n5. Prepare the prompt...")
        base_prompt = CreatePrompt.init_prompt(self.user_query, tables_schema, iteration=self.max_iterations)
        current_prompt = base_prompt
        scratchpad = ""
        iterations = 0
        print(f"Prepare the prompt result: Prompt initialized successfully\n")
        # print(current_prompt)
        

        
        
        
        # 6. AGENT LOOP
        print("\n6. Entering reasoning loop...")
        while iterations < self.max_iterations:            
            print(f"\na. Agent iteration {iterations}...")
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
                print("\nChecking for Final Answer result: Found!\n")
                return components, self.usage_metrics
            
            print("\nChecking for Final Answer result: Not found, continuing...\n")
            
            print("\nc. Execute Tools via ToolsManager...")
            action_input = components.get("action_input")
            
            if isinstance(action_input, dict) and "error" in action_input:
                observation = f"Observation: ERROR - {action_input['error']}. Please output valid JSON."
            else:
                observation, self.usage_metrics = await ToolsManager.main_agent_output_manager(self.db, self.company_id, action_input, request, self.usage_metrics)
                
            print(f"\nExecute Tools result: {observation}\n")
            
            print("d. updating prompt...")
            current_prompt, scratchpad = UpdatePrompt.update_prompt(base_prompt, scratchpad, llm_raw_output, observation)
            
            iterations += 1
            
        print("\n10. Exiting loop (max iterations reached)...\n")
        return get_fallback_response(), self.usage_metrics