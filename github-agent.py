import os
from typing import Optional, List
import logfire
import requests
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.usage import UsageLimits
from dotenv import load_dotenv
from dataclasses import dataclass

from constants import GITHUB_TOKEN

load_dotenv()
logfire.configure(
    token=os.getenv("LOGFIRE_TOKEN"),
    service_name="github-agent",
    environment="development"
)
logfire.info("GitHub Agent iniciado")

@dataclass
class GitHubDependencies:
    repo_owner: str
    repo_name: str
    github_token: str = os.getenv("GITHUB_TOKEN", "")


class Issue(BaseModel):
    number: int = Field(description='Issue number')
    title: str = Field(description='Issue title')
    state: str = Field(description='Issue state (open, closed)')
    html_url: str = Field(description='Issue URL')
    created_at: str = Field(description='Creation date')
    body: Optional[str] = Field(description='Issue description')
    assignee: Optional[str] = Field(description='Assigned user')
    labels: List[str] = Field(description='Issue labels')

class TestUseCase(BaseModel):
    usecase: str = Field(description='Test usecase for the issue') 
    name: str = Field(description='Name of the test usecase')
    objective: str = Field(description='Objective of the test usecase')
    expected_result: str = Field(description='Expected result of the test usecase')
    input_variables: List[str] = Field(description='Input variables for the test usecase')

class GitHubResult(BaseModel):
    response: str = Field(description='Response to the user')
    issues: Optional[List[Issue]] = Field(description='List of issues')
    repo_info: Optional[dict] = Field(description='Repository information')
    test_usecases: Optional[List[TestUseCase]] = Field(description='List of test usecases')

github_agent = Agent(
    'openai:gpt-4o',
    deps_type=GitHubDependencies,
    result_type=GitHubResult,
    instrument=True,
    system_prompt=(
        'Eres un asistente experto en GitHub que ayuda a los usuarios a obtener información sobre issues en un repositorio. '  
        'Proporciona información útil sobre el repositorio y sus issues cuando se te pregunte. '
        'Siempre responde de manera concisa y útil.'
    ),
)


@github_agent.system_prompt
async def add_repo_info(ctx: RunContext[GitHubDependencies]) -> str:
    """Agrega información del repositorio al prompt del sistema."""      
    repo_owner = ctx.deps.repo_owner
    repo_name = ctx.deps.repo_name
    return f"El repositorio que se está analizando es {repo_owner}/{repo_name}."


@github_agent.tool
async def get_repository_info(
    ctx: RunContext[GitHubDependencies]
) -> dict:
    """Obtiene información básica sobre el repositorio."""
    headers = {"Authorization": f"token {ctx.deps.github_token}"} if ctx.deps.github_token else {}
    
    url = f"https://api.github.com/repos/{ctx.deps.repo_owner}/{ctx.deps.repo_name}"
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        return {"error": f"Error al obtener información del repositorio: {response.status_code}"}
    
    repo_data = response.json()
    return {
        "name": repo_data.get("name"),
        "full_name": repo_data.get("full_name"),
        "description": repo_data.get("description"),
        "stars": repo_data.get("stargazers_count"),
        "forks": repo_data.get("forks_count"),
        "open_issues": repo_data.get("open_issues_count"),
        "created_at": repo_data.get("created_at"),
        "updated_at": repo_data.get("updated_at"),
        "html_url": repo_data.get("html_url"),
    }


@github_agent.tool
async def get_open_issues(
    ctx: RunContext[GitHubDependencies],
    state: str = "open",
    limit: int = 10
) -> List[Issue]:
    """Obtiene issues del repositorio con filtro opcional por estado."""
    headers = {"Authorization": f"token {ctx.deps.github_token}"} if ctx.deps.github_token else {}
    
    url = f"https://api.github.com/repos/{ctx.deps.repo_owner}/{ctx.deps.repo_name}/issues"
    params = {"state": state, "per_page": limit}
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code != 200:
        return [Issue(
            number=0,
            title=f"Error fetching issues: {response.status_code}",
            state="unknown",
            html_url="",
            created_at="",
            body=None,
            assignee=None,
            labels=[]
        )]
    
    issues_data = response.json()
    issues = []
    
    for issue_data in issues_data:
        # Omite las pull requests que también se devuelven en el endpoint de issues
        if "pull_request" in issue_data:
            continue
            
        labels = [label.get("name", "") for label in issue_data.get("labels", [])]
        assignee = issue_data.get("assignee", {}).get("login") if issue_data.get("assignee") else None
        
        issue = Issue(
            number=issue_data.get("number"),
            title=issue_data.get("title"),
            state=issue_data.get("state"),
            html_url=issue_data.get("html_url"),
            created_at=issue_data.get("created_at"),
            body=issue_data.get("body"),
            assignee=assignee,
            labels=labels
        )
        issues.append(issue)
    
    return issues


