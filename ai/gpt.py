import os
from typing import Generator
import json_repair
from openai import AzureOpenAI
from dotenv import load_dotenv

from pydantic import BaseModel


class Answer(BaseModel):
    answer_markdown: str
    recommended_questions: list[str]


load_dotenv()



def format_answer_markdown(answer: Answer) -> str:
        return f"""
    {answer.answer_markdown}

    Recommended questions:
    {'\n'.join(f'- {question}' for question in answer.recommended_questions)}
    """

def completions(user_prompt: str) -> Generator[str, None, None]:
    api_version = "2024-07-01-preview"
    client = AzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),  
        api_version=api_version,
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
    )

    SYSTEM_PROMPT = """
    You are a kind QA site representative.
    You provide the markdown format of the answer to a given question, and the question that should be asked next.
    The output should be in Japanese and **MUST BE FOLLOWING JSON SCHEMA** shown below.

    JSON SCHEMA
    {JSON_FORMAT}
    """

    system_prompt = SYSTEM_PROMPT.format(JSON_FORMAT=Answer.model_json_schema())
    # print(system_prompt)
    chat_completions = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={ "type": "json_object" },
        stream=True,
        stream_options={
            "include_usage": True
        },
        temperature=1,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )

    result = ""
    recent_answer_markdown = ""
    mark_returned = False
    sent_recommended_count = 0
    recommended_questions = []
    for chunk in chat_completions:
        answer_string = ""
        if len(chunk.choices) > 0:
            content = chunk.choices[0].delta.content
            # print(f"Delta: -->{content}<--")
            if content:
                result += content
                if result.endswith("\\"):
                    continue
                json_parsed = json_repair.loads(result)
                # print(json_parsed)
                if "answer_markdown" in json_parsed:
                    answer_string = json_parsed["answer_markdown"]
                    delta_answer_string = answer_string[len(recent_answer_markdown):]
                    if delta_answer_string != "":
                        # print(f"Yield: -->{delta_answer_string}<--")
                        yield delta_answer_string
                    recent_answer_markdown = answer_string
                if "recommended_questions" in json_parsed:
                    if not mark_returned:
                        yield "--------------------------"
                        mark_returned = True
                    tmp = json_parsed["recommended_questions"]
                    if isinstance(tmp, list):
                        recommended_questions.clear()
                        # print("Clear recommended_questions")
                        for t in tmp:
                            if isinstance(t, str):
                                recommended_questions.append(t)
                    # print(recommended_questions)
                    if len(recommended_questions) > sent_recommended_count + 1:
                        # print(f"Yield: -->{recommended_questions[sent_recommended_count]}<--")
                        yield recommended_questions[sent_recommended_count]
                        sent_recommended_count += 1
    if len(recommended_questions) > sent_recommended_count:
        for q in recommended_questions[sent_recommended_count:]:
            # print(f"Yield: -->{q}<--")
            yield q