import json
import os
import re
from datetime import datetime
from typing import List, Dict

import requests
from bs4 import BeautifulSoup
from loguru import logger

HF_URL = "https://huggingface.co/papers"
DATA_DIR = "data"


def main() -> None:
    """
    List daily papers from HuggingFace and saves their information in a JSON file.
    """
    response = requests.get(HF_URL)
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

    os.makedirs(DATA_DIR, exist_ok=True)
    today_date = datetime.now().strftime("%Y-%m-%d")
    data_filepath = os.path.join(DATA_DIR, f"{today_date}.json")
    with open(data_filepath, "w") as f:
        json.dump(papers, f, indent=4)
    logger.info(f"Saved {len(papers)} papers' information to {data_filepath}")


if __name__ == "__main__":
    main()