@github_agent.tool
async def search_issues(
    ctx: RunContext[GitHubDependencies],
    query: str,
    limit: int = 10
) -> List[Issue]:
    """Busca issues en el repositorio usando una cadena de consulta."""
    headers = {"Authorization": f"token {ctx.deps.github_token}"} if ctx.deps.github_token else {}
    
    # Formatea la consulta para buscar en el repositorio específico
    repo_query = f"repo:{ctx.deps.repo_owner}/{ctx.deps.repo_name} {query}"
    
    url = "https://api.github.com/search/issues"
    params = {"q": repo_query, "per_page": limit}
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code != 200:
        return [Issue(
            number=0,
            title=f"Error al buscar issues: {response.status_code}", 
            state="unknown",
            html_url="",
            created_at="",
            body=None,
            assignee=None,
            labels=[]
        )]
    
    search_data = response.json()
    issues = []
    
    for item in search_data.get("items", []):
        # Omite las pull requests
        if "pull_request" in item:
            continue
            
        labels = [label.get("name", "") for label in item.get("labels", [])]
        assignee = item.get("assignee", {}).get("login") if item.get("assignee") else None
        
        issue = Issue(
            number=item.get("number"),
            title=item.get("title"),
            state=item.get("state"),
            html_url=item.get("html_url"),
            created_at=item.get("created_at"),
            body=item.get("body"),
            assignee=assignee,
            labels=labels
        )
        issues.append(issue)
    
    return issues

@github_agent.tool
async def generate_test_usecases (
    ctx: RunContext[GitHubDependencies],
    issue: Issue,
    filename: str = "test_usecases.md"
) -> List[TestUseCase]:
    """Genera y guarda test usecases basados en issues de GitHub."""
    tester_agent = Agent[None, List[TestUseCase]](
        'openai:gpt-4o',
        result_type=List[TestUseCase],
        system_prompt=(
            "Eres un experto en testing. Genera test usecases para el issue proporcionado. Contesta siempre en español."
            "Devuelve por cada usecase: "
            "1. El nombre del test"
            "2. El objetivo del test"
            "3. El resultado esperado"
            "4. Las variables de entrada que se usarán para probar el test"
        ),
    )
    filename = f"test_usecases_{issue.number}.md"

    result = await tester_agent.run(
        f"Issue: {issue.title}\n\n{issue.body}",
        usage_limits=UsageLimits(request_limit=1)
    )
    
    # Formatea los test usecases como markdown
    md_content = f"#Issue #{issue.number}: {issue.title}\n\n"  
    md_content += f"**Issue URL:** {issue.html_url}\n\n" 
    for i, usecase in enumerate(result.data, 1):
        md_content += f"### Use Case {i}\n\n"
        md_content += f"**Nombre:** {usecase.name}\n\n"
        md_content += f"**Objectivo:** {usecase.objective}\n\n"
        md_content += f"**Resultado Esperado:** {usecase.expected_result}\n\n"
        md_content += f"**Variables de Entrada:** {usecase.input_variables}\n\n"
    
    # Guarda el contenido markdown formateado en un archivo
    with open(filename, "w") as f:
        f.write(md_content)
            
    return result.data

if __name__ == '__main__':

    deps = GitHubDependencies(
        repo_owner="LIDR-academy",
        repo_name="AI4Devs-pipeline-solved",
        github_token=GITHUB_TOKEN
    )

    # Get repository information
    result = github_agent.run_sync('Sobre que trata este repositorio?', deps=deps)
    print(result.data.response)
    print("-" * 50)

    # # Get open issues
    # result = github_agent.run_sync('Enseñame los issues abiertos en este repositorio', deps=deps)
    # print(result.data.response)
    # print("-" * 50)

    # Search for specific issues
    # result = github_agent.run_sync('Obten los issues más recientes de este repositorio y genera los test usecases necesarios para cubrir el issue, minimo 5 test usecases por issue', deps=deps)  
    # print(result.data.response)
    # print("-" * 50)