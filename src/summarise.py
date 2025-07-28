import json
import os
import time
from datetime import datetime
from typing import List, Dict
from pathlib import Path

import requests
from google import genai
from google.genai import types
from jinja2 import Template
from loguru import logger
from pydantic import BaseModel

DATA_DIR = (Path(__file__).resolve().parent.parent / "data")
MODEL = "gemini-2.5-flash"


class Response(BaseModel):
    category: str
    summary: str


def main() -> None:
    """
    Entry point to summarise papers and update the README.
    """
    today_date = datetime.now().strftime("%Y-%m-%d")
    data_filepath = DATA_DIR / f"{today_date}.json"
    try:
        with open(data_filepath, "r") as f:
            papers = json.load(f)
    except FileNotFoundError as e:
        logger.error(e)
        return

    summarise(papers)
    update_readme(today_date, papers)

    # update data
    with open(data_filepath, "w") as f:
        json.dump(papers, f, indent=4)


def summarise(papers: List[Dict[str, str]]) -> None:
    with open("templates/summary_template.md", "r") as f:
        template_string = f.read()
    summary_template = Template(template_string)

    for paper in papers:
        try:
            pdf_path = "temp.pdf"
            download_arxiv(paper["arxiv_id"], pdf_path)

            prompt = summary_template.render(title=paper["title"])
            res = summarise_paper(prompt, pdf_path)
            paper.update(res)
            time.sleep(30)
        except Exception as e:
            logger.warning(f"Failed to summarise paper {paper['title']}: {e}")
            continue


def download_arxiv(arxiv_id: str, save_path: str) -> None:
    """
    Downloads the PDF of a paper from arXiv given its ID.

    Args:
        arxiv_id (str): The arXiv ID of the paper.
        save_path (str): The path where the PDF will be saved.

    Returns:
        bool: True if the download was successful, False otherwise.
    """
    response = requests.get(f"https://arxiv.org/pdf/{arxiv_id}.pdf")
    if response.status_code == 200:
        with open(save_path, "wb") as f:
            f.write(response.content)
        return
    else:
        raise ValueError(f"Failed to download PDF for {arxiv_id}")


def summarise_paper(prompt: str, pdf_path: str) -> Dict[str, str]:
    """Summarises a paper and deduces its category."""
    client = genai.Client()
    response = client.models.generate_content(
        model=MODEL,
        contents=[prompt, pdf_path],
        config=types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(
                thinking_budget=0
            ),  # Disables thinking
            response_mime_type="application/json",
            response_schema=Response,
        ),
    )
    try:
        return json.loads(response.text)
    except Exception as e:
        logger.error(f"Unable to load in json: {e}")
        return {"category": "", "summary": ""}


def update_readme(today_date: str, papers: List[Dict[str, str]]) -> None:
    """
    Updates the README file with the summaries of the papers.
    """
    with open("templates/output_template.md", "r") as f:
        template_string = f.read()
    output_template = Template(template_string)

    output = output_template.render(today_date=today_date, papers=papers)
    with open("README.md", "w") as f:
        f.write(output)

    # save in archive
    year, month, day = today_date.split("-")
    os.makedirs(f"archive/{year}/{month}", exist_ok=True)
    with open(f"archive/{year}/{month}/{day}.md", "w") as f:
        f.write(output)


if __name__ == "__main__":
    main()
