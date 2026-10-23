"""The skill vocabulary: what counts as a skill, and every way people write it.

A transparent dictionary beats a black box here: when the tool says "this job wants Docker", you can see exactly which words triggered it.
Format: canonical name -> (category, [aliases]). Matching is case-insensitive on whole words.
"""
from __future__ import annotations
import re

RAW = {
    # languages
    "python": ("language", ["python", "python3", "py"]),
    "java": ("language", ["java"]),
    "javascript": ("language", ["javascript", "js", "ecmascript", "es6"]),
    "typescript": ("language", ["typescript", "ts"]),
    "c++": ("language", ["c++", "cpp"]), "c#": ("language", ["c#", "csharp"]), "go": ("language", ["golang"]),
    "rust": ("language", ["rust"]), "php": ("language", ["php"]), "ruby": ("language", ["ruby"]), "kotlin": ("language", ["kotlin"]),
    "swift": ("language", ["swift"]), "scala": ("language", ["scala"]), "r": ("language", ["r programming", "rstudio", "r language"]),
    "sql": ("language", ["sql", "t-sql", "pl/sql", "plsql", "tsql"]), "bash": ("language", ["bash", "shell scripting", "shell script"]),
    # web
    "react": ("web", ["react", "reactjs", "react.js"]), "angular": ("web", ["angular", "angularjs"]), "vue": ("web", ["vue", "vue.js", "vuejs"]),
    "node.js": ("web", ["node.js", "nodejs", "node js"]), "next.js": ("web", ["next.js", "nextjs"]), "django": ("web", ["django"]),
    "flask": ("web", ["flask"]), "fastapi": ("web", ["fastapi"]), "spring boot": ("web", ["spring boot", "springboot", "spring framework", "spring"]),
    "html": ("web", ["html", "html5"]), "css": ("web", ["css", "css3", "sass", "scss"]), "rest api": ("web", ["rest api", "rest apis", "restful", "rest endpoints"]),
    "graphql": ("web", ["graphql"]), "tailwind": ("web", ["tailwind", "tailwindcss"]),
    # data and ML
    "pandas": ("data", ["pandas"]), "numpy": ("data", ["numpy"]), "scikit-learn": ("ml", ["scikit-learn", "sklearn", "scikit learn"]),
    "tensorflow": ("ml", ["tensorflow"]), "pytorch": ("ml", ["pytorch", "torch"]), "keras": ("ml", ["keras"]),
    "machine learning": ("ml", ["machine learning", "ml models", "ml model"]), "deep learning": ("ml", ["deep learning", "neural networks", "neural network"]),
    "nlp": ("ml", ["nlp", "natural language processing"]), "computer vision": ("ml", ["computer vision", "opencv", "image recognition"]),
    "llm": ("ml", ["llm", "llms", "large language model", "large language models", "generative ai", "genai", "gpt", "openai"]),
    "rag": ("ml", ["rag", "retrieval augmented generation", "retrieval-augmented generation", "vector database", "vector db", "embeddings"]),
    "langchain": ("ml", ["langchain", "llamaindex", "langgraph"]), "prompt engineering": ("ml", ["prompt engineering", "prompt design"]),
    "mlops": ("ml", ["mlops", "mlflow", "model deployment", "model monitoring", "kubeflow"]),
    "statistics": ("data", ["statistics", "statistical analysis", "statistical modeling", "hypothesis testing", "regression analysis"]),
    "a/b testing": ("data", ["a/b testing", "ab testing", "a/b tests", "split testing"]),
    "time series": ("data", ["time series", "time-series", "demand forecasting", "forecasting models"]),
    "data analysis": ("data", ["data analysis", "data analytics", "exploratory data analysis", "eda"]),
    "data visualization": ("data", ["data visualization", "data visualisation", "dashboards", "dashboarding", "matplotlib", "seaborn", "plotly"]),
    "power bi": ("bi", ["power bi", "powerbi", "dax"]), "tableau": ("bi", ["tableau"]), "excel": ("bi", ["excel", "microsoft excel", "advanced excel", "vlookup", "pivot tables"]),
    "looker": ("bi", ["looker", "looker studio", "data studio", "qlik", "qlikview", "qliksense", "metabase", "superset"]),
    "spark": ("data eng", ["apache spark", "pyspark", "spark sql"]), "hadoop": ("data eng", ["hadoop", "hive", "hdfs"]),
    "airflow": ("data eng", ["airflow", "dagster", "prefect"]), "dbt": ("data eng", ["dbt"]), "kafka": ("data eng", ["kafka", "kinesis", "rabbitmq"]),
    "etl": ("data eng", ["etl", "elt", "data pipeline", "data pipelines", "data ingestion"]),
    "data warehousing": ("data eng", ["data warehouse", "data warehousing", "data modeling", "data modelling", "dimensional modeling"]),
    "snowflake": ("data eng", ["snowflake"]), "bigquery": ("data eng", ["bigquery"]), "redshift": ("data eng", ["redshift"]), "databricks": ("data eng", ["databricks"]),
    "duckdb": ("data eng", ["duckdb"]),
    # databases
    "postgresql": ("database", ["postgresql", "postgres"]), "mysql": ("database", ["mysql", "mariadb"]), "mongodb": ("database", ["mongodb", "mongo"]),
    "redis": ("database", ["redis"]), "elasticsearch": ("database", ["elasticsearch", "opensearch", "elk"]), "oracle": ("database", ["oracle", "oracle db"]),
    "sql server": ("database", ["sql server", "mssql", "ms sql"]), "sqlite": ("database", ["sqlite"]), "dynamodb": ("database", ["dynamodb", "cassandra"]),
    # cloud and devops
    "aws": ("cloud", ["aws", "amazon web services", "ec2", "s3", "lambda"]), "azure": ("cloud", ["azure", "azure devops"]), "gcp": ("cloud", ["gcp", "google cloud"]),
    "docker": ("devops", ["docker", "containers", "containerization"]), "kubernetes": ("devops", ["kubernetes", "k8s", "helm"]),
    "terraform": ("devops", ["terraform", "infrastructure as code", "iac", "ansible", "pulumi"]),
    "ci/cd": ("devops", ["ci/cd", "cicd", "continuous integration", "continuous delivery", "jenkins", "github actions", "gitlab ci", "circleci"]),
    "linux": ("devops", ["linux", "unix"]), "git": ("devops", ["git", "github", "gitlab", "bitbucket", "version control"]),
    "monitoring": ("devops", ["prometheus", "grafana", "datadog", "observability", "new relic", "splunk"]),
    # engineering practice
    "testing": ("practice", ["unit testing", "pytest", "junit", "test automation", "automated testing", "tdd", "integration testing", "selenium", "playwright", "cypress"]),
    "microservices": ("practice", ["microservices", "microservice"]), "system design": ("practice", ["system design", "distributed systems", "software architecture", "clean architecture", "solution architecture", "microservice architecture"]),
    "data structures": ("practice", ["data structures", "data structures and algorithms", "dsa"]), "oop": ("practice", ["oop", "object-oriented", "object oriented"]),
    "agile": ("practice", ["agile", "scrum", "kanban", "jira"]), "api design": ("practice", ["api design", "api development", "apis", "api integration"]),
    "automation": ("practice", ["automation", "workflow automation", "n8n", "zapier", "rpa", "uipath", "power automate", "make.com"]),
    "streamlit": ("web", ["streamlit", "gradio"]),
}

