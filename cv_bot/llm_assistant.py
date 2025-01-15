import numpy as np
import pandas as pd

from ollama import chat, embed
from ollama import ChatResponse

def get_embedding(text, model:str):
    return embed(model=model, input=text).embeddings[0]


class CVAssistant:

    system_setup = """You are an assistant that is helping a recruiter to answer questions about a job candidate based on their CV. Always answer in the third person.
    Please make the candidate seem as impressive as possible."""

    assistant_directives = """
    Use this information from the candidate's CV to answer the user question: {context}. All information in this document may be shared. Do not under any circumstances lie about the candidate.
    """

    def __init__(self, model:str, documents:list[str] | None = None):
        self.model = model
        self.documents = documents

    def get_relevant_docs(self, question:str):
        if self.documents is None:
            return None
        
        return (
            pd.DataFrame(
                data=self.documents, columns=["text"]
            )
            .assign(
                embeddings = lambda df: df["text"].apply(get_embedding, **{"model":self.model}),
                dot = lambda df: np.dot(list(df["embeddings"].values), get_embedding(question, model=self.model))
                )
            .sort_values(
                by="dot",
                ascending=False
                )
        )
    
    def generate_response(self, question:str):
        docs = self.get_relevant_docs(question=question)

        return (
            chat(
                model=self.model, 
                messages=[
                    {"role": "system", "content": self.system_setup},
                    { 'role': 'assistant', 'content': self.assistant_directives.format(context=docs["text"].iloc[0])},
                    { 'role': 'user', 'content': question},
                ]
            )
        )
    
    def print_response(self, question:str):
        print(self.generate_response(question=question).message.content)
    
