# daily-papers

## {{ today_date }}

{% for paper in papers %}
### {{ paper.title }}

[arXiv]({{ paper.link }})

**Authors:** {{ paper.authors }}

**Category:** {{ paper.category }}

**Summary:** {{ paper.summary }}

---
{% endfor %}