SOFT = {"communication", "teamwork", "leadership", "problem solving", "stakeholder"}   # not extracted: too vague to match on


def _pattern(alias: str) -> str:
    esc = re.escape(alias)
    if alias[-1] in "+#":                                   # c++ and c# have no word boundary after the symbol
        return r"(?<![a-z0-9])" + esc + r"(?![a-z0-9+#])"
    return r"(?<![a-z0-9+#/.-])" + esc + r"(?![a-z0-9+#])"


def _build():
    out = {}
    for canon, (cat, aliases) in RAW.items():
        pats = [re.compile(_pattern(a), re.I) for a in aliases]
        out[canon] = (cat, pats, aliases)
    return out


TAXONOMY = _build()
CATEGORY = {k: v[0] for k, v in TAXONOMY.items()}


# phrases that contain a skill word but are not the skill (found by reading real job posts)
NOT_SKILLS = re.compile(r"(\bagile robots\b|\breact (to|on|quickly|fast|swiftly|appropriately|accordingly)\b|\blab(oratory)? automation\b|"
                        r"\brest (and|of|assured|easy)\b|\bthe rest\b|\bhardware architecture\b)", re.I)


def find_skills(text: str) -> dict[str, int]:
    """skill -> how many times it appears in the text."""
    text = NOT_SKILLS.sub(" ", text)
    out = {}
    for canon, (_, pats, _) in TAXONOMY.items():
        n = sum(len(p.findall(text)) for p in pats)
        if n:
            out[canon] = n
    # 'java' must not be counted for javascript text, and 'rest' alone is too vague without 'api'
    return out
