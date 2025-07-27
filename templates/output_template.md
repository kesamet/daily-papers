# daily-papers

## {{ today_date }}

{% for paper in papers %}
### {{ paper.title }}

[arXiv]({{ paper.link }})

**Authors:** {{ paper.authors }}

**Summary:** {{ paper.summary }}

---
{% endfor %}
