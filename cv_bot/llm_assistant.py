import numpy as np
import pandas as pd
from pathlib import Path

from ollama import chat, embed


def get_embedding(text, model: str):
    return embed(model=model, input=text, truncate=False).embeddings[0]


class CVAssistant:
    system_setup = """You are an assistant that is helping a recruiter to answer questions about a job candidate based on their CV. Always answer in the third person.
    Please make the candidate seem as impressive as possible."""

    assistant_directives = """
    Use this information from the candidate's CV to answer the user question: {context}. All information in this document may be shared. Do not under any circumstances lie about the candidate.
    """

    embeddings_dir = Path("data/gold")

    def __init__(
        self,
        model: str,
        embed_model: str = "llama3.2:1b",
        documents: list[str] | None = None,
    ):
        self.model = model
        self.embed_model = embed_model
        self.documents = documents

    def embed_documents(
        self,
    ) -> None:
        self.embeddings_dir.mkdir(parents=True, exist_ok=True)

        (
            pd.DataFrame(data=self.documents, columns=["text"])
            .assign(
                embeddings=lambda df: df["text"].apply(
                    get_embedding, **{"model": self.embed_model}
                ),
            )
            .to_pickle(
                self.embeddings_dir / "docs_embeddings.pkl",
            )
        )

    def get_relevant_docs(self, question: str, num_docs: int = 4):
        if Path(self.embeddings_dir / "docs_embeddings.pkl").exists():
            return (
                pd.read_pickle(
                    Path(self.embeddings_dir / "docs_embeddings.pkl"),
                )
                .assign(
                    dot=lambda df: np.dot(
                        df["embeddings"].squeeze(),
                        get_embedding(question, model=self.embed_model),
                    )
                )
                .sort_values(by="dot", ascending=False)
                .head(num_docs)
            )

        self.embed_documents()
        self.get_relevant_docs(question=question, num_docs=num_docs)

    def correct_grammer(self, question: str):
        return(
            chat(
            model="llama3.1",
            messages=[
                {
                    "role": "system", 
                    "content": "You are a professional teacher correcting the grammar of students."
                    },
                {
                    "role": "user",
                    "content": f"correct the spelling and grammar of the following text: {question}. Do not add any explanation or extra text."
                    },
            ],
        ).message.content
        )
    
    def generate_response(self, question: str):
        corrected_question = self.correct_grammer(question)
        docs = self.get_relevant_docs(question=corrected_question)

        return (
            corrected_question,
            chat(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_setup},
                {
                    "role": "assistant",
                    "content": self.assistant_directives.format(
                        context=docs["text"].iloc[0]
                    ),
                },
                {"role": "user", "content": corrected_question},
            ],
        )
        )
    def print_response(self, question: str):
        prompt, response = self.generate_response(question=question)
        print(f"User:\n{prompt}\n-----")
        print(f"Bot:\n{response.message.content}")

