import json
import os
import re
import time
from datetime import datetime
from typing import List, Dict

import requests
from bs4 import BeautifulSoup
from google import genai
from google.genai import types
from jinja2 import Template
from loguru import logger
from pydantic import BaseModel

DATA_DIR = "data"
MODEL = "gemini-2.5-flash"


class Response(BaseModel):
    category: str
    summary: str


def main() -> None:
    """
    Entry point to summarise papers and update README.
    """
    today_date = datetime.now().strftime("%Y-%m-%d")

    papers = list_papers()
    summarise(papers)
    update_readme(today_date, papers)


def list_papers() -> dict:
    """
    List daily papers from HuggingFace and saves their information in a JSON file.
    """
    response = requests.get("https://huggingface.co/papers")
    soup = BeautifulSoup(response.content, "html.parser")

    papers: List[Dict[str, str]] = []
    seen_ids = set()  # Set to track seen arXiv IDs

    # Locate the relevant div elements
    for paper_div in soup.find_all("div", class_="w-full"):
        # Extract the title
        title_tag = paper_div.find("a", class_="line-clamp-3")
        if title_tag:
            title = title_tag.text.strip()
            title = " ".join([x.strip() for x in title.split("\n")])  # to remove \n
        else:
            logger.warning("Title not found, skipping...")
            continue

        # Extract the paper ID from the link
        link = title_tag["href"]
        arxiv_id_match = re.search(r"/papers/(\d+\.\d+)", link)
        if arxiv_id_match:
            arxiv_id = arxiv_id_match.group(1)
        else:
            logger.warning(f"Could not extract arXiv ID from link: {link}")
            continue

        # Check for duplicates using arXiv ID
        if arxiv_id in seen_ids:
            logger.warning(f"Duplicate paper detected with ID {arxiv_id}, skipping...")
            continue
        seen_ids.add(arxiv_id)  # Add ID to set of seen IDs

        # Extract the authors
        authors = []
        for li in paper_div.find_all("li"):
            author = li.get("title")
            if author:
                authors.append(author)

        papers.append(
            {
                "title": title,
                "authors": ", ".join(authors),
                "arxiv_id": arxiv_id,
                "link": f"https://arxiv.org/abs/{arxiv_id}",
            }
        )

    return papers


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
    Updates README with the summaries of the papers.
    """
    with open("templates/output_template.md", "r") as f:
        template_string = f.read()
    output_template = Template(template_string)

    output = output_template.render(today_date=today_date, papers=papers)
    with open("README.md", "w") as f:
        f.write(output)

    # save in archive
    year, month, _ = today_date.split("-")
    os.makedirs(f"archive/{year}/{month}", exist_ok=True)

    with open(f"archive/{year}/{month}/{today_date}.md", "w") as f:
        f.write(output)

    with open(f"archive/{year}/{month}/{today_date}.json", "w") as f:
        json.dump(papers, f, indent=4)
    logger.info(f"Saved {len(papers)} papers")


if __name__ == "__main__":
    main()
