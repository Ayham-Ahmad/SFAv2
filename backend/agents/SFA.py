import tents_agent, tables_agent
from ..services.prompts import CreatePrompt, UpdatePrompt
from ..utils.clean import extract_final_outputs

class SFA:

    # -1.gaurd agent, input(user_query) -> bool
    # 0.Intent agent, input(user_query) -> Dict[intent, respone], if only intent = financial go to #1 else return the respone to user
    # 1.Choosing the Tents, input(user_query, user_id) -> list_of_tents_names
    # 2.Chossing the tables, input(user_quer, user_id, list_of_tents_names) -> dict_of_tables{tent: list_of_tables}
    # 3.Prepare the prompt, input(user_query, dict_of_tables{tent: list_of_tables}) -> prompt
    # 4. while(not final answer):
    # 5.Agent, input(prompt) -> output
    # 6.update the prompt, input(output) -> prompt
    # 7.exit
    # 8.extract and manage the output for the user, input(output) -> final_outputs 
    pass


    #def agent(prompt: str):