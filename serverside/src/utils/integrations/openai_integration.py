import json
import logging
import re
from typing import Optional

from openai import OpenAI
from src.config import OPENAI_KEY

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class OpenAIHelper:
    def __init__(self):
        self.client = self._create_openai_client()

    def _create_openai_client(self) -> OpenAI:
        return OpenAI(api_key=OPENAI_KEY)

    def generate_initial_scoring_query(self, node) -> str:
        cur_fun_name = node["function"]
        cur_fun_impl = node["github_function_implementation"]
        cur_file_impl = node["github_file_content"]

        query = f"""
            Imagine that you're the most competent programmer in San Francisco.
            You are tasked with making very safe update to a FUNCTION (not anything else), 
            but you can improve readability/logic if you're 100% function will do exactly the same thing.

            target_function: {cur_fun_name}
            function_code: {cur_fun_impl}

            whole file code for context: ```{cur_file_impl}```

            Please output JSON structuring your view on the question. It needs to have two fields: "quality_score" how much would you rate quality of this function from 1 to 10 and "easy_to_optimize" to label that takes values "EASY_TO_OPTIMIZE", "MAYBE_OPTIMIZE", "HARD_OPTIMIZE" representing if there is a safe refactoring available.
        """

        return query

    def generate_improvement_query(self, call_graph, node) -> str:
        # Extract the required details from the log data
        cur_fun_name = node["function"]
        cur_fun_path = node["github_file_path"]
        cur_fun_impl = node["github_function_implementation"]
        cur_fun_input = node["arguments"]
        cur_fun_output = node["return_value"]
        cur_file_impl = node["github_file_content"]

        # parent_nodes = list(call_graph.graph.predecessors(node_id))
        # children = list(call_graph.graph.successors(node_id))

        query = f"""
            Imagine that you're the most competent programmer in San Francisco.
            You are tasked with making very safe update to a FUNCTION (not anything else), 
            but you can improve readability/logic if you're 100% function will do exactly the same thing.

            How function is actually implemented: 

            path: {cur_fun_path}, target_function: {cur_fun_name}
            function_code: {cur_fun_impl}
            example input: {cur_fun_input}
            example output: {cur_fun_output}

            whole file code for context: ```{cur_file_impl}```

            Please output only single thing, the proposed code of the same function. You can also leave comment in it, asking for for follow-ups.
        """

        return query

    def generate_simulation_query(self, call_graph, node) -> str:
        # Extract the required details from the log data
        cur_fun_name = node["function"]
        cur_fun_path = node["github_file_path"]
        cur_fun_impl = (
            node["github_function_implementation"]["content"]
            if "github_function_implementation" in node
            else "Function implementation not found."
        )
        cur_fun_input = json.dumps(node.get("input_value", {}), indent=2)
        cur_fun_output = json.dumps(node.get("return_value", {}), indent=2)
        cur_file_impl = node["github_file_content"]

        query = f"""
            As a highly skilled software engineer, you're reviewing a Python function to ensure its correctness and readability. Here's the task:

            - File path: {cur_fun_path}
            - Target function: {cur_fun_name}

            The current implementation of the function is as follows:
            ```python
            {cur_fun_impl}
            ```

            Given an example input:
            ```
            {cur_fun_input}
            ```

            The function is expected to produce the following output:
            ```
            {cur_fun_output}
            ```

            The context of the whole file where the function is located is provided for better understanding:
            ```python
            {cur_file_impl}
            ```

            Simulate the environment: Run the improved function with the given example input and compare the output to the expected output.
            Finally, provide a confidence level (from 0 to 100%) on whether the improved function will consistently produce the correct output across various inputs, similar to the example provided.
            I only need one of three enums in your response "MUST_WORK", "MAYBE_WORK", "DOESNT_WORK". It will show how condident you are new function will function in exactly the same way.
            
            Also note that inputs and outputs are serialized but probably they're python objects you can deduct from this seralization code
            ```python
                def _serialize_variable(self, value: Any) -> Dict[str, Any]:
                    try:
                        json_value = json.dumps(value, default=str)
                    except TypeError:
                        json_value = str(value)
                    return {{
                        "python_type": str(type(value)),
                        "json_serialized": json_value
                    }}
            ```
        """

        return query.strip()

    def generate_after_insert_style_query(self, new_file_code, function_name) -> str:
        query = f"""
            I have programatically changed source code of my file attempting to rewrite function called {function_name}.
            Important: I will give you source code of a file that contains this function, please make sure it aligns well with files (style, tabs, etc).
            Do nothing more and give me whole new script (even if nothing needs to be changed)!
            
            Here's script text: {new_file_code}
        """

        return query.strip()

    def call_chatgpt(self, query: str) -> str:
        chat_completion = self.client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": query,
                },
                {"role": "system", "content": "You are a helpful assistant."},
            ],
            model="gpt-4",
        )

        assert len(chat_completion.choices) == 1

        return chat_completion.choices[0].message.content

    @staticmethod
    def extract_first_code_block(text: str) -> Optional[str]:
        pattern = r"```(.*?)```"
        match = re.search(pattern, text, re.DOTALL)
        code = match.group(1)

        if match:
            code = code.lstrip("python")
            code = code.lstrip("\n")
            return code

        return None
