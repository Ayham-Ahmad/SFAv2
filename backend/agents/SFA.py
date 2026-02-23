import re
from sqlalchemy.orm import Session

from . import tents_agent, tables_agent, guard_agent, intent_agent
from ..tools import tools_manager
from ..services.prompts import CreatePrompt, UpdatePrompt
from ..utils.clean import extract_final_outputs, clean_tables_schema, clean_tables_schema_for_tableAgent
from api.database.events import TentCRUD
from ..core.llm_client import call_agent
from api.constants import AIModel

class SFA:

    def __init__(self, user_query: str, db: Session, company_id: int):
        self.user_query = user_query
        self.db = db
        self.company_id = company_id
        self.max_iterations = 5
        self.total_tokens = 0

    async def main(self, request=None):
        
        
        
        
        # 1. GUARD AGENT
        print("\n1. Guard agent...")
        is_safe = guard_agent.is_query_safe(self.user_query)
        if not is_safe:
            return "Sorry, I can't proceed with this request"
        print(f"Guard agent result: {is_safe}\n")
        
        
        
        
        
        
        
        # 2. INTENT AGENT
        print("\n2. Intent agent...")
        intent_response = intent_agent.classify_intent(self.user_query)
        intent = intent_response.get('intent')
        if intent in ['GREETING', 'IRRELEVANT']:
            print(intent_response.get('response'))
            return intent_response.get('response')
        print(f"Intent agent result: {intent}\n")
        
        
        
        
        
        
        # 3. TENT AGENT
        print("\n3. Choosing the Tents...")
        tents_ids = tents_agent.get_retlevant_tents(self.user_query, self.db, self.company_id)
        print(f"Choosing the Tents result: {tents_ids}\n")
        
        
        
        
        
        
        # 4. TABLES AGENT
        print("\n4. Choosing the tables...")
        tables_schema = TentCRUD.get_tables_schema(self.db, self.company_id, tents_ids)
        
        tablesAgent_tables_schema = clean_tables_schema_for_tableAgent(tables_schema)
                                
        tables_dict_response = tables_agent.get_relevant_tables(self.user_query, tents_ids, tablesAgent_tables_schema)
        print(f"Raw tables agent response: {tables_dict_response}")
                       
        
        
        
        
        
        
        
        
        
        # print("\n5. Prepare the prompt...")
        # base_prompt = CreatePrompt.init_prompt(self.user_query, final_table_schema)
        # scratchpad = ""
        # iterations = 0
        # print(f"\nPrepare the prompt result: Prompt initialized successfully\n")
        
        # print(base_prompt)
                
        # print("\n6. Entering reasoning loop...")
        # while iterations < self.max_iterations:
        #     current_prompt = base_prompt + scratchpad
            
        #     print(f"\na. Agent iteration {iterations}...")
        #     llm_raw_output, self.total_tokens = await call_agent(prompt=current_prompt, model=AIModel.LLAMA_33_70B, total_tokens=self.total_tokens)
        #     print(f"\nAgent output result: {llm_raw_output}\n")
            
        #     thought_match = re.search(r"Thought:\s*(.*?)(?=\nAction:|$)", llm_raw_output, re.DOTALL)
        #     action_match = re.search(r"Action:\s*(.*?)(?=\nAction Input:|$)", llm_raw_output, re.DOTALL)
        #     action_input_match = re.search(r"Action Input:\s*(.*?)(?=\nObservation:|\nThought:|\nFinal Answer:|$)", llm_raw_output, re.DOTALL)

        #     extracted_thought = thought_match.group(1).strip() if thought_match else "None"
        #     extracted_action = action_match.group(1).strip() if action_match else "None"
        #     extracted_action_input = action_input_match.group(1).strip() if action_input_match else "None"
            
        #     print("\nb. Checking for Final Answer...")
        #     if "Final Answer:" in llm_raw_output:
        #         print("\nChecking for Final Answer result: Found!\n")
        #         return extract_final_outputs(llm_raw_output), getattr(self, 'total_tokens', 0)
        #     print("\nChecking for Final Answer result: Not found, continuing...\n")
            
        #     print("\nc. Execute Tools via ToolsManager...")
        #     observation = await tools_manager.ToolsManager.main_agent_output_manager(
        #         db=self.db,
        #         company_id=self.company_id,
        #         LLM_raw_output=extracted_action_input,
        #         request=request
        #     )
        #     print(f"\nExecute Tools result: {observation}\n")
            
        #     scratchpad += f"\n{llm_raw_output}\nObservation: {observation}\nThought: "
            
        #     iterations += 1
            
        # print("\n10. Exiting loop (max iterations reached)...\n")
        # return "Final Answer: I reached the maximum number of thinking steps without finding a complete answer."