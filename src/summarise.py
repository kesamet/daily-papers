"""
Summarises the papers pulled from Hugging Face's papers page,
updates the README with the summaries, and cleans up temporary files.
"""

import json
import os
import shutil
import time
from datetime import datetime
from typing import List, Dict

import google as genai
from google.genai import types
from pydantic import BaseModel

from logger import logger

TEMP_DIR = "temp_pdfs"
MODEL = "gemini-2.5-flash"


class Response(BaseModel):
    category: str
    summary: str


def main() -> None:
    """
    Main function to summarise papers, update the README, and clean up temporary files.
    """
    date = datetime.now().strftime("%Y-%m-%d")
    with open(f"data/{date}_papers.json", "r") as f:
        papers = json.load(f)

    summaries = []
    for paper in papers:
        try:
            summary = summarise_paper(
                title=paper["title"],
                pdf_path=paper["pdf_path"],
            )
            summaries.append({**paper, **summary})
            time.sleep(60)
        except Exception as e:
            logger.warning(f"Failed to summarise paper {paper['title']}: {e}")
            continue

    update_readme(summaries)

    shutil.rmtree(TEMP_DIR)
    os.makedirs(TEMP_DIR, exist_ok=True)


def summarise_paper(title: str, pdf_path: str) -> Dict[str, str]:
    """Summarises a research paper and deduces its category."""
    with open("templates/summary_template.md", "r") as f:
        template = f.read()
    prompt = template.replace("{title}", title)

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


def update_readme(result: List[Dict[str, str]]) -> None:
    """
    Updates the README file with the summaries of the papers.

    Args:
    - summaries (List[Dict[str, str]]): A list of dictionaries containing paper information and summaries.
    """
    date_str = datetime.now().strftime("%Y-%m-%d")
    new_content = f"\n\n## Papers for {date_str}\n\n"
    new_content += "| Title | Authors | Category | Summary |\n"
    new_content += "| ----- | ------- | -------- | ------- |\n"
    for r in result:
        # Replace line breaks with spaces
        summary = r["summary"].replace("\n", " ")
        new_content += f"| {r['title']} (Read more on [arXiv]({r['link']})| {r['authors']} | {r['category']} | {summary} |\n"

    day = date_str.split("-")[2]

    # Write the new content to the archive
    # Create the archive directory if it doesn't exist
    year = date_str.split("-")[0]
    month = date_str.split("-")[1]
    os.makedirs(f"archive/{year}/{month}", exist_ok=True)
    with open(f"archive/{year}/{month}/{day}.md", "w") as f:
        f.write(new_content)

    # Update the README with the new content
    # Load the existing README
    with open("README.md", "r") as f:
        existing_content = f.read()

    # Load the intro template
    with open("templates/README_intro.md", "r") as f:
        intro_content = f.read()

    # Add the date to the intro
    date_str_readme = date_str.replace("-", "--")
    intro_content = intro_content.replace("{DATE}", f"{date_str_readme} \n \n")

    # Remove the existing header
    front_content = existing_content.split("## Papers for")[0]
    existing_content = existing_content.replace(front_content, "")

    # Combine the intro, new content, and existing content
    updated_content = intro_content + new_content + "\n\n" + existing_content

    # Write the updated content to the README
    with open("README.md", "w") as f:
        f.write(updated_content)


if __name__ == "__main__":
    main()
